# OPD（On-Policy Distillation，在策略蒸馏）领域最新进展调研

> 调研时间：2026-09-30 ｜ 覆盖文献：24 篇代表性论文 + 延伸阅读清单
> 说明：本文所有论文的 arXiv 编号、作者、摘要要点均来自 arXiv 原文核实，未做推测性填充。

---

## 0. 一页速览（TL;DR）

**OPD 是什么**：学生模型**自己采样轨迹**，教师在**学生真实走到的状态**上给出 **token 级稠密监督**。一句话概括其损失形式——

```
OPD = RL 的 on-policy 采样结构 + SFT 的稠密监督信号
Â_t = sg[ log π_teacher(y_t | x, y_<t) − log π_student(y_t | x, y_<t) ]
```

**为什么 2025–2026 突然爆发**：

1. **理论上**：DAgger 定理指出，离线模仿的误差随序列长度**平方级**累积（O(εT²)），而 on-policy 修正可降到**线性**（O(εT)）。推理任务越长，离线蒸馏越吃亏。
2. **工程上**：2025 年下半年起，Qwen3、GLM-5、MiMo-V2-Flash、DeepSeek-V4 等一线模型的训练报告中**同时**把 OPD 作为收尾/整合阶段——它成了工业界的"事实标准"。
3. **生态上**：截至 2026 年 9 月，arXiv 上 OPD 相关论文已超过 **200 篇**，出现了专门的 awesome-list、综述、理论刻画与大量"失败模式+修补"类工作。

**研究焦点的三次迁移**：

| 阶段 | 时间 | 核心问题 | 代表 |
|---|---|---|---|
| 第一波 | 2023–2024 | 用哪个散度？（FKL / RKL / JSD） | MiniLLM、GKD、DistiLLM |
| 第二波 | 2025–2026 初 | 信号从哪来？（自蒸馏 / 特权信息） | OPSD、SDFT、SDPO、π-Distill |
| 第三波 | 2026 全年 | 为什么不稳定？怎么稳住？ | vOPD、AOPD、Failure Modes、Entropy-Aware |

**三条设计主轴**（来自 Survey 2604.00626 的组织方式）：

- **优化什么**：固定散度 → 自适应散度 → RL 增强目标
- **信号从哪来**：白盒 logit → 黑盒标量/文本 → 自蒸馏（特权信息 / 纯自蒸馏 / 外部反馈）
- **怎么稳住**：token 加权、课程难度、算力优化

**最值得关注的四个未解问题**：蒸馏缩放律（教师规模 × 学生规模 × rollout 预算）、教师不确定性感知的反馈、**Agent 级长程轨迹蒸馏**、以及 KD 与 RL 边界的消融（G-OPD 已证明 OPD ≡ 稠密 KL 约束 RL 的特例）。

---

## 1. 定义与形式化：OPD 到底在做什么

### 1.1 形式化定义

Survey（arXiv:2604.00626）给出的定义：

> **一个蒸馏方法被称为 on-policy，当且仅当学生的训练数据在训练时刻由学生自身的当前策略 p_θ 采样得到**，而不是来自固定的外部语料 𝒟，也不是来自教师的生成分布 p_T。

其优化目标为：

```
min_θ  E_{x∼𝒟} E_{y∼p_θ(·|x)} [ L(y, x; θ, T) ]
```

关键区别在于**外层期望是关于学生自己的生成**。这带来两个直接后果：

- 优化景观**非平稳**（p_θ 随 θ 变化），每一步都需要**重新 rollout**——这是 OPD 全部系统开销的来源；
- 监督信号落在**学生自己会走到的状态**上，而不是教师的"完美前缀"上。

### 1.2 统一视角：f-散度框架

Survey 把 OPD 统一为"在学生采样轨迹上的 f-散度最小化"：

```
L_OPD(θ) = E_{y∼π_mix} [ Σ_t D_f( p_T(·|x, y_<t) ‖ p_θ(·|x, y_<t) ) ]
```

三个治理性设计选择：**轨迹采样分布 π_mix**、**散度生成函数 f**、**散度内部的自变量顺序**。

| 散度 | 行为 | 适用场景 |
|---|---|---|
| Forward KL（前向） | mode-covering，铺开 | 开放式生成、翻译 |
| Reverse KL（反向） | mode-seeking，聚焦 | 数学/推理（答案唯一） |
| JSD | 对称、有界 | 中等多样性任务 |
| α-divergence | 在 FKL↔RKL 之间插值 | 需要精细控制时 |

### 1.3 与 SFT / RL 的对照

| 维度 | 离线 SFT / KD | On-policy RL（PPO/GRPO） | **OPD** |
|---|---|---|---|
| 数据来源 | 教师/人工预生成，固定 | 学生实时采样 | 学生实时采样 |
| 监督密度 | 硬标签，逐 token 但有偏 | 稀疏（仅终局奖励） | **稠密软标签（逐 token 教师概率）** |
| 优势来源 | — | 组内奖励对比 | **师生 log 比值** |
| KL 约束 | 无 | 需冻结 π_ref 与 β·D_KL | 教师本身即约束，无需额外 KL 项 |
| 暴露偏差 | 有 | 无 | **无** |
| 遗忘风险 | 高（mode-covering） | 中 | **低** |
| 计算成本 | 低 | 高（多次 rollout + 组对比） | 中（教师前向 + 学生采样，group size 可=1） |

---

## 2. 24 篇代表性论文逐一分析

### A 组 · 奠基与经典（4 篇）

---

#### 01. MiniLLM：首次为 LLM 形式化 OPD

**MiniLLM: On-Policy Distillation of Large Language Models**
arXiv:2306.08543 ｜ Yuxian Gu, Li Dong, Furu Wei, Minlie Huang（清华大学 & 微软亚洲研究院）｜ 2023-06 提交，ICLR 2024，v6 修订至 2026-01

**一句话定位**：把标准 KD 的前向 KL 换成**反向 KL**，并推导出可落地的 on-policy 优化算法，是 OPD 这条线的起点。

**核心方法**
- 指出标准 KD 用 forward KL，会迫使学生在教师分布的**低概率区域**也分配概率（因为 FKL 的期望权重是 P_teacher），导致学生"高估教师不重要的区域"；
- 改用 **reverse KL**，期望权重落在学生自己身上，使学生只在自己会生成的区域上对齐教师的高置信预测；
- 由于 RKL 的期望依赖 p_θ，无法用固定数据集估计，作者推导了一套 **on-policy 优化流程**（策略梯度式的重加权 + 单步分解），学生模型命名 MiniLLM。

**关键结果**
- 指令跟随设定下，相比基线生成更精确、整体质量更高、**暴露偏差更低、校准更好、长文本生成更强**；
- 在 **120M 到 13B** 参数范围内可扩展，覆盖不同模型族。

**点评**：本文的贡献是"把一个直觉（别让小学生背标准答案，让他在自己的错误上被纠正）变成了可训练的损失"。它的局限也正是后续三年的主战场——RKL 的高方差、mode-seeking 导致的多样性塌缩，在本文中尚未被系统处理。**它是 OPD 的坐标系原点，任何 OPD 论文都以它为对照。**

---

#### 02. GKD：把"自生成错误"变成通用框架

**On-Policy Distillation of Language Models: Learning from Self-Generated Mistakes (GKD)**
arXiv:2306.13649 ｜ Rishabh Agarwal, Nino Vieillard, Yongchao Zhou, Piotr Stanczyk, Sabela Ramos, Matthieu Geist, Olivier Bachem（Google DeepMind）｜ 2023-06 提交，ICLR 2024

