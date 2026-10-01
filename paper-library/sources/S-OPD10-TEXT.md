# OPD近期顶会十篇：Meta-method v0.4.0逐篇贡献拆解

日期：2026-09-30。框架固定为v0.4.0 / `0631fa06e01fa345fb90b57727342d2f82279c0c`。

## 范围与阅读边界

这是一组本轮检索并核验到的近期主会已发表／已录用论文，按首次arXiv提交时间倒序编号；不声称完成了整个领域的穷尽普查。A表示正式论文集，B表示作者或机构明确录用记录，后者不冒充已经出版的论文集。Workshop、Findings和仅预印本不混入主会身份。

使用此前24篇报告作为发现线索，但主会身份重新核验。分析基于公开版本的摘要、核心方法、部分结果、相关消融和局限；没有复现模型训练、独立全面核查证明、作第二编码者复核或推送GitHub。方法版本与最终录用版本可能不同，逐条注明。

作者码记录原文呈现的贡献动作，不推断作者真实发现时间顺序。审查意见与后续提案分别保存；单次来源锚定不证明操作卡具有跨任务生成效果。所有案例是开发材料。

## 编号

| 编号 | 首次公开 | 论文 | 会议 | 身份依据 |
|---|---|---|---|---|
| OPD-T01 | 2026-08-21 | [SecOPD](https://arxiv.org/html/2608.21500v1) | EMNLP 2026 Main | [B](https://pppyb.github.io/) |
| OPD-T02 | 2026-06-04 | [ViCuR](https://arxiv.org/html/2606.05718v1) | EMNLP 2026 Main | [B](https://github.com/tiankanghui/ViCuR) |
| OPD-T03 | 2026-06-01 | [SafeSteer](https://arxiv.org/html/2606.02530v2) | EMNLP 2026 Main (Oral, author project announcement) | [B](https://anjingkun.github.io/SafeSteer/) |
| OPD-T04 | 2026-05-30 | [Decomposed OPD / VGS](https://arxiv.org/html/2606.00564v1) | ICML 2026 | [A](https://proceedings.mlr.press/v306/yoon26f.html) |
| OPD-T05 | 2026-05-20 | [PW-OPSD](https://arxiv.org/html/2605.21606v1) | NeurIPS 2026 (author repository acceptance announcement) | [B](https://github.com/SaFo-Lab/PW-OPSD) |
| OPD-T06 | 2026-05-10 | [Rock Tokens](https://arxiv.org/html/2605.09253v4) | NeurIPS 2026 (author announcement) | [B](https://yuxuanjiang1.github.io/) |
| OPD-T07 | 2026-04-22 | [HPD](https://arxiv.org/html/2604.20244v2) | ICML 2026 | [A](https://proceedings.mlr.press/v306/zhu26av.html) |
| OPD-T08 | 2026-03-11 | [REOPOLD](https://arxiv.org/html/2603.11137v1) | NeurIPS 2026 (Microsoft Research publication record) | [B](https://www.microsoft.com/en-us/research/publication/relaxed-on-policy-distillation-selective-credit-allocation-for-scaling-reasoning-efficiently/) |
| OPD-T09 | 2026-03-07 | [Entropy-Aware OPD / EOPD](https://arxiv.org/html/2603.07079v3) | ICML 2026 | [A](https://proceedings.mlr.press/v306/jin26e.html) |
| OPD-T10 | 2026-02-03 | [Video-OPD](https://arxiv.org/html/2602.02994v3) | ICML 2026 | [A](https://proceedings.mlr.press/v306/li26im.html) |

## OPD-T01 — SecOPD: Mitigating Adaptive Prompt Injections by On-Policy Distillation

原文：[2608.21500v1](https://arxiv.org/html/2608.21500v1)。作者操作暂定：**M6 / M2**。

**原有局限：**序列级偏好或结果奖励难以对同时包含合法回答与注入任务的混合输出分配信用。

**作者改变了什么：**学生在受污染输入上生成；冻结的初始化模型在对应干净输入上，对同一条学生轨迹逐token评分。改变的是教师的条件信息，而非必需更换成更大模型。

**为什么不只是A+B：**把“移除注入时会怎样回答”的跨上下文参照转为细粒度学习信号。增量是反事实式教师构造与任务保留的信用分配，不只是安全数据加OPD。

**原文证据：**原文比较相同训练数据上的多种对齐方法，包含自适应攻击与AgentDojo迁移。Qwen3.6-27B的PISmith设置报告pass@10攻击成功率从Meta-SecAlign的94.0%降至9.0%；该数字只对应其评测协议。

**审计边界，不等于已证明的缺陷：**干净输入不等于干净生成前缀。教师仍条件于学生已经生成的z_<t；输入威胁移除不能保证教师对任意偏离轨迹都可恢复。后者是待检验边界，不是本次已证实的失败。

**可生成的候选方向：**研究跨上下文教师信号在输出前缀受污染后的有效范围。

**最小判别证据：**固定任务与深度，准备正常、局部错误及已偏离任务的无害封闭轨迹；比较干净输入教师的独立任务恢复率与逐token反馈方向，再决定是否需要前缀修复。

**结果—行动：**若只清理输入已经稳定提供有效反馈，保留原简单方案。 若只有部分前缀导致反馈失真，再针对前缀或上下文构造修复，不先堆叠新奖励模型。

原文定位：§3.2–3.3: sequence-level versus token-level signals；§4.1–4.2: paired inputs and shared generated prefix；§5–6: attack, utility, transfer evaluation。

## OPD-T02 — ViCuR: Visual Cues as Recoverable Privilege for Multimodal On-Policy Distillation

原文：[2606.05718v1](https://arxiv.org/html/2606.05718v1)。作者操作暂定：**M6 / M12 / M9**。

**原有局限：**答案或推理轨迹型特权信息增强教师，却可能让监督依赖部署学生看不到的信息。

**作者改变了什么：**将特权信息改成图像与问题中的视觉线索，并在学生prefill阶段使用sink-token交叉注意力恢复相关证据；推理输入接口不增加显式cue。

**为什么不只是A+B：**同时改变教师优势的来源和学生吸收它的接口。其理想化S=f(X)分析对应可恢复信息，而非只把答案提示换成描述提示。

**原文证据：**七个多模态基准上，视觉cue与恢复模块具有组件比较；相对对应OPSD基线，2B/8B平均提高1.19/1.24点，相对对应OPD提高0.64/1.08点。

**审计边界，不等于已证明的缺陷：**S=f(X)仅说明理想信息条件，不保证有限容量与预算下能计算f。学生结构增加模块，prefill有额外成本；8B的OPSD+ViCuR均值仍低于该初始模型，不能写成全部能力无损。主会身份来自官方repo 2026-08-21公告，v1的旧投稿页眉不作最新状态。

**可生成的候选方向：**刻画特权信息的“信息上可恢复”与“计算上可学习”之间的迁移边界。

**最小判别证据：**构造教师帮助程度、长度相近，但从输入提取难度不同的视觉线索；用相同学生预算比较恢复能力与任务收益。先验证可恢复性诊断能否预测收益，再增加结构。

**结果—行动：**若难度指标不改变教师或接口选择，不把它扩成新方法。 若固定预算下存在稳定迁移边界，再研究cue选择或学习路径，而不是把更多外部答案直接放进teacher。

原文定位：§3.1: recoverable privilege and deterministic abstraction；§3.2–3.4: architecture and training；§4, Appendix ablations and latency: matched baselines and overhead。

## OPD-T03 — SafeSteer: Localized On-Policy Distillation for Efficient Safety Alignment

原文：[2606.02530v2](https://arxiv.org/html/2606.02530v2)。作者操作暂定：**M6 / M2 / M3**。

**原有局限：**由拒绝方向构造的强安全教师会同时拒绝无害请求；整体模仿它可能损害通用能力。

**作者改变了什么：**对教师激活注入拒绝方向，利用无害校准输入提取其相对基础模型更倾向的安全token集合；对有害输入上的学生轨迹，只在该词表子集上施加蒸馏项。

**为什么不只是A+B：**教师不必整体适于部署：从一个全局偏置的教师中提取局部有用行为。贡献在选择性知识转移，而不是简单steering+KD。

**原文证据：**四个模型、七项安全与五项通用基准，并比较全词表蒸馏、不同教师构造和选择方式。论文以少量有害训练样本实现明显安全改善。

**审计边界，不等于已证明的缺陷：**“100个有害训练样本”不等于所有阶段总共只使用100条数据；无害Alpaca用于token提取。词表子集损失不代表其他token或共享参数不会改变，也不是安全零税的理论保证。

**可生成的候选方向：**研究局部监督应该按全局token身份，还是按该token在当前任务中的功能选择。

**最小判别证据：**匹配词表规模、采样预算与更新范数，在需要相同措辞的合法请求和不同表述的违规请求上比较固定token集合与上下文条件集合。先做冻结策略的行为校准，再做小规模学习。

**结果—行动：**若上下文条件化没有独立收益，保留固定集合。 若同一token在不同合法功能中存在系统性误转移，再引入功能条件，不依据词表稀疏性宣称参数局部性。

原文定位：§3.1: teacher rejects harmful and harmless instructions；§3.2–3.3: harmless calibration and token selection；§3.4 and experiments: restricted objective and utility evaluation。

## OPD-T04 — Decomposed On-Policy Distillation for Vision-Language Reasoning: Steering Gradients for Visual Grounding

原文：[2606.00564v1](https://arxiv.org/html/2606.00564v1)。作者操作暂定：**M2 / M9 / M1**。

**原有局限：**一个整体的多模态蒸馏目标同时要求语言先验匹配与视觉依据匹配，却不显式区分两者。

**作者改变了什么：**通过条件概率分解构造语言与视觉信息增益目标；分析梯度几何，再用VGS增强视觉方向并在相关情形加入语言保持项。

**为什么不只是A+B：**从“模仿整个教师”转向“保留学生语言先验，吸收教师的视觉条件增量”。新增的是可计算的目标分解及有针对性的更新控制。

**原文证据：**原文给出Bayes分解与局部可计算目标、梯度分析及多模态任务比较；附录报告单步时间约为标准OPD的1.375倍。

**审计边界，不等于已证明的缺陷：**某些参数点梯度近正交不等于功能或因果独立；视觉是主要瓶颈也是有范围的假说。单步额外成本需进入总预算，不将论文的minimal overhead解释为免费。

**可生成的候选方向：**研究何时应优先视觉、何时应保护或加强语言推理，而非一律增强某一分量。

**最小判别证据：**使用视觉证据不足、视觉证据清楚但推理复杂等可核验任务，固定训练预算，检验独立诊断能否预测不同更新分配的收益。

**结果—行动：**若视觉优先已覆盖目标分布，不强加自适应门控。 若诊断稳定预测分配反转，再发展按错误来源配置更新的规则。

原文定位：§3.1: Eq.5–10 objective construction；§3 gradient geometry; §4 VGS and language preservation；Appendix C: computation and overhead。

## OPD-T05 — When Are Teacher Tokens Reliable? Position-Weighted On-Policy Self-Distillation for Reasoning

原文：[2605.21606v1](https://arxiv.org/html/2605.21606v1)。作者操作暂定：**M7 / M1**。

**原有局限：**局部熵等指标描述歧义，却不直接回答教师提出的分支能否由普通学生继续走向正确答案。

**作者改变了什么：**用privileged teacher提出分支，在不含参考答案的学生上下文中续写检验branch viability；据此对完整轨迹采用随相对位置增加的权重，早期权重不为零。

**为什么不只是A+B：**先把“可靠”改写为可操作的分支成功，再压缩成低成本的位置先验。不是因为换一个sigmoid函数就构成创新。

**原文证据：**诊断对位置与若干不确定性指标作比较；训练使用保持学生rollout的前向KL型OPSD目标，在三个模型和数学基准上报告收益。Avg@12与Pass@12分别定义，不能互换。

**审计边界，不等于已证明的缺陷：**诊断使用成功spine，不能自动代表全部失败前缀。归一化位置可能关联剩余推理步数；额外诊断开销与无额外训练teacher pass是两回事。

**可生成的候选方向：**区分绝对位置、剩余决策距离与分支本身可靠性，形成比“越晚越可信”更有范围的规律。

**最小判别证据：**在可控制关键事件位置的任务中，分别改变前置长度与剩余必要决策数；续写仍使用普通学生上下文，匹配评估机会。

**结果—行动：**若位置效应由剩余决策距离解释，收窄结论并尝试事件级调度。 若简单位置先验已稳定有效，不为形式上的复杂性增加新评分器。

原文定位：§2 and branch-viability diagnostic: correct spines and student continuation；§3.1: clipped forward-KL surrogate；§3.2–3.3: position weights; limitations: scope and modest gains。

## OPD-T06 — Cornerstones or Stumbling Blocks? Deciphering the Rock Tokens in On-Policy Distillation

原文：[2605.09253v4](https://arxiv.org/html/2605.09253v4)。作者操作暂定：**M1 / M7 / M10**。

**原有局限：**少量高频、跨上下文持续难匹配的token占据大量蒸馏损失；高损失未必表示它们值得继续集中优化。

**作者改变了什么：**结合频率、跨上下文一致性、训练持续性分析Rock Tokens；将损失表现与推理时token类型干预区分，再研究训练预算重分配。

**为什么不只是A+B：**改变token重要性的判断依据，从“拟合困难”转向“功能作用与可改善空间”。解释性诊断可独立构成贡献，训练配方是进一步产物。

**原文证据：**原文包含梯度几何、训练前后KL、推理敲除与重加权实验。附录明确：200个候选token的个体Pillar识别经Bonferroni/BH校正后均未保留，个体标记是探索性的。

**审计边界，不等于已证明的缺陷：**推理阶段禁止一个token类型，与训练阶段减小该token的损失权重是不同干预。相关性不显著不证明完全独立；优化器二阶矩解释在文中仍为假说。

**可生成的候选方向：**研究同一结构token在自然语言解释、精确格式输出和代码等任务中如何改变训练价值。

**最小判别证据：**先固定token身份，改变是否需要严格格式等任务契约，独立比较推理可替代性和同预算训练权重效应；不直接建立永久token黑名单。

**结果—行动：**若无效性只在宽松格式下成立，报告任务边界。 若上下文功能显著预测训练收益，再建立功能条件重分配；不能靠无显著敲除效应证明可安全删除。

原文定位：§2: definition, context consistency and gradient geometry；§3: inference-time type-level knockout and training interventions；Appendix D.1–D.2: correlations and multiple-testing limits。

## OPD-T07 — Hybrid Policy Distillation for LLMs

原文：[2604.20244v2](https://arxiv.org/html/2604.20244v2)。作者操作暂定：**M9 / M2 / M3**。

**原有局限：**散度方向、估计形式和数据来源经常捆绑改变，使方法比较难以定位究竟在改变什么。

**作者改变了什么：**统一为加权token对数似然，区分专家token和学生采样的非专家token；按高估/低估情况有选择地使用正负更新。主配方在离线前缀下做轻量学生token采样，另有完整on-policy实验。

**为什么不只是A+B：**并非固定系数FKL+RKL：明确控制抑制某token后概率质量应向哪里移动，同时节省完整rollout成本。

**原文证据：**原文提供统一推导、梯度与权重机制，覆盖数学、对话和代码任务；§5.4另检验on-policy设置。

**审计边界，不等于已证明的缺陷：**离线前缀上的学生token采样不等于当前学生完整轨迹；局部修正不能自动证明已解决状态分布偏移。这是近似适用范围，而不是作者暗称严格on-policy。

**可生成的候选方向：**在固定总成本下，区分何时只需刷新token分布，何时必须刷新状态/前缀。

**最小判别证据：**比较专家前缀、旧学生前缀和当前学生前缀上的局部更新价值；随后只对状态失配严重部分追加rollout，并和均匀刷新在相同总成本下比较。

**结果—行动：**若状态刷新不能改善独立结果，保留轻量近似。 若相同局部损失却发生部署失败，研究状态选择接口而非再混合一个散度。

原文定位：§4.1: reweighted likelihood view；§4.2 Eq.11–13: expert/non-expert token weighting and offline prefixes；§5.4: on-policy evaluation。

## OPD-T08 — Relaxed On-Policy Distillation: Selective Credit Allocation for Scaling Reasoning Efficiently

原文：[2603.11137v1](https://arxiv.org/html/2603.11137v1)。作者操作暂定：**M1 / M9 / M3**。

**原有局限：**稠密token反馈仍可能有重尾负信号、无效更新与探索受限，并非密度越高就越值得全部利用。

**作者改变了什么：**对教师/学生log-ratio反馈设置有推导依据的下限，并用先奖励过滤、后熵筛选的阶段化策略分配更新；默认算法使用预设T_switch。

**为什么不只是A+B：**放松的是“每个位置都严格追随教师”，同时控制更新信号强度、位置与阶段。并非直接将PPO clipping原样搬来。

**原文证据：**原文比较组件、任务与师生配置，报告相对RL基线的样本效率收益。样本效率倍数不等于相同倍数的端到端GPU时间节省。

**审计边界，不等于已证明的缺陷：**机构录用标题与所读arXiv v1标题不同，本文只分析该公开版本。阶段切换是超参数，不写成已实现自动阶段发现；减小噪声、删减信息和改变目标需区分。

**可生成的候选方向：**识别选择性更新的收益究竟来自信息选择，还是更小的有效步长与更少更新。

**最小判别证据：**固定batch及token保留率，匹配更新范数/学习率后比较规则选择与随机选择；观察持出任务和不同负尾分布中的稳定收益。

**结果—行动：**若范数匹配后优势消失，优先简化优化设置。 若选择规则仍有独立收益，再研究跨任务的阶段触发，而非假定固定切换步数普适。

原文定位：arXiv v1 title: Scaling Reasoning Efficiently via Relaxed On-Policy Distillation；§3–4; Eq.4–6 and Algorithm 1；§4.1: mixture-inspired clipping; experiments and component ablations。

## OPD-T09 — Entropy-Aware On-Policy Distillation of Language Models

原文：[2603.07079v3](https://arxiv.org/html/2603.07079v3)。作者操作暂定：**M1 / M2**。

**原有局限：**在教师高熵位置，单纯reverse-KL配方可能产生不稳信号并损失多样输出覆盖。

**作者改变了什么：**保留原OPD目标，在教师熵超过阈值的位置加入forward KL；不是在高熵处完全替换原项，也不是全部位置固定混合。

**为什么不只是A+B：**根据诊断得到的条件区域改变目标配置，把不同散度的作用落实到“在哪些状态使用”。

**原文证据：**六个数学基准上，三个Qwen3 Base规模的平均Pass@8提高1.37、2.39和5.05点；原文已比较随机位置加FKL、全位置FKL、熵正则等对照。

**审计边界，不等于已证明的缺陷：**教师高熵可能来自多种正确续写，也可能来自不知道如何继续；token熵不是策略多样性或任务正确性的同义词。某一规模增益更大不证明一般缩放定律。

**可生成的候选方向：**区分“多种正确答案导致的高熵”和“信息不足导致的高熵”，检验覆盖性蒸馏何时有用。

**最小判别证据：**构造熵相近但教师正确续写质量不同的固定前缀，使用独立验证器评价覆盖；先检验额外可靠性条件能否改变蒸馏选择，再考虑联合门控。

**结果—行动：**若可靠性条件不能改进选择，保留原熵门控。 若同熵不同质量导致相反训练收益，研究条件目标，但不把堆叠更多不确定性指标当作贡献。

原文定位：§3–4: high entropy and conditional forward-KL augmentation；§5: six mathematics benchmarks；§5.5–5.8: random/full FKL, entropy regularization and baselines。

## OPD-T10 — Video-OPD: Efficient Post-Training of Multimodal Large Language Models for Temporal Video Grounding via On-Policy Distillation

原文：[2602.02994v3](https://arxiv.org/html/2602.02994v3)。作者操作暂定：**M6 / M5 / M3**。

**原有局限：**视频时间定位依赖较稀疏的终局奖励；教师会出错，因此只选择师生分歧最大的样本也可能放大错误指导。

**作者改变了什么：**以学生轨迹上的token监督替代部分稀疏结果反馈；TVDF先用真实时间标注检查教师定位可靠性，再按师生分歧安排训练。

**为什么不只是A+B：**把标注从直接训练答案，改用为教师可信性的筛选信号；不同来源的反馈承担不同职责。不是仅将语言OPD换成视频输入。

**原文证据：**在Charades-TimeLens、ActivityNet-TimeLens和QVHighlights-TimeLens上比较任务表现与成本；已有教师可靠性/分歧优先的组件消融。

**审计边界，不等于已证明的缺陷：**基础OPD可不依赖时间标注，但TVDF增强配方用标注作为validation oracle；不能称整套方法无标注。训练前教师验证调用和筛选偏向也应进入成本/覆盖分析。

**可生成的候选方向：**在教师验证与标注预算有限时，学习何时值得购买可靠性证据，而非假设所有样本都已有oracle。

**最小判别证据：**冻结候选池与总教师/验证预算，对比均匀验证、按分歧验证和考虑覆盖的验证；独立报告长视频、稀有事件与高难样本表现。

**结果—行动：**若验证成本超过训练收益，简化课程。 若筛选提升均值却丢失关键事件，改写覆盖约束；只有改变独立结果才升级为新方法。

原文定位：§3.1: on-policy reverse-KL training；§3.2: TRPV and DBTP, temporal annotation oracle；§4.3 and §5: ablations, efficiency and teacher comparisons。

## 跨论文沉淀

1. 教师优势可以来自不同的信息或内部行为条件，而不只来自模型规模。SecOPD、ViCuR和SafeSteer分别改变干净上下文、可恢复线索和激活偏置；它们需要验证不同的转移条件。
2. 单一蒸馏损失可以拆成具有不同任务含义或不同学习价值的对象。VGS与HPD的贡献并非只增加一个正则项，而是说明在什么对象、条件和采样下进行更新。
3. token熵、持续损失、位置、分支存活率、教师验证和梯度大小不是可互换的重要性指标。PW-OPSD、Rock Tokens、EOPD、REOPOLD及Video-OPD显示了不同选择问题；不能据此构造一个无证据的全能评分器。
4. 最有价值的下一步，是检验一个诊断是否改变教师、训练对象、采样或预算决策，并用独立任务确认。不是把这十个方法全部拼接。

建议优先考虑：教师指导的可恢复性与有限预算可学习性；token在推理中可替代与训练中有用的区别；前缀状态刷新与局部token修正的资源分工。上述均为本轮候选提案，尚未完成穷尽查新或前瞻验证。

## 不混入主名单的材料

Prefix OPD被明确列于ACL 2026 Findings；CoDistill-GRPO的作者页面列为ICML 2026 AdaptFM workshop。新预印本或主会赛道尚未确认的候选保留在JSON登记中，不据此断言其未获录用。

本文件的数字均为原文报告或已检索的元数据，没有新增训练或数值实验。更详细的来源与状态见`paper_register.json`。
