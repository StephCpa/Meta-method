# 三个结束状态示例（全部是公开构造材料）

这不是三次真实实验或三臂结果。对应JSON在 `examples/claims.json`，ID为EX07–EX09。格式示例不会提升任何历史论文的核验状态。

## EX07

主张：对有限非空动作集，任意固定常数c不改变u的argmax。
证明：任意a,b，(u(a)+c)−(u(b)+c)=u(a)−u(b)，比较关系全部保持，最大化集合相同。
状态：claim_status=supported；work_status=complete；evidence_outcome=supports。该初等命题仅示范完成记录，不申报新的理论贡献，也不主张训练轨迹不变。

## EX08

构造前提：待检主张为增益θ≥0.05；预先给定并假定有效的区间为[-0.01,0.02]。上界0.02<0.05，按构造标准排除有意义效应。
状态：claim_status=refuted；work_status=complete；evidence_outcome=refutes。这里完成的是研究判断，不是“原主张获得支持”。没有实际运行实验、证明区间覆盖或估计任何模型效果。

## EX09

构造前提：同一阈值0.05，给定区间为[-0.04,0.12]；无法判断是否达到阈值。
状态：claim_status=inconclusive；work_status=paused；evidence_outcome=inconclusive。暂停由资源约束决定，不是不存在效应。重启条件是可获得信息量足以区分目标范围的新证据。