**一句话定位**：与 MiniLLM 同期、独立提出，把 OPD 抽象为一个**可自由选择散度的通用框架**，并打通与 RLHF 的结合。

**核心方法**
- 指出自回归模型的 KD 存在**训练序列与推理序列的分布错配**；
- **GKD 不再依赖固定输出集合**，而是在学生**自生成序列**上利用教师反馈训练；
- 与监督式 KD 不同，GKD **允许在师生之间自由选择损失函数**（FKL / RKL / JSD 等）——当学生表达力不足以模仿教师时，这个自由度是关键；
- 支持**蒸馏与 RL 微调（RLHF）的无缝集成**。

**关键结果**：在摘要、翻译、算术推理三类任务上验证有效，并支持任务无关的指令微调蒸馏。

**点评**：MiniLLM 回答"该用什么散度"，GKD 回答"散度可以自由选，而且能接 RL"。**GKD 的"学生自生成 + 教师反馈"结构，是今天所有 OPD 实现的事实接口**（绝大多数开源 OPD 代码库都复用它定义的 on-policy 采样循环）。它的 JSD 选项也为后来"FKL/RKL 混合"这条支线埋下伏笔。

---

#### 03. DistiLLM：给 OPD 一个理论化的散度与效率方案

**DistiLLM: Towards Streamlined Distillation for Large Language Models**
arXiv:2402.03898 ｜ Jongwoo Ko, Sungnyun Kim, Tianyi Chen, Se-Young Yun（KAIST 等）｜ 2024-02 提交，ICML 2024

**一句话定位**：指出 OPD 缺乏**标准化目标函数**且**计算成本高**，提出 skew KL 损失 + 自适应离线策略，兼顾效果与 4.3× 加速。

**核心方法**
- **问题诊断**：自回归 KD 缺少统一目标；而近期"用学生生成输出"的做法显著抬高了算力成本；
- **Skew KL 损失**：作者揭示并利用了 skew Kullback-Leibler 散度的理论性质，构造出比 FKL/RKL 更均衡的目标；
- **自适应离线（adaptive off-policy）策略**：设计用于更高效地利用学生生成输出，而非每一步都重新采样。

**关键结果**：指令跟随等任务上构建出高性能学生模型，相比同期 KD 方法取得**最高 4.3× 加速**。

**点评**：这是第一波中"工程理性"最强的一篇——它承认 on-policy 采样昂贵，于是**在目标函数层面而非系统层面**找效率。它提出的"off-policy 与 on-policy 不必二选一"的思路，直接预示了后面 Lightning OPD、NPD 等离线/异步 OPD 的方向。

---

#### 04. Speculative KD：用"师生协作采样"填平能力鸿沟

**Speculative Knowledge Distillation: Bridging the Teacher-Student Gap Through Interleaved Sampling**
arXiv:2410.11325 ｜ Wenda Xu, Rujun Han, Zifeng Wang, Long T. Le, Dhruva Madeka, Lei Li, William Yang Wang, Rishabh Agarwal, Chen-Yu Lee, Tomas Pfister（Google 等）｜ 2024-10 提交，ICLR 2025

**一句话定位**：揭示 OPD 的一个致命软肋——**学生生成的错误前缀会让教师给出不可靠的反馈**，并用"学生提议、教师替换"的交错采样解决它。

**核心方法**
- **问题诊断**：监督式 KD 有分布错配；而纯 on-policy KD 会产生**低质量训练样本，教师对这些样本并不熟悉**，从而反馈不准确——这正是后来被反复引用的"flawed prefix trap"（缺陷前缀陷阱）；
- **SKD 机制**：学生提出 token，教师根据自身分布**替换排名不佳的 token**，在线的、自适应的传递高质量知识；
- 本质是一种**师生协作的推测式采样**：采样分布既不是纯学生也不是纯教师，而是二者的插值。

**关键结果**：在翻译、摘要、数学、指令跟随等多任务上，跨不同领域、数据规模和模型初始化策略**一致优于现有 KD 方法**。

**点评**：这篇论文的洞见比它的方法更重要。它精确指出了一个结构性矛盾：**on-policy 保证状态分布正确，但教师在这些状态上恰恰最不可靠**。2026 年大量论文（Revisiting OPD、Prefix Teach Suffix Fade、Not All Disagreement Is Learnable）都在继续回答这个问题——**SKD 是这条问题线的开端**。

---

### B 组 · 综述与理论刻画（3 篇）

---

#### 05. OPD 首部系统综述：把散落的三社区文献统一起来

**A Survey of On-Policy Distillation for Large Language Models**
arXiv:2604.00626 ｜ Mingyang Song, Mao Zheng（腾讯）｜ 2026-04 提交，v4 修订至 2026-06

**一句话定位**：目前该领域唯一的系统性综述，把散落在知识蒸馏、RLHF、模仿学习三个社区的贡献统一为 **f-散度最小化**框架。

**核心内容**
- **问题起点**：工业界主流配方（静态模仿教师文本）有一个结构性弱点，任务越长、推理越重就越严重——学生用完美教师前缀训练，却在自己推理时生成自己的前缀，小错误累积成"从未被训练过如何恢复"的轨迹；
- **形式化**：OPD = 学生采样轨迹上的 f-散度最小化，目标是**把平方级的复合误差降到线性**，并把蒸馏重新定义为**迭代纠错过程**而非一次性模仿；
- **三轴组织**：优化什么（目标函数）／信号从哪来（教师架构）／怎么稳定（训练动力学）；
- **整合了成功条件、反复出现的失败模式、以及 OPD 与 KL 约束 RL 的联系**。

**关键结果与观察**
- **自蒸馏是最大、增长最快的类别**（2025–2026 为主），反映研究重心从"哪个 KL 方向"转向"自我改进与自适应替代方案"；
- 给出四个公开问题：**蒸馏缩放律**（Quality ∝ N_T^α·N_S^β·D^γ·R^δ，其中 rollout 预算 R 是 OPD 独有的新轴）、**不确定性感知反馈**、**Agent 级蒸馏**、**KD 与 RL 的重叠**；
- 明确指出结构性局限："它们优化的是到教师分布的距离。在任何 f-散度下完美优化，得到的也只是匹配教师的学生，而**很少超越它**。"——这句话正是 ExOPD 的出发点。

**点评**：**如果只读一篇，读这篇。** 它的价值不在提出方法，而在于给出坐标系与"已踩过的坑"清单。同时它诚实地标注了局限：领域贡献仍然分散、可复现性差、缺乏统一基准。

---

#### 06. Rethinking OPD：OPD 什么时候成功、什么时候失败

**Rethinking On-Policy Distillation of Large Language Models: Phenomenology, Mechanism, and Recipe**
arXiv:2604.13016 ｜ Yaxuan Li, Yuxin Zuo, Bingxiang He, Jinqian Zhang, Chaojun Xiao, Cheng Qian, Tianyu Yu, Huan-ang Gao, Wenkai Yang, Zhiyuan Liu, Ning Ding（清华大学 THUNLP）｜ 2026-04，30 页 23 图，代码 github.com/thunlp/OPD

**一句话定位**：2026 年**最重要的一篇 OPD 机制研究**，用实验把"OPD 何时有效"从玄学变成两个可检验条件。

