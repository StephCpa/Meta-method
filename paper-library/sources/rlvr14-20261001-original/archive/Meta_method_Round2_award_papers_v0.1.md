# Meta-method Round 2：跨领域获奖论文首轮对照登记 v0.1

核对日期：2026-09-30。

## 范围与证据状态

这是一组覆盖七个会议的14篇分层探索样本，不是“所有会议最近两届获奖论文”的完整普查。奖项按授奖会议年份记录，而非 arXiv 首发年份。
原计划按各会议最新两届已公布奖项取样；本轮 ICML 2026、KDD 2026 获奖名单尚未完成可靠核验，所以不宣称完整覆盖2025—2026，也不以2024自动替代未核验届次。2024论文在登记中明确标注。
Best Paper、Outstanding、Honorable Mention、Runner-Up、Applied Data Science和Dataset/Benchmark奖分别保留。时间检验奖、个人奖、竞赛奖不混入。
本轮以官方奖项/会议论文/作者原文为依据，核对主要研究对象与关键证据段；没有复现原实验，也没有完整验证所有证明。编码均为分析提案，不是客观标签或研究发现顺序。
这些样本已用于修订框架，后续不能再次充当未见的确认集。

## 样本登记

### A01｜Transformers are Inherently Succinct
- 会议与奖项：ICLR 2026 — Outstanding Paper
- 问题领域：形式语言与表达复杂度
- 候选编码：M9 主；M2/M11 辅
- 关键研究动作：从能否表达，改为表达同一语言需要多少描述规模；定理使用特定 Transformer 模型，不能外推成任意部署模型结论。
- 对框架的压力测试：理论证明与复杂度边界即可构成终点，不强制要求 GPU 实验。
- 阅读/核验深度：摘要、关键定理和结论段；未逐项完成证明复核
- 原论文来源：https://arxiv.org/html/2510.19315v1
- 奖项来源：https://blog.iclr.cc/2026/04/23/announcing-the-iclr-2026-outstanding-papers/

### A02｜SAM 2: Segment Anything in Images and Videos
- 会议与奖项：ICLR 2025 — Honorable Mention
- 问题领域：视觉系统与数据生产
- 候选编码：M8 主；M5/M6/M12 辅
- 关键研究动作：模型、流式记忆、交互标注与数据引擎共同构造新能力。原文已有标注流程对照及独立评价设计。
- 对框架的压力测试：系统可以先构造出可观测对象；不能将数据、接口与工程一律视为附属贡献。
- 阅读/核验深度：摘要、数据引擎与数据划分/评价关键段；未复现
- 原论文来源：https://arxiv.org/html/2408.00714v2
- 奖项来源：https://blog.iclr.cc/2025/04/22/announcing-the-outstanding-paper-awards-at-iclr-2025/

### A03｜Score Matching with Missing Data
- 会议与奖项：ICML 2025 — Outstanding Paper
- 问题领域：缺失数据统计推断
- 候选编码：M2 主；M9/M14 辅
- 关键研究动作：把缺失机制和边际 score 写入目标，而非只对完整数据方法补丁式插值。主要分析 MCAR；MNAR 扩展有已知缺失机制条件。
- 对框架的压力测试：不能将作者已声明的扩展当遗漏；观测机制与估计对象必须联动。
- 阅读/核验深度：摘要、缺失设定、边际目标、MNAR 附录条件
- 原论文来源：https://arxiv.org/html/2506.00557v1
- 奖项来源：https://icml.cc/virtual/2025/awards_detail

### A04｜Conformal Prediction as Bayesian Quadrature
- 会议与奖项：ICML 2025 — Outstanding Paper
- 问题领域：概率保证与不确定性
- 候选编码：M11 主；M7/M9 辅
- 关键研究动作：连接 conformal 与 Bayesian quadrature；区分跨校准样本的边际保证和基于已观测校准数据的后验风险判断。
- 对框架的压力测试：不能把后验/数据条件保证写成每个输入上的无分布假设保证。
- 阅读/核验深度：摘要、保证定义、讨论与局限段；未复核全部证明
- 原论文来源：https://arxiv.org/html/2502.13228v2
- 奖项来源：https://icml.cc/virtual/2025/awards_detail

### A05｜Stochastic Taylor Derivative Estimator: Efficient amortization for arbitrary differential operators
- 会议与奖项：NeurIPS 2024 — Best Paper
- 问题领域：数值计算与科学机器学习
- 候选编码：M2 主；M11/M3 辅
- 关键研究动作：将高阶微分算子的张量收缩转为可随机估计的高阶 AD 计算。
- 对框架的压力测试：核心可以是计算原语重写，不必先发现测量失效；估计量、实际浮点误差与资源收益分别验证。
- 阅读/核验深度：摘要、估计量条件及消融定位；未复现数值实验
- 原论文来源：https://arxiv.org/html/2412.00088v1
- 奖项来源：https://blog.neurips.cc/2024/12/10/announcing-the-neurips-2024-best-paper-awards/

