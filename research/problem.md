# Research Problem Contract

> Replace every `[TODO]` before starting a full run. The PI must stop if required fields remain unknown.

## 1. Research question
- **Problem:** [TODO]
- **Why it matters:** [TODO]
- **Target contribution:** [TODO]
- **Falsifiable hypothesis:** [TODO]

## 2. Human state of the art (SOTA)
- **Primary paper:** [TODO: title, authors, venue/year, DOI/arXiv URL]
- **Official code:** [TODO: repository URL]
- **Pinned commit/tag:** [TODO]
- **Baseline reproduction command:** [TODO]
- **Known reported results:** [TODO: cite source and metric]

## 3. Benchmark contract
- **Datasets and versions:** [TODO]
- **Train/validation/test splits:** [TODO]
- **Primary metric:** [TODO]
- **Secondary metrics:** [TODO]
- **Evaluation command / harness:** [TODO]
- **Statistical protocol:** [TODO: seeds, confidence intervals, tests]
- **Allowed external data:** [TODO]

## 4. Immutable constraints
- Do not alter test data, labels, splits, scoring code, or benchmark rules.
- [TODO: domain-specific constraints]
- [TODO: compute and memory constraints]
- [TODO: privacy, licensing, safety constraints]

## 5. Compute and schedule budget
- **Hardware:** [TODO]
- **GPU hours:** [TODO]
- **Wall-clock limit:** [TODO]
- **Token / API budget:** [TODO]
- **Maximum full benchmark runs:** [TODO]

## 6. Deliverables
- Reproducible code and environment lockfile.
- Baseline and candidate results with raw logs.
- Full benchmark and component-level ablation report.
- LaTeX manuscript and bibliography.
- Peer-review/rebuttal history.
- Four-part integrity audit.

## 7. Human approval gates
- Approve baseline reproduction before candidate implementation: [yes/no]
- Approve full benchmark compute: [yes/no]
- Approve external/cloud spend: [yes/no]
- Approve final manuscript claims: [yes/no]
