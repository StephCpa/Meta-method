# Meta-method · v0.4

**贡献生成 × 主张审计 × 研究决策**

> 从重要问题与限制出发，找到改变关键关系的操作，形成具有实质增量的候选；再用匹配的证据决定如何推进。

[English](README.en.md) · [版本状态](STATUS.md) · [变更记录](CHANGELOG.md)

v0.4.0 保留 v0.3.1 的五层结构、M1–M14 和审计工具，但不再让“少犯错”代替“产生好方向”。生成可从机会和瓶颈开始，不强迫先有精确主张。理论、解释、算法、系统、数据与决策有各自的成果终点。

## 按当前任务进入

| 当前任务 | 入口 | 产物 |
|---|---|---|
| 形成研究方向 | [六张生成操作卡](generation/move-cards.md) · [机会—贡献卡](templates/opportunity-to-contribution.md) | 对象、障碍、具体变换、新增结果和第一个产物 |
| 判断组合的增量 | [M13 增量检验](templates/m13-lift-card.md) | 最近的简单组合、改变的关系、增量证据 |
| 理解成功贡献的结构 | [八篇作者贡献记录](cases/author-moves-eight.md) · [结构化记录](data/author-moves.json) | 带版本和原文锚点的首轮分析 |
| 审查已形成的主张 | [贡献—证据卡](templates/contribution-evidence-card.md) · [证据配置](docs/evidence-profiles.md) | 已支持范围、必要证据、不适用要求 |
| 选择下一步 | [工作流](docs/workflow.md) · [框架](docs/framework.md) | 证明、原型、观察、实验、完成或暂停 |
| 评价框架 | [双轨评估入口](evaluation/README.md) | 审计与生成分开，不以审计成绩证明创意能力 |

## 论文分析库

[**浏览论文库**](paper-library/README.md) · [论文索引](paper-library/INDEX.md) · [研究方向池](paper-library/IDEAS.md) · [新增与复读](paper-library/ADDING.md)

独立内容库保存论文分析、后续方向和潜力历史，不收录原论文。当前为57篇去重论文、71份分析／补充记录、44条方向或迁移提问；阅读深度与来源边界分别保留。与框架版本独立维护，使用后按 `paper-library/ADDING.md` 追加记录。交互页面需下载后打开 `paper-library/index.html`，GitHub源码页不会直接运行HTML。

## 已入库的具体增量

**八篇作者记录**来自 v0.4 工作包的首轮来源阅读，仍待独立复核；历史48条案例没有被覆盖，也没有新增为56篇。**六张操作卡**明确触发情境、变换、首个产物和不适用条件；它们不是新增M编号。

**M13**要求说清组合改变了什么以及新增结果的证据。L1–L7保留为外部审查提示，不是创新通行证。**外部M↔C映射**与“187/382”仅作为审查者的报告保存，完整目录尚未取得。

**MM-P01**继续检验必要证据漏项与过度要求。**MM-G01**单独检验候选生成、历史贡献恢复、固定候选池筛选及实际研究决策。后者为设计稿，尚无模型输出或人工效果评分。

## 使用与检查

```bash
python3 -m pip install -r requirements.txt
python3 tools/validate.py
python3 -m unittest discover -s tests -v
python3 tools/generation.py check
python3 tools/freeze.py create --kind version --out outputs/freezes/v040.json
python3 tools/freeze.py verify outputs/freezes/v040.json
```

Python 3.10+。输出文件必须是新路径。工具检查结构、引用与执行约定，不判科学真值、新颖性或创意质量；不调用模型。主张Schema与旧命令继续兼容。

## 维护入口

[代码本及角色](docs/codebook.md) · [规则追溯](data/rule-lineage.json) · [来源纪律](docs/provenance.md) · [英文术语表](docs/glossary.en.md) · [v0.4 发布说明](releases/v0.4.0.md) · [权利说明](RIGHTS.md)

独立复核作者编码、补充其他研究共同体来源、绑定实际生成评估，均是后续工作，不是本版已完成的效果验证。不要用贴码数或建议数给框架评分。