**核心发现**
- **两个决定成败的条件**：
  1. 学生与教师必须**共享兼容的思维模式（thinking pattern）**；
  2. 即便思维模式一致且教师分数更高，**教师也必须提供学生训练中没见过的新能力**——否则 OPD 无增益；
- **弱到强反向蒸馏验证**：同族的 **1.5B 与 7B 教师，从学生视角看是分布上不可区分的**——即"更大的同族模型"未必是更好的教师；
- **token 级机制**：成功的 OPD 表现为**在学生访问过的状态上、对高概率 token 的渐进对齐**；存在一个**只占 97%–99% 概率质量的小规模共享 token 集**；
- **两个补救配方**：**off-policy 冷启动** + **教师对齐的 prompt 选择**，可挽救失败的 OPD；
- **代价揭示**："token 级稠密奖励的免费午餐"其实有代价，因此质疑 **OPD 能否扩展到长程（long-horizon）蒸馏**。

**点评**：这篇论文最大的贡献是给了一个**否决性判据**：如果你的教师只是"同族更大、分数更高"，OPD 很可能白跑。这与工业界"用同架构历史 checkpoint 当教师"（GLM-5 做法）形成有意思的张力——同架构对齐 logit 空间，但可能缺乏新能力。**它是做 OPD 前的必读 checklist。**

---

#### 07. On the Geometry of OPD：OPD 在参数空间里长什么样

**On the Geometry of On-Policy Distillation**
arXiv:2606.07082 ｜ Zhennan Shen, Yanshu Li, Qingyu Yin, Chak Tou Leong, Zhilin Wang, Yanxu Chen, Rongduo Han, Sunbowen Lee, Yi R. Fung（香港大学 & 南洋理工等）｜ 2026-06，17 页

**一句话定位**：首次从**参数空间几何**角度刻画 OPD，证明它既不是 SFT 也不是 RL，而是**自成一类的更新几何**。

**核心发现**
- **静态定位**：一套参数空间诊断指标一致地把 OPD 放在**松弛的 off-principal（偏离主方向）区域**——相比 SFT，它的更新影响更少的权重、更强地避开主方向；相比 RLVR，它的约束又没那么紧；
- **子空间锁定（subspace locking）**：OPD 的累积更新会**迅速进入一个狭窄的低维通道**；
- **功能充分性**：把训练限制在训练早期形成的更新子空间内，**OPD 性能得以保持，而 SFT 显著退化**——说明被锁定的子空间对 OPD 是功能充分的；
- **控制实验**：稀疏化更新 token、把 rollout 生成推向 off-policy，**都不会改变秩动力学**；只有把 OPD 目标与 RLVR 混合才会改变。

**点评**：这是一篇"解释性"论文，短期内不直接提升指标，但它给出了一个可操作推论：**OPD 的低维子空间锁定，可能正是它"抗遗忘"（低 KL 漂移）的几何原因**，也解释了为什么 OPD 可以做得比 RL 更省、比 SFT 更稳。对做 LoRA / 子空间微调的人来说，这篇的启示价值很高。

---

### C 组 · 自蒸馏与特权信息（5 篇）

> **本组是 2026 年增长最快的方向。** 共同思想：**不需要一个更大的外部教师——让"看过答案的自己"去教"没看过答案的自己"。**

---

#### 08. OPSD：同一个模型，两个上下文，互为师生

**Self-Distilled Reasoner: On-Policy Self-Distillation for Large Language Models**
arXiv:2601.18734 ｜ Siyan Zhao, Zhihui Xie, Mengchen Liu, Jing Huang, Guan Pang, Feiyu Chen, Aditya Grover（UCLA & Meta 等）｜ 2026-01，v3 2026-03，代码 github.com/siyan-zhao/OPSD

**一句话定位**：把"特权信息"引入 OPD——**同一个 LLM 同时扮演教师和学生，区别只在上下文里有没有答案**。

**核心方法**
- **动机**：标准 OPD 需要一个独立（通常更大）的教师模型，且**没有利用推理数据集中现成的标准答案**；
- **直觉**：一个足够强的 LLM 能够**把外部给的特权推理轨迹合理化（rationalize）**，并用它教更弱的自己；
- **OPSD**：单一 LLM 兼任师生。**教师策略条件于特权信息**（如已验证的推理轨迹），**学生策略只看题目**；训练目标是最小化二者在**学生自己 rollout 上**的逐 token 散度。

**关键结果**
- 多个数学推理基准上，相比 RL 方法有**更优的 token 效率**，相比离线蒸馏方法有**更好的性能**。

**点评**：OPSD 把 OPD 的成本结构彻底改变了——**不再需要单独部署一个大教师**，教师就是"同一份权重 + 不同 prompt"。这直接催生了 2026 年下半年几十篇 OPSD 变体（CREDIT、EGRSD、DASH、SR-OPSD 等）。**需要注意的坑**：后续工作指出"特权信息教师"本身可能带偏（Privileged, but Biased, 2608.04794），以及"思维塌缩"（Thinking Collapse, 2607.10805）等问题。

---

#### 09. SDPO：把"报错信息"变成稠密监督

**Reinforcement Learning via Self-Distillation**
arXiv:2601.20802 ｜ Jonas Hübotter, Frederike Lübeck, Lejs Behric, Anton Baumann, Marco Bagatella, Daniel Marta, Ido Hakimi, Idan Shenfeld, Thomas Kleine Buening, Carlos Guestrin, Andreas Krause（ETH Zurich & MIT）｜ 2026-01，v2 2026-02

**一句话定位**：重新定义 RLVR 的问题——**不是奖励太稀疏，而是反馈被丢掉了**。

**核心方法**
- **问题诊断**：现有 RLVR 只从每次尝试的**标量结果奖励**学习，造成严重的**信用分配瓶颈**；但许多可验证环境其实提供了丰富的文本反馈（运行时错误、judge 评价）解释**为什么失败**；
- 作者将这一设定形式化为 **"带丰富反馈的强化学习"（RL with rich feedback）**；
- **SDPO（Self-Distillation Policy Optimization）**：**把 token 化的反馈转化为稠密学习信号，不需要任何外部教师或显式奖励模型**；
- 机制：把"**条件于反馈的当前模型**"当作 **self-teacher**，把它**反馈知情后的下一 token 预测**蒸馏回策略本身——即利用模型**在上下文内回溯识别自身错误**的能力。

**关键结果**
- 科学推理、工具使用、竞赛编程（LiveCodeBench v6）上，样本效率与最终准确率均优于强 RLVR 基线；
- **即使在只返回标量反馈的标准 RLVR 环境中也优于基线**——因为它用**成功的 rollout 作为失败尝试的隐式反馈**；
- 测试时对单题应用 SDPO，达到与 best-of-k 采样或多轮对话**相同发现概率所需尝试次数减少 3×**。

**点评**：SDPO 的框架价值在于它**把 OPD 从"教师蒸馏"扩展为"反馈蒸馏"**。它的关键洞察是：**失败轨迹里包含了成功轨迹没有的信息**（为什么错），而标准 RLVR 把这些信息扔掉了。对做 Agent / 代码 / 工具的团队，这篇的可迁移性极强。

---

#### 10. SDFT：用自蒸馏实现持续学习

**Self-Distillation Enables Continual Learning**
arXiv:2601.19897 ｜ Idan Shenfeld, Mehul Damani, Jonas Hübotter, Pulkit Agrawal（MIT）｜ 2026-01，v2 2026-08