### A06｜Optimal Mistake Bounds for Transductive Online Learning
- 会议与奖项：NeurIPS 2025 — Best Paper Runner-Up
- 问题领域：在线学习理论
- 候选编码：M9 主；M11 辅
- 关键研究动作：用理论界刻画预先获取无标签实例序列的价值。普遍下界与存在达到界的类，量词不同。
- 对框架的压力测试：最坏情形证明不因没有真实模型实验而不完整；不可将存在性上界写成对所有类的上界。
- 阅读/核验深度：摘要和主要结论；未完成完整证明链复核
- 原论文来源：https://arxiv.org/html/2512.12567v1
- 奖项来源：https://blog.neurips.cc/2025/11/26/announcing-the-neurips-2025-best-paper-awards/

### A07｜Evaluating Decision Rules Across Many Weak Experiments
- 会议与奖项：KDD 2025 — Best Paper — Applied Data Science
- 问题领域：实验设计与决策统计
- 候选编码：M7 主；M9/M3 辅
- 关键研究动作：由逐实验显著性转向跨实验的决策规则预期收益；选择与评价分离，并分析剩余训练样本量偏差。
- 对框架的压力测试：M14 应针对目标层级；单实验弱不等于跨实验规则无可辨价值。
- 阅读/核验深度：摘要、估计目标、交叉验证偏差与定理条件
- 原论文来源：https://arxiv.org/html/2502.08763v2
- 奖项来源：https://kdd.org/kdd2025/awards/

### A08｜When Heterophily Meets Heterogeneity: Challenges and a New Large-Scale Graph Benchmark
- 会议与奖项：KDD 2025 — Best Paper — Dataset and Benchmark
- 问题领域：图学习与基准基础设施
- 候选编码：M7 主；M12/M6 辅
- 关键研究动作：把节点/边类型异质性与标签异配性同时纳入统一数据和评测流程。
- 对框架的压力测试：数据与统一协议可以是主体贡献；A+B 的交叉设定不自动创新，也不自动无效。
- 阅读/核验深度：会议版 PDF 首页与流程页图像，摘要和方法组织
- 原论文来源：https://jshun.csail.mit.edu/H2GB.pdf
- 奖项来源：https://kdd.org/kdd2025/awards/

### A09｜Native Sparse Attention: Hardware-Aligned and Natively Trainable Sparse Attention
- 会议与奖项：ACL 2025 — Best Paper
- 问题领域：模型算法与硬件共同设计
- 候选编码：M8 主；M3/M2 辅
- 关键研究动作：稀疏模式、原生训练和硬件执行共同设计。
- 对框架的压力测试：减少理论运算量不等于端到端加速；应匹配工作负载和生命周期。
- 阅读/核验深度：会议摘要和 arXiv 方法概述；未复现内核
- 原论文来源：https://aclanthology.org/2025.acl-long.1126/
- 奖项来源：https://2025.aclweb.org/program/awards/

### A10｜Memory efficiency and resource-rational encoding in sentence processing
- 会议与奖项：ACL 2026 — Best Paper
- 问题领域：语言认知与计算建模
- 候选编码：M9/M11 主；M2 辅
- 关键研究动作：将工作记忆限制实现为可调表示噪声及编码精度约束，以人类阅读时数据检验解释。
- 对框架的压力测试：研究目标是解释人类行为；模型性能最大化不是唯一评价终点。
- 阅读/核验深度：会议页、PDF 首页和认知设定页图像；未重新分析人类数据
- 原论文来源：https://aclanthology.org/2026.acl-long.1550/
- 奖项来源：https://2026.aclweb.org/program/best_papers/

### A11｜An image speaks a thousand words, but can everyone listen? On image transcreation for cultural relevance
- 会议与奖项：EMNLP 2024 — Best Paper
- 问题领域：跨文化多模态与任务定义
- 候选编码：M7 主；M6 辅
- 关键研究动作：共同评价图像文化相关性和意义保留，并建立任务/数据与人工评价。
- 对框架的压力测试：目标涉及群体与语境；分歧不能预先全部定义为噪声。
- 阅读/核验深度：官方论文摘要与奖项核对；本轮未取得完整 PDF，不作全文审计
- 原论文来源：https://aclanthology.org/2024.emnlp-main.573/
- 奖项来源：https://2024.emnlp.org/program/best_papers/

