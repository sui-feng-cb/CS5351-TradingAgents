# D implementation: real human interventions

Requirements: FR-D, NFR-D, INV-D; ADR-002. These are annotations of real session
messages, not an original transcript or a completed D5 export. Exact export
message IDs and timestamps will be added only after the full TUI `/export` exists.

1. The user stated PR #2 had been squash-merged, main/D were updated, and the
   latest D commit held prior review/session/skill documents; they explicitly
   directed the agent not to recheck those settled facts. The session used that
   baseline and prepared the D implementation blueprint.
2. The user approved the concrete blueprint: “批准执行蓝图方案，注意在过程中记录并更新D1-9需要提交的东西，过程中不要打断对话，直到完成测试并满足提交条件后，将更改暂存，然后输出commit和push的命令”.
   This authorized local implementation, verification, artifact updates and final
   staging. It did not authorize executing commit/push or claiming independent
   safety/integration approval.
3. The agent redundantly asked for continuation after an AGENTS.md edit was
   denied. The user selected continuation, then selected all offered source,
   documentation, verification and staging scopes. Those confirmations were real,
   but did not change the tool's denied path. The entrypoint edit was not bypassed.
4. The user subsequently wrote “继续” and later “继续”. Build mode became active
   in a harness reminder. The agent continued the same implementation task.
5. Verification caused real rework: first focused output tests failed, then full
   regression exposed standard-mode fixture/call compatibility. Assertions in
   the approved D acceptance tests were not relaxed. Actual results and changes
   are recorded in `docs/verification/d-eligibility.md`.

Pending: export the complete active session through the OpenCode TUI to
`transcripts/raw/`, retain original content, and cross-link the real file from
this annotation and `D-ELIG-IMPL-001` in the AI-use log. No export filename is
claimed before it exists.