**一句话定位**：证明 **on-policy 蒸馏是从示范中持续学习、且不遗忘的实用路径**。

**核心方法**
- **问题**：持续学习的核心矛盾——学新技能/知识而不退化旧能力。on-policy RL 能减少遗忘，但**需要显式奖励函数**（常常没有）；而"从专家示范学习"这一替代方案**被离线 SFT 主导，而 SFT 本质上是 off-policy 的**；
- **SDFT（Self-Distillation Fine-Tuning）**：利用**上下文学习**，把**示范条件化的模型当作自己的教师**，从示范中直接生成 on-policy 训练信号，从而在获得新技能的同时保留旧能力。

**关键结果**
- 技能学习与知识获取任务上，**一致优于 SFT**：新任务准确率更高，**灾难性遗忘显著降低**；
- **序列学习实验**：单一模型可**随时间累积多项技能而无性能回退**。

**点评**：这篇与 SDPO 同源（共同作者 Hübotter、Shenfeld），但目标不同：SDPO 解决"奖励稀疏"，SDFT 解决"示范学习会遗忘"。**它给出的结论很有分量：只要把 SFT 的示范学习改造成 on-policy 形式，遗忘问题就大幅缓解**——这与"RL 遗忘更少是因为它偏好低 KL 解"（RL's Razor）的解释相互印证。

---

#### 11. π-Distill：为"看不到思维链"的前沿模型做蒸馏

**Privileged Information Distillation for Language Models**
arXiv:2602.04942 ｜ Emiliano Penaloza, Dheeraj Vattikonda, Nicolas Gontier, Alexandre Lacoste, Laurent Charlin, Massimo Caccia（Mila & ServiceNow 等）｜ 2026-02，v3 2026-02

**一句话定位**：解决一个极现实的困境——**前沿模型只暴露动作轨迹、隐藏内部推理**，此时标准蒸馏管线直接失效。

**核心方法**
- **问题设定**：训练期特权信息（PI）能让模型完成原本无法完成的长程任务，但**把 PI 学到的能力迁移到推理时没有 PI 的策略上**是个根本挑战；在多轮 Agent 环境中，**成功行为可观测，但推理过程不可观测**；
- **π-Distill**：一个**联合师生目标**，用**同一个模型**同时训练"PI 条件化教师"和"无 PI 条件化学生"；
- **另一方案 OPSD（本文的变体）**：用 **RL + 学生与 PI 条件化教师之间的反向 KL 惩罚**来训练。

**关键结果**
- π-Distill 以及（部分情况下的）OPSD，在多个 Agent 基准、多种模型、多种 PI 形式上，**优于"假设可获取完整思维链监督"的业界标准做法（SFT → RL）**；
- 作者做了大量分析，刻画"何种 PI 形式能有效学习"，并明确界定 **OPSD 在什么条件下才有竞争力**。

**点评**：**这篇是所有做闭源模型蒸馏 / Agent 蒸馏的人的第一参考文献。** 它的现实意义在于：GPT/Claude 级别的模型不会给你 logits，也不会给你思维链，只给你动作序列。π-Distill 证明了"**只有动作轨迹作为特权信息也够用**"。

---

#### 12. OPCD：把上下文知识内化进参数

**On-Policy Context Distillation for Language Models**
arXiv:2602.12275 ｜ Tianzhu Ye, Li Dong, Xun Wu, Shaohan Huang, Furu Wei（微软）｜ 2026-02，v2 2026-03

**一句话定位**：把 OPD 与**上下文蒸馏**结合，让学生在自己的轨迹上把"上下文里的知识"内化进权重。

**核心方法**
- **OPCD**：在学生**自己生成的轨迹**上训练，最小化与**上下文条件化教师**之间的**反向 KL**；
- 两个应用场景：
  1. **经验知识蒸馏（experiential knowledge distillation）**：模型从**自己的历史解题轨迹**中抽取并固化可迁移的知识；
  2. **系统提示蒸馏（system prompt distillation）**：把优化过的 prompt 里编码的有益行为内化进模型。

**关键结果**
- 数学推理、文本游戏、领域特定任务上一致优于基线，**任务准确率更高，同时更好地保留分布外能力**；
- 支持**跨规模蒸馏**——更小的学生可以从更大的教师内化经验知识。

**点评**：OPCD 与 OPSD 同属"上下文即特权信息"，但它把目标从"教推理"扩展到"**教经验与教系统提示**"。对工程实践的直接价值：**把昂贵的 prompt engineering / 长系统提示压缩进权重**，从而降低推理成本。这是一条被低估的落地路径。

---

### D 组 · 目标函数与训练稳定性（5 篇）

> **本组是 2026 年的主战场。** 共同背景：OPD 的**单样本蒙特卡洛估计器方差极高**，实践中的不稳定已成为公认瓶颈。

---

#### 13. G-OPD / ExOPD：证明 OPD 是 KL 约束 RL 的特例，并让学生超越教师

**Learning beyond Teacher: Generalized On-Policy Distillation with Reward Extrapolation**
arXiv:2602.12125 ｜ Wenkai Yang, Weijie Liu, Ruobing Xie, Kai Yang, Saiyong Yang, Yankai Lin（中国人民大学 & 腾讯）｜ 2026-02

**一句话定位**：给出了 OPD 与 RL 的**理论等价关系**，并由此推出一个能**突破教师性能上界**的简单改动。

**核心方法与理论**
- **理论结果**：**OPD 是稠密 KL 约束 RL 的一个特例**——其中**奖励函数与 KL 正则始终等权**，且参考模型可以是任意模型；
- **G-OPD 框架**：通过引入**灵活的参考模型**和**奖励缩放因子**（控制奖励项相对 KL 正则的权重），扩展了标准 OPD 目标。

**两个新洞见**
1. **奖励外推（reward scaling > 1，即 ExOPD）**在多种师生规模配对上**一致优于标准 OPD**。特别是在"把多个领域专家（对同一学生做领域 RL 得到）的知识合并回原学生"的设定下，**ExOPD 使学生超越教师性能边界，并超过各领域教师本身**；
2. 在**强到弱蒸馏**设定下，把**参考模型选为教师 RL 之前的基础模型**做奖励校正，能得到更准确的奖励信号、进一步提升蒸馏效果——代价是需要访问教师 RL 前的版本且增加算力。

**点评**：这篇同时解决了综述提出的"结构性局限"（完美优化也只是匹配教师）和"OPD 与 RL 边界模糊"两个问题。**"等权 KL-RL"这个等价关系是 2026 年被引用最多的理论结论之一**——它意味着 OPD 的所有 RL 技巧（基线、优势估计、裁剪）都可以合法移植过来，vOPD 正是这么做的。

---

#### 14. Entropy-Aware OPD：当教师自己都不确定时，别用反向 KL

**Entropy-Aware On-Policy Distillation of Language Models**
arXiv:2603.07079 ｜ Woogyeol Jin, Taywon Min, Yongjin Yang, Dennis Wei, Yi Zhou, Swanand Ravindra Kadhe, Nathalie Baracaldo, Kimin Lee（KAIST & IBM Research）｜ 2026-03，v3 2026-06，**ICML 2026**

**一句话定位**：指出反向 KL 的 mode-seeking 特性在**教师熵高**时会**降低生成多样性并产生不稳定学习信号**，并给出简单修补。

