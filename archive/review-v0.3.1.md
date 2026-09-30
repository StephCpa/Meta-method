# Review of StephCpa/Meta-method v0.3.1 (commit 5c0dcd4)

Reviewed 2026-09-30. Read: README, docs/, data/, templates/, examples/, evaluation/, archive/, CHANGELOG, RIGHTS, releases/. `tools/validate.py` returns no errors and all 118 tests pass locally; GitHub CI status could not be checked from this session.

**Bottom line.** The repo has turned into a careful framework for checking whether a research claim is supported. It says much less about how successful papers get to non-A+B contributions, which was the original goal. Its operation codebook is also barely grounded in coded papers. Both problems can be fixed, and the catalog v0.1 in this project closes part of the gap directly.

## Strengths

- **The claim is the unit of analysis (主张级).** One paper can make mathematical, engineering and mechanism claims, and each needs its own evidence. This is more accurate than templates keyed on paper type.
- **The author/review/proposal split (docs/codebook.md)** stops an analyst's suggestions from being counted as field practice. It is the right guard, and it is what exposes issue 2 below.
- **Honest scoping.**
  - It states that a purposive sample is not a prevalence estimate.
  - It tracks development vs holdout contamination.
  - It allows `not_applicable` and empty codes.
  - No score rewards filling in more codes.
- **The "minimal discriminating evidence vs final sufficient evidence" table** (docs/framework.md §4) is the most practically useful page.
- **The three-arm pilot** separates the framework increment (B−A) from the codebook increment (C−B).
- **The tooling works.** Schema, validate/freeze/evaluate and 118 tests. The v0.2 probe arithmetic checks out: pass@8 0.8322→0.5344 re-derived.

## Priority issues

### 1. Decide what the framework is for, then make the pilot measure that

Most of the framework is evaluative: it asks whether a claim is supported, bounded and non-circular. That covers the five layers, R01–R12, the six evidence profiles and contracts A–F. Only the M-codebook is generative, and it is the thinnest layer.

The pilot's outcomes, omission rate and severe overreach, measure only the evaluative side. Even a clean win for arm C would show that the framework makes analyses more careful, not that it helps anyone find a better direction.

**Fix.**
- State explicitly that there are two halves, each with its own outcome:
  - (a) a move catalog for generating directions;
  - (b) a claim–evidence audit.
- Test (a) by **retrodiction**:
  1. Take award papers published after the executor model's training cutoff.
  2. Give each arm the state before the paper existed: the problem plus the prior work it cites.
  3. Ask for k candidate directions.
  4. Score whether the winning move appears, plus blinded expert ratings of novelty and significance.

  The repo's existing contamination tracking already supports this design.

### 2. The codebook is not grounded in coded papers yet

**No author-role codes exist.** In data/cases.json:
- The 10 MAS cases carry only `coding_role = proposal` codes: M14 ×9, M7 ×6, M9 ×6, M10 ×5, M12 ×2, M3 ×1, M8 ×1. These are the analyst's recommended next steps, not what the papers did.
- The 24 OPD and 14 XD cases have empty `candidate_codes`.
- docs/provenance.md:19 confirms that the 10 seed post-training papers and the 32-paper purposive sample have no lists.

**The seed domains show through.**
- M4 (weak model / negative control), M5 (feedback loop), M6 (feedback channel) and M14 (support set / estimand) are post-training vocabulary.
- R08 and contract A come from MAS execution.
- The same GPT instance that read the seeds then did the "cross-domain" generalization, so anchoring is likely.

**The cross-domain sample is narrow.** All 14 XD papers are ML/NLP/AI. None are from TCS (STOC/FOCS/SODA), security, systems/DB, SE or HCI. Those are the communities where the 382-paper catalog found the most distinctive moves:
- theory: C7 + C24 = 50% of primary codes;
- security: C13 + C27 = 35%;
- HCI/SE: C18.

**Quick win.** 8 of the 14 XD papers are already coded in the catalog. Under codebook.md's own rule, they can go in as author-role codes with an abstract-level locator note:

| Case | Paper | Award | Primary | Secondary |
|---|---|---|---|---|
| XD01 | Score Matching with Missing Data | ICML 2025 Outstanding | C10 | flagged A+B; C32 candidate |
| XD02 | Conformal Prediction as Bayesian Quadrature | ICML 2025 Outstanding | C1 | C3, C8 |
| XD03 | SAM 2 | ICLR 2025 Honorable Mention | C9 | C19, C10 |
| XD04 | Transformers are Inherently Succinct | ICLR 2026 Outstanding | C7 | C1, C8 |
| XD05 | Stochastic Taylor Derivative Estimator | NeurIPS 2024 Best Paper | C10 | C20, C15 |
| XD06 | Optimal Mistake Bounds for Transductive Online Learning | NeurIPS 2025 Runner-up | C7 | – |
| XD09 | Native Sparse Attention | ACL 2025 Best Paper | C14 | C11 |
| XD12 | Infini-gram mini | EMNLP 2025 Best Paper | C15 | C9, C2 |

### 3. About half of award-paper moves have no M code

The crosswalk below is a judgment call:

