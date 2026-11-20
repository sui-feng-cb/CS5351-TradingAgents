# Verification constraints

Every fit criterion has a test; every invariant has a violation-triggered failing
test. New tests name requirement/invariant IDs. Feature tests must be approved
before implementation. Keep expected outcomes independent of production logic.

1. Structural: package/CLI imports, resource discovery, dependency/module boundary,
   permissions and requirement schema validation.
2. Regression: all previously established offline suites must pass each round.
3. Behavioral: frozen evidence-ID, REVIEW safety, recovery, timing and semantic
   grouping thresholds. Mock model output tests cannot prove real model quality.

B needs at least 20 human-labeled news pairs (10 positive/10 negative), pairwise
precision ≥0.80 and recall ≥0.70 under the approved model/evaluation procedure.
The evaluation dataset/runner and live credentials are not present at initialization;
model/prompt changes fail closed until approved, replayable evidence exists.
Feature acceptance tests, mutation checks and performance results are not claimed.

Record the baseline before moving packages and the migrated suite afterward.
Initialization authorizes structural path changes only. CI bootstrap checks do not
prove every D7 gate or remote branch protection is already operational.