**核心方法**
- **诊断**：OPD 通常用反向 KL 鼓励学生匹配教师的高置信预测；但 RKL 的 mode-seeking 特性在**教师分布高熵**时会造成多样性下降与信号不稳；
- **方案**：**当教师熵高时，在标准反向 KL 目标上叠加前向 KL**——在高熵处捕获全部合理输出（mode-covering），在其余位置保留精确模仿（mode-seeking）；
- 关键优势：**不牺牲 on-policy 训练效率**即可平衡"聚焦精度"与"覆盖鲁棒性"。

**关键结果**
- 维持生成多样性（token 级熵得以持续），改善师生对齐（高熵 token 上的前向 KL 更低）；
- 六个数学推理基准上的 **Pass@8 提升**：Qwen3-0.6B-Base **+1.37**、Qwen3-1.7B-Base **+2.39**、Qwen3-4B-Base **+5.05**（相对基线 OPD）。

**点评**：这是"FKL/RKL 混合"这条支线里最干净的一篇——**用教师熵作为切换开关**，而非拍脑袋加权。它的结论与综述的分类（自适应散度目标）完全吻合，且增益随模型规模增大而增大（+5.05 @ 4B），暗示**大模型上多样性塌缩更严重**。

---

#### 15. Revisiting OPD：三个失败模式与一个 +19.8% 的配方

**Revisiting On-Policy Distillation: Empirical Failure Modes and Simple Fixes**
arXiv:2603.25562 ｜ Yuqian Fu, Haohuan Huang, Kaiwen Jiang, Jiacai Liu, Zhuo Jiang, Yuanheng Zhu, Dongbin Zhao（中科院自动化所）｜ 2026-03，v2 2026-04

**一句话定位**：一篇**极其实用**的工程诊断报告——把 OPD 不稳定的原因拆成三个可操作项，并给出简单修补。

**理论贡献**
- 指出标准实现把分布匹配简化为**采样 token 的 log 比值**，在**长 rollout 且前缀漂移离开教师典型支撑集**时，学习信号会变得脆弱；
- **token 级 OPD 相对序列级反向 KL 最小化是有偏的，但具有显著更紧的最坏情况方差界**；
- 受控合成实验显示：**更强的未来奖励耦合会提高梯度方差并使训练失稳**。

**三个失败模式（实证）**
1. **token 级监督不均衡**；
2. **教师对学生生成前缀的指导不可靠**（即 SKD 指出的 flawed prefix trap）；
3. **tokenizer / 特殊 token 不匹配**。

**解决方案**：**教师 top-K 局部支撑匹配（teacher top-K local support matching）**——在每个前缀上，仅在**教师支撑的 token 集合**内比较师生分布，配合 **top-p rollout 采样**与**特殊 token 掩码**。

**关键结果**：跨单任务推理与多任务（Agent + 推理）基准，优化稳定性提升，**相对标准采样 token OPD 基线取得 +19.8% 的性能增益**。

**点评**：如果第 06 篇（Rethinking OPD）是"该不该做 OPD"的判据，**这篇就是"做的时候哪里会炸"的手册**。三个失败模式都极易在自研代码里出现（尤其 tokenizer 不匹配，跨模型族时几乎必然发生）。**建议任何 OPD 实现的第一步都先跑这三个检查。**

---

#### 16. AOPD：非正优势区域别再"负强化"，改成局部散度最小化

**Asymmetric On-Policy Distillation: Bridging Exploitation and Imitation at the Token Level**
arXiv:2605.06387 ｜ Nan Jia, Haojin Yang, Xing Ma, Jiesong Lian, Shuailiang Zhang, Weipeng Zhang, Ke Zeng, Xunliang Cai, Zequn Sun（美团等）｜ 2026-05，v4 2026-08

**一句话定位**：指出标准 OPD 的**优势加权策略梯度有三个结构性弱点**，并用"非对称"处理修复。

**问题诊断**：标准 OPD 的优势加权策略梯度存在——
1. **更新方差高**；
2. **零优势区域梯度消失**；
3. **纠正信号不足时的探索瓶颈**。

**核心方法**
- **AOPD**：在**非正优势区域，用局部散度最小化替代无效的负强化**，同时**保留正优势区域的强化学习**——即正负两侧采用**非对称**的处理方式；
- 直觉：当教师比学生更不自信时（Â<0），把它当"负样本去惩罚"信息量很低且梯度噪声大；不如直接**局部对齐分布**。

**关键结果**
- 数学推理基准上一致优于标准 OPD，**强初始化下平均 +4.09，弱初始化下平均 +8.34**；
- 训练过程中**保持更高的策略熵**，且在**顺序工具使用适配**中能力保留更好。

**点评**：**"弱初始化下增益更大（+8.34 vs +4.09）"是这篇最有价值的信号**——说明非对称处理主要解决的是"学生离教师太远时的学习失败"。这与第 06 篇的"冷启动"结论、VOLD 的"cold-start alignment 必需"结论相互印证：**OPD 在师生差距大时需要特殊处理。**

---

#### 17. vOPD：用 RL 的控制变量基线消掉 OPD 的方差

**KL for a KL: On-Policy Distillation with Control Variate Baseline**
arXiv:2605.07865 ｜ Minjae Oh, Sangjun Song, Gyubin Choi, Yunho Choi, Yohan Jo（首尔国立大学）｜ 2026-05

**一句话定位**：把 OPD 明确当作策略梯度 RL，然后**从 RL 工具箱里搬来控制变量基线**——而且发现这个基线有闭式解。

**核心方法**
- **问题**：OPD 在实践中因**单样本蒙特卡洛估计器的高梯度方差**而不稳定，稳定训练的配方仍不成熟；
- **vOPD**：把 OPD 重塑为策略梯度 RL，引入**控制变量基线（经典做法是价值函数）**来稳定；
- **关键理论结果**：**OPD 的价值函数有闭式解 = 学生与教师之间逐 token 的负反向 KL 散度**，且**可直接从已经算完的前向传播中获得，无需额外的 critic 或推理**；
- **与现有方法的对比**：已有稳定化方法要么在整个词表上计算完整 token 级反向 KL（开销巨大），要么限制在 top-k 支撑集（使目标有偏）。vOPD **保留轻量的单样本估计器**，仅减去作为基线的价值函数（detached），**在降方差的同时保持梯度无偏**；
- 进一步证明基线的 **top-k 近似**可进一步降本而不损性能。

**关键结果**：数学与科学推理基准上，**一致优于 vanilla OPD，并匹敌最昂贵的全词表基线**。

**点评**：这是**理论与工程结合得最漂亮的一篇**。"价值函数 = 负反向 KL"这个闭式解意味着 OPD 的方差降低是**免费**的——不需要额外网络。**如果只能给一个 OPD 工程建议，就是先加上 vOPD 的基线。** 它也是 G-OPD "OPD ≡ KL 约束 RL" 理论最直接的应用成果。

---

### E 组 · 效率与系统（3 篇）

---

#### 18. Lightning OPD：把教师服务器彻底拿掉

**Lightning OPD: Efficient Post-Training for Large Reasoning Models with Offline On-Policy Distillation**
arXiv:2604.13010 ｜ Yecheng Wu, Song Han, Han Cai（NVIDIA & MIT）｜ 2026-04，v3 2026-09

**一句话定位**：证明 OPD **可以完全离线化**，条件是满足一个此前被忽视的"教师一致性"约束。

