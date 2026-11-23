---
name: session-artifacts
description: Use at CS5351 session completion to record reusable outcomes, actual validation and complete OpenCode transcript exports.
---

# Session completion

Record the real scope, changed files, requirement/ADR links, commands, results,
failures and next decisions in `.opencode/skills/<name>/SKILL.md`. Never label
planned features, incomplete tests or missing approvals as delivered.

Use the TUI `/export` for the complete active session and save under
`transcripts/raw/`; preserve original content and add human annotations separately.
Native CLI JSON export is an additional lossless backup, not a forged Markdown
export. If no active-session export tool is available, state that blocker and
ask the human to run `/export`. Add real paths to the AI-use log only after export.
Check all shared artifacts for credentials and private account details.
