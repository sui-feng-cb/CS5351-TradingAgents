# Project OpenCode rules — human-owned after adoption

This initial draft was prepared by the coding agent under the explicit repository
initialization request; human adoption is pending. Future edits are human-only.

Read AGENTS/Prompt and current requirements/architecture. Stop for human plan and
test approval before application implementation. Use project configuration only;
do not change operating system, global Git or global OpenCode configuration.
Keep upstream contributions separate; enforce deterministic evidence/rating
boundaries; review commands because shell is not sandboxed by path rules.

Do not access or print .env, credentials or sensitive account inputs. Never commit
or push until expressly approved. At the end of each completed work session:

1. Summarize actual files, verification, failures and pending decisions.
2. Save reusable outcomes in `.opencode/skills/<name>/SKILL.md` with real evidence.
3. Use OpenCode `/export` to preserve the complete session under `transcripts/raw/`;
   keep human annotations separately and cross-link them to AI-use entries/PRs.
4. If the tool cannot export the active session, record the blocker and have the
   user perform `/export`; never synthesize a replacement transcript.

Restart OpenCode after changing project config; existing sessions retain loaded
settings. Default agent is plan; switch to build only after the recorded approval.