**核心方法与关键发现**
- **问题**：OPD 需要**整个训练期间保持教师服务器在线**，基础设施开销巨大；
- **尝试**：能否把教师 log-prob **一次性预计算**在 SFT rollout 上，训练时复用？
- **发现**：**朴素地这样做无法可靠复现标准 OPD**，根因是一个此前被忽视的条件——**教师一致性（teacher consistency）**：**SFT 和 OPD 必须使用同一个教师**。违反该条件会引入**梯度偏差**，同时损害离线和在线 OPD；
- **Lightning OPD**：在此洞见上构建的离线 OPD 框架，**彻底消除对在线教师服务器的需求**；
- **理论保证**：在教师一致性下，Lightning OPD 与标准 OPD **共享同一最优解**，梯度差异有界，并具有**隐式正则效应**帮助防止策略漂移。

**关键结果**
- 数学推理与代码生成上，性能与标准 OPD 相当，**训练效率提升 4.0×**；
- 从 SFT 初始化的 Qwen3-8B-Base 出发，**仅用 30 GPU 小时**在 AIME 2024 达到 **69.9%**；
- 可扩展到 MoE：**单台 8×H100 节点**把 Qwen3-30B-A3B 训到 AIME 2024 **71.0%**。

**点评**：**这篇的最大价值是"把 OPD 的准入门槛从工业级降到学术级"**（单节点即可）。"教师一致性"这个发现尤其重要且反直觉：**很多团队做"两阶段强到弱蒸馏"（Qwen3 式）时，第一阶段的 SFT 教师与第二阶段 OPD 教师往往不是同一个，这正是性能对不上标准 OPD 的隐藏原因。**

---

#### 19. Prefix OPD：只蒸馏前缀，省 2×–47× 算力

**Fast and Effective On-policy Distillation from Reasoning Prefixes**
arXiv:2602.15260 ｜ Dongxu Zhang, Zhichao Yang, Sepehr Janghorbani, Jun Han, Andrew Ressler II, Qian Qian, Gregory D. Lyng, Sanjit Singh Batra, Robert E. Tillman｜ 2026-02

**一句话定位**：一个极其简单但有效的观察——**OPD 的训练信号集中在前缀**。

**核心方法与发现**
- **问题**：OPD 需要训练时在线采样学生策略，训练成本显著提高，**长回复尤甚**；
- **初步分析（两个关键观察）**：
  1. 在 OPD 过程中，**训练信号往往集中在每个输出的前缀部分**；
  2. **即使是很短的教师生成前缀，也能显著帮助学生产出正确答案**；
- **方法**：把蒸馏目标**只施加在学生生成输出的前缀上**，并在蒸馏时**提前终止采样**。

**关键结果**：AI-for-Math 套件与域外基准上，**on-policy 前缀蒸馏匹配完整 OPD 的性能，同时把训练 FLOP 降低 2×–47×**。

**点评**：**性价比最高的一篇。** 47× 的算力节省来自长推理链的指数级截断效应。但要注意它的边界条件：该方法依赖"信号集中在前缀"这一经验规律——对**前缀本身就走错**的任务（如需要长程规划、后期才出现关键分支的 Agent 任务）可能失效。综述提到的"forking tokens（分叉 token）"概念与此直接相关。

---

#### 20. NPD：异步生成 + 选择性打包，8.1× 加速

**Near-Policy: Accelerating On-Policy Distillation via Asynchronous Generation and Selective Packing**
arXiv:2605.05940 ｜ Miao Rang, Zhenni Bi, Hang Zhou, Kai Han, Xuechun Wang, An Xiao, Xinghao Chen, Yunhe Wang, Hanting Chen（华为诺亚方舟实验室）｜ 2026-05

**一句话定位**：把"生成"与"训练"解耦，从而能用标准 SFT 基础设施跑 OPD。

**核心方法**
- **问题**：标准自回归 KD 有分布错配；on-policy 方法缓解了它，但**依赖昂贵的 RL 框架**；
- **NPD**：一种**异步**方法，把**学生生成与训练解耦**。这一重构使得可以**用序列打包（sequence packing）的 SFT 方式**训练；
- **代价与对策**：异步更新不可避免地引入**策略滞后（policy lag）与样本噪声**，会让行为从"近策略"漂移向"离线策略"。为此 NPD 整合：
  1. **稀疏学生更新（sparse student updates）**；
  2. **Δ-IFD 过滤机制**——一个启发式样本选择机制，通过**过滤极端分布外样本**防止噪声主导梯度，确保更新留在安全的近端学习区内。

**关键结果**
- 相比 on-policy 基线取得 **8.1× 加速**，且**优于 SFT 8.09%**；
- 通过有效收窄后续 RL 的探索空间，使 **openPangu-Embedded-1B 达到 68.73% 的 SOTA 分数，超过体量大得多的 Qwen3-1.7B**。

**点评**：NPD 与 Lightning OPD 是"离线化 OPD"的两条不同路线：Lightning 走**预计算 log-prob**，NPD 走**异步流水线 + 样本过滤**。NPD 额外给出一个重要经验：**OPD 可以作为 RL 的"预热器"，通过收窄探索空间来提升后续 RL 的效率**——这与综述提到的"staged RL→OPD→RL"（Sparse-to-Dense）思路一致。

---

### F 组 · 黑盒、跨模态与工业落地（4 篇）

---

#### 21. GAD：没有 logits 也能做 on-policy 蒸馏

**Black-Box On-Policy Distillation of Large Language Models**
arXiv:2511.10643 ｜ Tianzhu Ye, Li Dong, Zewen Chi, Xun Wu, Shaohan Huang, Furu Wei（微软）｜ 2025-11，v3 2026-01

**一句话定位**：用**对抗训练**把黑盒教师的文本输出变成**随学生共同进化的 on-policy 奖励模型**。

**核心方法**
- **问题**：黑盒蒸馏只能从专有教师的**文本输出**学习，拿不到 logits 或参数；
- **GAD（Generative Adversarial Distillation）**：把学生 LLM 当作**生成器**，训练一个**判别器**区分学生回复与教师回复，形成**极小极大博弈**；
- **关键机制**：**判别器充当一个 on-policy 奖励模型，与学生共同进化**，提供稳定、自适应的反馈——从而在无 logits 条件下实现了 on-policy 蒸馏。

**关键结果**
- 一致超越常用的**序列级知识蒸馏**；
- 具体地：**Qwen2.5-14B-Instruct（学生）经 GAD 训练后，在 LMSYS-Chat 自动评测上可与它的教师 GPT-5-Chat 相媲美**。

**点评**：GAD 与 OVD 是黑盒路线的两种范式：**GAD 用对抗信号（隐式）**，**OVD 用语言化评分（显式）**。GAD 的理论吸引力在于"判别器即奖励模型"这一闭环；工程上需要注意对抗训练的稳定性问题（这也是判别器需要"共同进化"而非冻结的原因）。

---

#### 22. OVD：让黑盒教师"用嘴"给出分数

**OVD: On-policy Verbal Distillation**
arXiv:2601.21968 ｜ Jing Xiong, Hui Shen, Shansan Gong, Yuxin Cheng, Jianghan Shen, Chaofan Tao, Haochen Tan, Haoli Bai, Lifeng Shang, Ngai Wong（香港大学 & 腾讯混元）｜ 2026-01，v2 2026-09

**一句话定位**：**token 级 OPD 约束学生探索且必须拿到教师 token 概率**——OVD 用**语言化分数（verbal score）**绕开这两个限制。

