# XD05｜本对话跨领域补充分析

论文：Stochastic Taylor Derivative Estimator: Efficient amortization for arbitrary differential operators

本对话原编号A05；已有仓库ID提示XD05（按标题/原文链接匹配，不按序号）。

> 本条为合并候选，不新增重复论文实体；已参与框架开发。本次未重核奖项和原文，不覆盖其他分析者编码。

- 会议与奖项：NeurIPS 2024 — Best Paper
- 问题领域：数值计算与科学机器学习
- 候选编码：M2 主；M11/M3 辅
- 关键研究动作：将高阶微分算子的张量收缩转为可随机估计的高阶 AD 计算。
- 对框架的压力测试：核心可以是计算原语重写，不必先发现测量失效；估计量、实际浮点误差与资源收益分别验证。
- 阅读/核验深度：摘要、估计量条件及消融定位；未复现数值实验
- 原论文来源：https://arxiv.org/html/2412.00088v1
- 奖项来源：https://blog.neurips.cc/2024/12/10/announcing-the-neurips-2024-best-paper-awards/

## 来源与合并规则

逐字字段来自 `archive/Meta_method_Round2_award_papers_v0.1.md` 对应A05节。候选码为历史分析，不是本次独立作者编码。原始框架压力测试作为复核记录保存；未在本轮凭空扩写新的后续项目。
