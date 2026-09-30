# Meta-method · v0.4

**Contribution generation · Claim–evidence audit · Research decisions**

[中文](README.md) · [Status](STATUS.md) · [M-code glossary](docs/glossary.en.md)

Start from a meaningful problem, limitation or opportunity. Identify a concrete transformation and its added result, then choose evidence appropriate to the resulting claims. A precise claim is an audit unit, not a prerequisite for early idea formation.

## Three distinct outputs

| Track | Input | Output | Evaluation |
|---|---|---|---|
| Generation | Problem situation, prior limits and constraints | Specific candidate contributions | Substantive increment, importance and a feasible first step |
| Audit | Candidate claims | Supported scope and justified evidence needs | Essential omissions and unnecessary demands |
| Decision | Candidates, evidence and budget | Which proof, experiment or artifact to pursue | Independent knowledge/capability gains and costs |

The release integrates [eight first-pass author-move records](cases/author-moves-eight.md), [six generative cards](generation/move-cards.md), an [opportunity template](templates/opportunity-to-contribution.md), and a [combination-lift test](templates/m13-lift-card.md). Legacy M1–M14 identifiers and the v0.3.1 audit schema remain compatible. Moves, evidence checks, implementation techniques and combination labels have distinct roles.

The eight records are annotations *about* authors' contributions, not authors' self-labels or evidence of the discovery timeline. They are provisional and inherited from the supplied workbench, not independently recoded in this release. The external C-code mapping is retained as external judgment; the underlying 382-paper catalog was not supplied. Existing 48 development entries remain unchanged.

[MM-P01](evaluation/pilot-protocol.md) evaluates auditing. [MM-G01](evaluation/generation/MM-G01-protocol.md) proposes separate tests of generation, historical recovery, selection from a fixed pool and prospective decisions. Known award-winning solutions are useful references, not the only acceptable ideas. Neither study has established effectiveness. Participant instructions omit arm labels and outcome expectations; content-based treatment inference may remain possible.

```bash
python3 -m pip install -r requirements.txt
python3 tools/validate.py
python3 -m unittest discover -s tests -v
```

These are engineering checks, not evidence of scientific validity. Rights remain unchanged; see [RIGHTS.md](RIGHTS.md). Research status and historical artifact availability are centralized in [STATUS.md](STATUS.md).
