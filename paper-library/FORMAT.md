# 数据结构与维护契约

可增长的记录按一对象一文件存放；编号固定，不按排序重编号。

```text
library.json               库版本、框架关联与来源范围
INDEX.md / IDEAS.md         自动生成的Markdown入口
index.html / catalog.json  自动生成、可离线浏览的完整视图

data/papers/P0001.json     标题、标识、别名、主题、元信息观察、分析与方向引用、评分历史
data/analyses/A0001.json   一次分析的版本、范围、来源、代码和正文位置
data/ideas/I0001.json      一个候选方向，可连接多论文；状态和方向级评分
data/sources/*.json        来源快照位置、哈希与来源类别
data/collections.json     旧批次集合，不代表互不重叠的论文集
notes/A0001.md             分析正文（可与原来源片段逐字核对）
sources/                   既有分析资料和导入单，不放PDF或原论文全文
history/                   写入工具产生的更新前后记录
views/P0001.md             每论文自动生成的Markdown入口
```

## 数据语义

`metadata_observations`是按来源保存的观察，不能把“作者宣布录用”自动升级成“正式论文集已出版”。新记录保留版本与来源；元信息冲突需人工处理，不自动消除。

`reading_status`表示本库当前最具体的分析类型；不是读完全文的认证。每一份分析自身的范围和`preservation`更精确：`verbatim_excerpt`表示从已有分析档案截取，`structured_conversation_digest`表示本轮整理的摘要。

`status=imported_not_reverified`说明当前导入没有再次执行论文核验。原分析中的“我运行了”是历史记录，不变成本轮执行声明。

`codings.role`的author表示分析者编码的作者贡献操作，不表示作者亲自赋码；review与proposal分别记录审查和建议。不得把三个角色的频率混计。

`ratings`是追加列表：score、scope、reason、assessor、date至少明确。没有评分采用空列表。paper_main_followup与specific_direction分开；历史主线评分不自动继承到各方向。

## 标识与去重

arXiv按基础ID合并，vN作为分析记录中的论文版本保留；DOI去掉URL前缀并规范大小写。两个标识若指向不同条目则拒绝写入。同标题缺少稳定标识时要求人工指定；相似题目不自动合并。旧MAS、OPD、XD、OPD-T编号保存为aliases。

## 安全与失败

导入单只能提供http(s)来源链接；正文以文本显示，不执行其中HTML或脚本。路径限定在库内且拒绝符号链接。编辑工具加锁并使用原子文件替换，遇到冲突报错。锁残留时先确认没有正在进行的写入，再处理，不并行重复导入。

构建只改生成视图；用户原始分析不被生成器重写。直接手改`notes/`会导致哈希检查失败，推荐通过add追加更正；需修正录入错误时，保留旧内容及修改理由，并相应维护哈希。

当前验证器只做数据完整性，不判断某条研究建议新颖、有价值或科学成立。记录契约以工具支持的字段为准；不要把未列字段的存在视为被充分验证。
