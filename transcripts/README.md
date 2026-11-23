# Full session evidence

No student names, IDs or five annotated sessions are fabricated at initialization.
From the repository-root OpenCode TUI use `/export` to save the complete active
session under `transcripts/raw/`. Preserve the export, then add human annotations
with timestamps/message references, decisions and rationale. Link both artifacts
from the AI-use log and actual PR. D5 submission names must include student IDs
and names; five full annotated sessions collectively cover all supervised stages.

The CLI `opencode export <sessionID>` exports native JSON; it is a useful additional
lossless backup but is not to be relabeled as a TUI Markdown `/export`. Review
exports for secrets before sharing; retain originals locally, and document any
redactions in shared evidence. A skill summary never replaces the full export.