| M code | Closest catalog code(s) | Fit |
|---|---|---|
| M1 诊断后干预 | C4b diagnose → minimal fix | good |
| M2 表示／基本操作重写 | C10a | good |
| M3 预算／瓶颈重分配 | C14, C20 | good |
| M4 弱模型／负控制 | method_signal: no code (a technique); negative_control: an evidence check (R05), near C16 | split it |
| M5 反馈闭环 | none | a technique family, close to an A+B ingredient |
| M6 数据／反馈通道扩展 | C11, C9b | partial |
| M7 评价协议重构 | C2, C1b | good |
| M8 跨层共同设计 | C28, C14 | good |
| M9 隐含假设形式化 | C22, C12, C32 | partial |
| M10 设计空间搜索与机制归因 | C4a, C6 | the search half is a move; the attribution half is a check |
| M11 结构迁移／桥接 | C8 (C8c) | good |
| M12 中间抽象／统一接口 | C10b, C3 | good |
| M13 A+B | overlay flag + lift L1–L7 | needs lift criteria (issue 4) |
| M14 双重闸门 | C2 as an audit action | a check, not a move; R04 restates it |

Primary codes with a reasonable M counterpart cover 187 of 382 papers (49%).

**Moves with no M code** (share of primary codes):
- C1 reframe: 11.0%, the most common move
- C9 enabling artifact: 8.1%
- C18 people in context: 5.2%
- C13 adversary's lens: 4.2%
- C7 prove a limit: 4.2%
- C24 break a named barrier: 2.6%
- C15 revive/retire, C17 negative result, C19 new task/capability, C5 radical simplification

**Fix.** Split the codebook into moves and checks. Move M14, M4 negative_control and the attribution half of M10 into the rules/evidence layer. Then add the missing moves.

### 4. M13 needs a lift test, since that is the crux of the A+B critique

M13 says a combination is "既非自动创新也非自动否定" and stops there. In the catalog, about 15% of award winners look like A+B, and every one has a nameable lift:

| Lift | What it means |
|---|---|
| L1 | exact correspondence or derivation |
| L2 | surprising result |
| L3 | new capability |
| L4 | distance plus a named barrier |
| L5 | mechanism diagnosis |
| L6 | real-world or production validation |
| L7 | realistic threat model |

**Fix.** Require M13 codes to name the lift and the evidence for it. Also list the anti-patterns:
- swapping a component with no diagnosis;
- a gain that comes only from compute or data;
- new vocabulary with no new result.

XD01 is a ready-made worked example: it is flagged A+B, and the candidate lift is C32 (relax an assumption).

### 5. Pilot confounds

- **Length/effort.** The arm packages differ a lot in size: A 1,202 bytes, B 10,397, C 15,641 (evaluation/materials.json). B−A therefore mixes content with sheer amount of instruction. Add a length-matched placebo arm, such as a generic checklist plus reviewer guidelines at about 10 KB.
- **Blinding leak to executors.** materials.json strips arm labels only in the evaluator copy. The executor-facing files still say which arm they belong to:
  - evaluation/inputs/framework-package.md:1 "（B/C相同）"
  - bc-instructions.md:1 and :3
  - docs/conditional-contracts.md:35 "B/C试验臂…C仅另有操作代码本"
  - common.md:7

  An LLM that knows it is the "framework arm" may behave differently for that reason alone (demand characteristics). Strip these labels from participant copies.
- **Unset parameters and power.** δ/η, model, budget and seeds are unset, and there is no power analysis. As a rough guide: detecting an omission-rate drop from 30% to 15% (α = .05, power .8) needs about 120 independent claims per arm, before any clustering by case. Twelve development cases will not get there. Analyze paired by case (McNemar or a GLMM) and size the holdout set before running.

### 6. Rules cannot be traced to evidence

All 12 rules in data/rules.json cite the same four source_ids: SRC-MAS, SRC-V02, SRC-CROSS and SRC-V03. There is no way to tell which case motivated which rule, or whether a rule fires in only one domain (R07 is RL-flavored; R08 is MAS-flavored).

**Fix.** Give each rule these fields: `derived_from_cases`, `counterexample_cases`, and the domains where it has triggered.

### 7. Repo hygiene

- **Dangling references.** Several files point to material that is not in the repo:
  - README.md:28 and releases/v0.3.1.md:7 refer to documents "写入工具拦截…只在对话交付包中提供".
  - archive/manifest.json points to `legacy_meta_materials_2026-09-30.zip`.
  - docs/provenance.md:37 mentions `Meta_method_v0.3_review_bundle.zip`.

  Commit these files (as a release asset if large) or drop the references. Chat-process artifacts should not live in product docs.
- **Scattered caveats and version notes.** Nearly every page restates the status caveats; put them in one STATUS section. Move version patch notes (e.g. "v0.3.1：M14复验触发…" in codebook.md) to CHANGELOG.
- **No English.** Add an English README summary and an M-code glossary. The target literature is international, and English makes crosswalks easier.
- **No license.** RIGHTS.md deliberately grants none, so default copyright applies and others cannot reuse or contribute. If uptake matters, consider CC BY 4.0 for docs and MIT for tools. This is the owner's call.

## Suggested order

1. Author-code the 8 overlapping XD papers and add the M↔C crosswalk. This takes hours.
2. Split the codebook into moves and checks. Add C1, C7, C13, C18 and the L1–L7 lift test for M13.
3. Fix the blinding leak and the length confound, then set δ/η and the sample size.
4. Add the retrodiction outcome before running the pilot.