### A12｜Infini-gram mini: Exact n-gram Search at the Internet Scale with FM-Index
- 会议与奖项：EMNLP 2025 — Best Paper
- 问题领域：压缩索引与研究仪器
- 候选编码：M3/M12 主；M11 辅
- 关键研究动作：利用已知 FM-index 并重构大规模并行构建和磁盘查询，开放更大规模精确语料检索。
- 对框架的压力测试：已知组件仍可因可靠能力/成本边界而形成贡献；精确字符串命中不等于训练污染因果结论。
- 阅读/核验深度：摘要、实现与成本权衡段；未运行大规模索引
- 原论文来源：https://arxiv.org/html/2506.12229v4
- 奖项来源：https://2025.emnlp.org/program/awards/

### A13｜Model Change for Description Logic Concepts
- 会议与奖项：AAAI 2026 — Outstanding Paper
- 问题领域：知识表示与信念修正
- 候选编码：M9 主；M2/M11 辅
- 关键研究动作：将知识变化写为模型集合增删及联合修正，刻画公理与可实现性的关系。
- 对框架的压力测试：联合修正不能简单等同于先增后删；证明义务与经验评价不可互相替代。
- 阅读/核验深度：原文关键定义/修正章节，KR 作者报告对 AAAI 奖项的确认
- 原论文来源：https://arxiv.org/html/2603.05562v1
- 奖项来源：https://kr.org/KR2026/FinalVersionsRPR/ModelChangeforDescriptionLogicConcepts.pdf

### A14｜Causal Structure Learning for Dynamical Systems with Theoretical Score Analysis
- 会议与奖项：AAAI 2026 — Outstanding Paper
- 问题领域：动力系统与因果发现
- 候选编码：M2 主；M9/M14 辅
- 关键研究动作：从动力过程与观测时间机制构造因果评分；理论保证依赖具体稳定性、模型与评分条件。
- 对框架的压力测试：预测/评分性质不等于无条件因果识别；作者已有假设不能当作未声明漏洞。
- 阅读/核验深度：原文摘要、动力稳定性和评分理论条件；官方奖项页通过索引核对，直接访问受限
- 原论文来源：https://arxiv.org/html/2512.14361v1
- 奖项来源：https://aaai.org/about-aaai/aaai-awards/aaai-conference-paper-awards-and-recognition/

## 首轮建议：保留操作代码，改造执行层

1. 先确定研究目标与允许的贡献终点，再选择校准方式。理论刻画、经验解释、系统构造、评价/数据、决策改进不必共享同一终点。
2. 把“最小实验”扩大为“最小判别证据”：证明反例、计算校验、真实实验、标注/效度审计、工程验收各有适用条件。
3. 先诊断是可选研究入口，不是每篇论文必须遵循的时间顺序。建造仪器、形成形式化和创建任务也可能先发生。
4. 把目标合理性、可观测性、统计可估性和实施可行性分开；主体差异与文化分歧不自动是参考噪声。
5. 公理、精确算子、理想估计量、有限精度实现和实际决策保持分层，不用一个层级的保证替代另一个。
6. 对A+B的判断依据是新增可证明/可运行/可复用能力，而不是组件是否全新；不自动判无创新，也不自动判创新。
7. M14应用在当前估计目标层级；不要以单个实验不显著否决跨实验规则评估。
8. 为探索性发现留空间；预注册冻结确认阶段，不能禁止任何意外观察或目标修订。
9. “找不到缺陷”是合法结果；既提取论文已解决的正面问题，也检查解释边界，不为凑研究点重复已有控制。
10. 代码允许不适用、无法判断和跨码歧义；公式出现不自动记M9，用GPU不自动记M8，有评测不自动记M7。

## 下一轮可执行的跨领域检验（尚未实施）

将本轮14篇作为开发集；冻结代码本和解释边界后，从未分析的问题家族另建留出集。另配同会议、同年份、同轨道和相近主题的非获奖论文作为对照，不将非获奖视为低质量。
比较相同时间/字数预算下的一般审稿清单与Meta-method。对论文提案的评审尽可能隐藏获奖标签，但需记录模型或评审者可能已见过论文的知识污染。
评价的不是“能否贴码”，而是核心贡献识别是否正确、是否误提原文已完成控制、是否提出适配证据类型的可执行下一步、是否错误否决理论/资源型研究，以及实际改变研究决策的信息收益。
若框架只能解释已成功论文、不能改善留出任务中的判断，结论应收窄为文献整理工具；若持续误判某类贡献，修改或弃用该部分规则。

## 通用证据卡模板

研究目标 → 精确主张与量词/适用群体 → 现有方法的限制或新机会 → 核心对象/操作变化 → 所需证据及独立参照 → 哪种结果会推翻主张 → 哪种结果只改变适用范围 → 已有工作与未解决部分 → 最小下一步及成本 → 合法完成/转向/停止条件。

## 状态

完成：奖项与原文的分层核对、14篇首轮对象编码、跨领域规则修订提案。
未完成：七会议双年全量获奖普查、所有原文全文与证明审计、独立双人编码、真正留出验证、对研究产出的前瞻效果评估。