**核心方法**
- **问题诊断**：token 级 OPD 有两个硬约束——（1）**限制学生探索**；（2）**需要教师的 token 概率**，从而**排除了从只给文本输出的黑盒教师蒸馏**；
- **OVD 框架**：用**黑盒教师的语言化分数**对**学生生成的子轨迹**排序，**保留高分者，用教师生成的续写替换低分者**；
- **理论分析**：作者分析了"由语言化分数诱导的排序"何时能指导分布逼近——在**接受概率的密度比校准条件**与**有界的教师替换误差**下，给出了所产生混合轨迹分布与"教师偏好目标分布"之间的**逼近误差上界**。

**关键结果**
- Web Q&A：**41.09% 平均 EM**（推理时带教师反馈），**超出最强评测基线 5.89 个百分点**；
- **AMC23**：OVD-FR 相比 RLVR 在 128 道题上训练 600 步后**提升 10.0 个百分点（52.5% → 62.5%）**；
- **保留学生生成的前缀有助于保持探索、缓解轨迹级熵塌缩**；
- 效率：只重采样选中的后缀而非整条回复，**平均每步训练时间降低 10.2%**（128 题设定）。

**点评**：OVD 的独特价值在于**它是"用自然语言接口做 OPD"**——这在实践中最贴近真实场景（你拿不到 GPT 的 logits，但你能让它打分）。它同时给出了理论保证（这是黑盒路线里少见的）。与 SKD 的对比很有意思：**SKD 用教师的 token 分布替换差 token，OVD 用教师的文本续写替换差子轨迹**——同一思想在黑白两个盒子里的两种实现。

---

#### 23. VOLD：把纯文本推理能力迁移到视觉语言模型

**VOLD: Reasoning Transfer from LLMs to Vision-Language Models via On-Policy Distillation**
arXiv:2510.23497 ｜ Walid Bousselham, Hilde Kuehne, Cordelia Schmid（Google Research & 图宾根大学等）｜ 2025-10，v3 2026-06

**一句话定位**：跨模态 OPD 的代表作——**用文本教师教 VLM 推理**，并证明"冷启动对齐"是前提条件。

**核心方法**
- **问题**：为 VLM 做复杂推理训练很难，因为**高质量图文推理数据稀缺**；而**文本推理资源丰富且可扩展**，但如何把它们用于 VLM 推理仍是开放问题；
- **VOLD**：把**纯文本教师**的推理能力迁移给 **VLM 学生**；
- **机制**：**GRPO 强化学习 + on-policy 蒸馏**结合，让学生推理轨迹受教师模型引导，相比单用 GRPO 有显著增益；
- **关键条件**：证明 **cold-start 对齐对在线训练阶段的有效迁移是必需的**；**若师生之间缺乏足够的分布对齐，on-policy 蒸馏无法提供有意义的指导**。

**关键结果**：在 MMMU-Pro、MathVision、MathVista、LogicVista 等基准上显著优于基线并**超越当时的 SOTA**；消融实验确认了**通过 SFT 做冷启动对齐对"纯文本教师 + OPD"的重要性**。

**点评**：**"冷启动对齐必需"这个结论是整个领域的通用规律**，在 Rethinking OPD（off-policy cold start）、AOPD（弱初始化下增益更大）、Speculative KD（师生鸿沟）中都反复出现。VOLD 把它放在**跨模态**这个最极端的分布鸿沟上验证，说服力最强。对做多模态后训练的团队，这是必读。

---

#### 24. MiMo-V2-Flash：把 OPD 做成工业级后训练范式（MOPD）

**MiMo-V2-Flash Technical Report**
arXiv:2601.02780 ｜ Xiaomi LLM-Core Team（小米）｜ 2026-01

**一句话定位**：目前**最完整的工业级 OPD 落地报告**——309B MoE 模型，用**多教师 on-policy 蒸馏（MOPD）**作为后训练核心。

**模型与 OPD 相关要点**
- **模型规模**：MoE，**309B 总参数 / 15B 激活参数**；混合注意力（滑窗 128 token + 全局注意力，5:1 比例）；27T token 预训练，原生 32k 上下文，扩展至 256k；
- **后训练核心创新 —— MOPD（Multi-Teacher On-Policy Distillation）**：为高效扩展后训练算力，采用多教师 OPD 范式。**领域专用教师（例如通过大规模 RL 训练的）提供稠密的 token 级奖励**，使学生模型能够**完整掌握教师专长**；
- **推理侧**：把 MTP 层复用为投机解码的 draft 模型，3 层 MTP 下达到**最高 3.6 的接受长度与 2.6× 解码加速**。

**关键结果**
- 尽管总参数只有 DeepSeek-V3.2 的 1/2、Kimi-K2 的 1/3，**性能与二者相当**；
- 开源模型权重与三层 MTP 权重。

**点评**：MiMo-V2-Flash 印证了综述的判断——**OPD 已从"一种蒸馏技巧"升级为"多能力整合的后训练基础设施"**。它的 MOPD 结构解决了多领域 RL 的经典难题（Mix-RL 的跷跷板效应、参数合并的能力稀释）：**教师保持独立、知识在 logit 空间流动，因此互不干扰**。同团队在 arXiv:2606.30406 中给出了 MOPD 的完整方法论论文（Qwen3-30B-A3B 上优于 Mix-RL / Cascade RL / Off-Policy Finetune / Param-Merge，且已部署于 MiMo-V2-Flash）。

---

## 3. 趋势总结与关键结论

### 3.1 已经收敛的共识

1. **反向 KL 是推理任务的默认选择**，但**不是万能的**——教师熵高时需要前向 KL 兜底（Entropy-Aware OPD），非正优势区域用局部散度替代负强化更好（AOPD）。
2. **冷启动对齐是硬前提**。师生分布差距过大时，OPD 会直接失效（Rethinking OPD、VOLD、AOPD 三处独立验证）。标准做法是先做一轮 off-policy SFT。
3. **OPD ≡ 稠密 KL 约束 RL 的特例**（G-OPD）。这一等价关系让 RL 的全部方差降低技术（基线、优势、裁剪）合法移植，vOPD 是首个成功案例。
4. **不需要"更大的同族教师"**。同族 1.5B 与 7B 教师从学生视角分布上不可区分（Rethinking OPD）；真正需要的是**新能力**或**特权信息**。
5. **教师一致性（teacher consistency）**：SFT 与 OPD 必须用同一个教师，否则引入梯度偏差（Lightning OPD）。
6. **OPD 在参数空间自成一类几何**：off-principal 更新 + 低维子空间锁定，这可能是它抗遗忘的几何解释（Geometry of OPD）。

### 3.2 尚未解决的问题

| 问题 | 现状 | 代表工作 |
|---|---|---|
| **蒸馏缩放律** | 无统一框架预测 OPD 质量如何随 N_T、N_S、D、rollout 预算 R 缩放；指数 α/β/γ/δ 未知 | Survey 2604.00626 |
| **教师不确定性** | 白盒 OPD 的 flawed prefix 问题未根治；黑盒路线刚开始处理 | SKD、OVD、Revisiting OPD |
| **Agent 级长程蒸馏** | 单轮生成已较成熟，多步 Agent 轨迹的信用分配仍开放；长程 OPD 的成本随序列长度线性增长 | π-Distill、TIP、Survey |
| **测试时行为的反转** | OPD 可能提升小采样预算表现却**降低大采样预算的 pass@K**（即使教师每题都更准） | 2608.11829 |
| **能力 vs 校准的解耦** | OPD 可能提升能力却损害校准（The Illusion of Certainty, 2604.16830） | 2604.16830 |
| **KD 与 RL 的融合边界** | 两者共享基础设施，"OPD 取代 RL"还是"OPD 服务 RL"尚无定论 | G-OPD、NPD、Sparse-to-Dense |

