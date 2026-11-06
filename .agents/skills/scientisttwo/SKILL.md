---
name: scientisttwo
description: >
  Run the complete ScientistTwo-inspired autonomous research lifecycle:
  limitation discovery, novelty-filtered hypotheses, baseline reproduction,
  subset-to-full experiments, idea evolution, ablations, paper drafting,
  simulated peer review, rebuttal experiments, meta review, and integrity audit.
  Use when the user asks for end-to-end scientific research or to run the
  ScientistTwo-Codex Research Lab. Do not use for ordinary code fixes.
---

# ScientistTwo-Codex Full Research Workflow

Act as the PI. The Python state/ledger is the durable source of truth; this skill defines the scientific procedure. Read `AGENTS.md`, `research/problem.md`, `research/budget.toml`, and `research/state.json` first.

## Non-negotiable entry gate

1. Inspect the repository, data access, environment, baseline code, and benchmark specification.
2. Identify missing or ambiguous fields in `research/problem.md`.
3. If the problem, baseline, dataset splits, metrics, benchmark rules, or compute budget are incomplete, write `research/blocking_inputs.md` and stop before expensive runs.
4. Run `st2 doctor` and `st2 status`. If the project state is uninitialized, initialize it with `st2 init --problem research/problem.md`.
5. Do not claim this workflow is identical to Google's private implementation. It is a faithful workflow-level reproduction of the public paper.

## Six agent groups and their contracts

### Group 1 — Idea Generator

Delegate to `limitation_extractor`, `limitation_verifier`, `novelty_checker`, `idea_generator`, and later `idea_evolver`. Retrieve the configured number of reference papers for novelty comparison (two in the paper-reported profile).

- Extract actionable theoretical and empirical limitations of the pinned human SOTA.
- Attach evidence (paper section, code path, benchmark behavior, or verified source) to every limitation.
- Have the verifier independently judge whether the set is sufficient to guide improvements. Refine up to `limitation_extraction_max_rounds`.
- Generate distinct, falsifiable hypotheses tied to specific limitations.
- Score novelty against retrieved literature; novelty scores are prioritization signals, not proof of originality.
- Keep both evolved ideas and unevaluated high-novelty seed ideas (exploration + exploitation). The paper-reported profile evaluates two candidates per round: one seed candidate and one evolved candidate, subject to the task budget.
- Persist each limitation and idea under `research/literature/` and `research/candidates/`.

### Group 2 — Evaluator

Delegate to `baseline_coder`, `subset_coder`, `subset_critic`, `subset_engineer`, `fullset_coder`, `fullset_critic`, and `fullset_engineer`.

- Reproduce the baseline on a representative subset before implementing ideas.
- Freeze the baseline configuration, data split, seed, code commit, dependencies, and metric definitions.
- For each candidate, modify a copy/worktree of the baseline, run subset experiments, and record raw logs and metrics.
- The subset critic must return exactly `BAD`, `GOOD`, or `ENGINEER` with evidence and next action.
- `BAD`: discard but preserve the failure trace. `ENGINEER`: refine within the configured engineering budget. `GOOD`: request human approval if required, then scale to the full benchmark.
- Full-set coder adapts the candidate to the complete benchmark. Full-set critic independently checks metrics, protocol compliance, variance, and baseline comparison. Full-set engineer may refine only within budget.
- Never tune against test labels or change the evaluation harness to inflate scores.

### Group 3 — Analyzer

Delegate to `best_idea_selector`, `result_comparator`, `ablation_planner`, `ablation_coder`, and `ablation_critic`.

- Aggregate all successful and failed execution traces.
- Select the best validated candidate, not merely the highest single-run score.
- Design component-level ablations, including removal/replacement of each proposed contribution and relevant controls.
- Quantify attribution: a gain caused by generic training tricks or evaluation changes is not evidence for the proposed mechanism.
- Ablation critic returns `GOOD` or `REFINE`; refine within `ablation_refinement_max_rounds`. Create a new candidate ID/worktree rather than overwriting the current best. Use `result_comparator` to accept an updated full-set candidate only if it strictly outperforms the current best under the same protocol. If the ablation budget expires without a `GOOD` decision, do not present the proposed mechanism as a validated contribution.
- Store plans, results, confidence intervals, and attribution reasoning under `research/ablations/`.

### Group 4 — Writer

Delegate to `paper_drafter` and `paper_enhancer`.

- Draft from the selected hypothesis, full-set results, ablations, and verified bibliography only.
- Generate LaTeX in `paper/`; keep a claim-to-evidence map in `research/audit/claims.json`.
- Every quantitative claim must map to a metrics file and reproducible command.
- Never fabricate results, citations, theorem statements, or limitations.

### Group 5 — Peer Review

Delegate to `peer_reviewer`, `rebuttal_planner`, and `rebuttal_coder`.

- Review novelty, correctness, significance, clarity, experimental design, statistical validity, reproducibility, and limitations.
- Provide strengths, weaknesses, questions, confidence, and a 1–10 diagnostic score.
- If below the configured threshold and budget remains, turn material criticisms into targeted supplementary experiments; do not answer empirical criticism with prose alone.
- Re-run the reviewer after rebuttal and let `paper_enhancer` update only claims supported by new evidence.
- Stop at the configured maximum review rounds. Clearly label the review as simulated, not an actual conference decision. After the manuscript is frozen, run `heldout_reviewer` once as an independent held-out diagnostic; do not feed its score back into iterative optimization.

### Group 6 — Meta Review

Delegate to `meta_reviewer`.

- Assess the manuscript and complete review/rebuttal history.
- Return `ACCEPT`, `REFINE`, or `REJECT`, with reasons and actionable feedback.
- `REFINE` returns to idea/experiment refinement; `REJECT` halts and preserves artifacts; `ACCEPT` proceeds to integrity audit.

## Closed-loop execution protocol

At every stage:

1. Read the current state and prior evidence.
2. Delegate independent read-only work in parallel where useful.
3. Use one code writer per worktree. Use Codex App worktrees for competing implementations.
4. Ask an independent critic to evaluate the artifact.
5. Record the gate with `st2 gate <stage> --decision ... --feedback ...`.
6. Record experiments with `st2 experiment run ...` or ensure equivalent immutable run directories and metrics are saved.
7. Update state and ledger before moving to the next phase.

Use the iteration limits in `research/budget.toml`; do not silently extend budgets. Keep a Pareto view of performance, compute, and complexity where appropriate. Preserve the best validated candidate separately from exploratory candidates.

## Four-part integrity audit

Before completion, run all four checks:

1. **Score verification:** rerun every reported main result and compare to manuscript values within declared tolerance.
2. **Specification compliance:** execute benchmark-specific checks for data leakage, forbidden APIs, split integrity, reward hacking, or protocol violations.
3. **Reference verification:** verify DOI/arXiv records against authoritative scholarly sources; correct or remove invalid citations.
4. **Method-code alignment:** independently compare the method section to the actual code and configs, line by line where possible.

Fill `research/audit/manifest.json` and run `st2 audit --manifest research/audit/manifest.json --online`. The CLI structural checks do not replace semantic agent review. Any missing check is `INCOMPLETE`, not `PASS`.

## Completion criteria

Only mark the project completed when:

- Full benchmark results are reproducible.
- The claimed contribution survives component-level ablation.
- All benchmark constraints are respected.
- Bibliography is verified.
- Method and code agree.
- Manuscript claims map to evidence.
- Code, environment, configs, logs, and audit reports are preserved.

If any criterion fails, report the blocker and keep the project state open. Never claim guaranteed novelty, acceptance, or SOTA improvement.
