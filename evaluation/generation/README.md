# MM-G01 文件入口

[协议](MM-G01-protocol.md) · [量表](rubric.md) · [计划](plan.json) · [材料](materials.json)

`inputs/`仅含中性参与者正文，没有组名、来源论文实例或赢家答案。组织者读取完整协议，执行者只接收所属材料及当前一个情境。实际token长度、模型和预算尚未锁定，因此不声明已做严格等长实验。

`python3 tools/generation.py check`检查结构与引用；`python3 tools/generation.py check --opportunity PATH`检查一张机会卡。没有模型执行子命令，不能把此检查当作MM-G01启动或预注册。