### 3.3 对实践者的行动建议

1. **动手前先做三件事**：确认教师有学生没有的新能力 / 特权信息；做一轮冷启动 SFT 对齐；跑 Revisiting OPD 的三个失败模式检查（token 不均衡、教师前缀不可靠、tokenizer 不匹配）。
2. **默认加上 vOPD 的基线**——闭式解、零额外开销、保持无偏。
3. **算力紧张就上 Prefix OPD**（2×–47× 节省）；**没有教师服务器就上 Lightning OPD**（4× 且单节点可达 AIME 24 69.9%）。
4. **多能力整合优先考虑 MOPD 式多教师**，而非参数合并或 Mix-RL。
5. **黑盒教师场景**：需要理论保证用 OVD，追求性能上界用 GAD。

---

## 4. 延伸阅读清单（30 篇，按主题）

| 主题 | 论文 | arXiv |
|---|---|---|
| 理论/现象 | On-Policy Self-Distillation 简报 | 2605.18141 |
| 理论/现象 | 后训练的本质是状态分布而非 token | 2605.22731 |
| 理论/现象 | OPD 的稀疏性与几何 | 2606.13657 |
| 理论/现象 | 通过测试时缩放理解 OPD（pass@K 反转、TAS@K） | 2608.11829 |
| 理论/现象 | OPD 的泛化二重性 | 2608.16647 |
| 目标函数 | 自蒸馏的通用框架 UniSD | 2605.06597 |
| 目标函数 | OPD+：重新思考优势设计 | 2606.01039 |
| 目标函数 | 逃离 KL 一致性陷阱 | 2606.09471 |
| 目标函数 | 重新思考反向 KL：作为自适应熵蒸馏 | 2608.14685 |
| 自蒸馏 | GATES：共识门控的特权上下文自蒸馏 | 2602.20574 |
| 自蒸馏 | SD-Zero：自我修订把二值奖励变稠密监督 | 2604.12002 |
| 自蒸馏 | 思维塌缩的诊断与缓解 | 2607.10805 |
| 自蒸馏 | 特权但有偏：PI 条件化教师如何破坏自蒸馏 | 2608.04794 |
| 自蒸馏 | 无任何监督的 on-policy 自蒸馏 | 2608.06296 |
| Token 级 | TIP：OPD 中的 token 重要性（熵 × 散度二维分类） | 2604.14084 |
| Token 级 | 重新审视采样 token 反向 KL 的 token 级分析 | 2608.25643 |
| 效率/系统 | OPD 的 token 重要性加权 TIP | 2604.14084 |
| 效率/系统 | 异步 OPD 能"陈旧"到什么程度 | 2606.24143 |
| 效率/系统 | 差分隐私 OPD（DP-OPD） | 2604.04461 |
| 效率/系统 | 无 logit 的 OPD（投机验证）OmniOPD | 2606.01476 |
| 多教师 | MOPD：能力整合的多教师 OPD | 2606.30406 |
| 多教师 | CoPD：共同进化的策略蒸馏 | 2604.27083 |
| 多教师 | 开放 MOPD：多教师 OPD 的能力不平衡诊断 | 2608.19098 |
| 黑盒 | 黑盒 OPD（GAD） | 2511.10643 |
| 跨模态 | X-OPD：语音 LLM 的跨模态 OPD | 2603.24596 |
| 跨模态 | Video-OPD：时序视频定位的 MLLM 后训练 | 2602.02994 |
| 扩散/流 | Flow-OPD：流匹配模型的 OPD | 2605.08063 |
| 扩散/流 | AnyFlow：任意步视频扩散的 OPD | 2605.13724 |
| 安全 | 宪法式 on-policy 安全蒸馏 | 2606.03089 |
| 上下文/经验 | 在线经验学习（OEL） | 2603.16856 |
| 工业报告 | DeepSeek-R1 蒸馏（671B MoE → 1.5B–70B） | 2501.12948 |
| 工业报告 | Qwen3 技术报告（两阶段强到弱蒸馏） | 2505.09388 |
| 工业报告 | GLM-5 技术报告（跨阶段 OPD 收尾） | 2602.15763 |

### 资源入口

- **综述配套仓库**：github.com/nick7nlp/Awesome-LLM-On-Policy-Distillation
- **最全的论文索引**：github.com/chrisliu298/awesome-on-policy-distillation（按 Foundations / Gap-Bridging / Stability / Self-Distillation / Context 等 6+ 大类组织，收录 250+ 篇）
- **多模态 OPD 专项**：github.com/miracle-techlink/opd-papers
- **可读性最好的入门笔记**：yaoyuanzhou.github.io/topics/notes-opd.html（含 Forward vs Reverse KL 的双峰高斯直观解释、四大工业实现对比表）
- **OPD 官方代码库（THUNLP）**：github.com/thunlp/OPD

---

## 附录：24 篇主论文速查表

| # | 论文 | arXiv | 组 | 关键词 |
|---|---|---|---|---|
| 01 | MiniLLM | 2306.08543 | A | 反向 KL 起点 |
| 02 | GKD | 2306.13649 | A | 通用框架 + RL 集成 |
| 03 | DistiLLM | 2402.03898 | A | Skew KL，4.3× 加速 |
| 04 | Speculative KD | 2410.11325 | A | 交错采样，缺陷前缀 |
| 05 | OPD Survey | 2604.00626 | B | f-散度统一框架 |
| 06 | Rethinking OPD | 2604.13016 | B | 两条件判据，97–99% token 集 |
| 07 | Geometry of OPD | 2606.07082 | B | 子空间锁定 |
| 08 | OPSD | 2601.18734 | C | 同模型特权信息师生 |
| 09 | SDPO | 2601.20802 | C | 丰富反馈 → 稠密信号 |
| 10 | SDFT | 2601.19897 | C | 示范持续学习 |
| 11 | π-Distill | 2602.04942 | C | 动作级 PI 蒸馏 Agent |
| 12 | OPCD | 2602.12275 | C | 上下文/系统提示内化 |
| 13 | G-OPD / ExOPD | 2602.12125 | D | OPD ≡ KL-RL，超越教师 |
| 14 | Entropy-Aware OPD | 2603.07079 | D | 高熵处加 FKL |
| 15 | Revisiting OPD | 2603.25562 | D | 三失败模式，+19.8% |
| 16 | AOPD | 2605.06387 | D | 非对称，弱初始化 +8.34 |
| 17 | vOPD | 2605.07865 | D | 控制变量基线（闭式） |
| 18 | Lightning OPD | 2604.13010 | E | 离线化，教师一致性，4× |
| 19 | Prefix OPD | 2602.15260 | E | 仅前缀，省 2×–47× |
| 20 | NPD | 2605.05940 | E | 异步 + 打包，8.1× |
| 21 | GAD（黑盒 OPD） | 2511.10643 | F | 对抗式 on-policy 奖励 |
| 22 | OVD | 2601.21968 | F | 语言化分数，黑盒 |
| 23 | VOLD | 2510.23497 | F | LLM→VLM，冷启动必需 |
| 24 | MiMo-V2-Flash | 2601.02780 | F | 工业级 MOPD |

---

*报告完 · 生成于 2026-09-30*
