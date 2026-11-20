# Permission model

`.opencode/opencode.json` is the actual project configuration; it explicitly loads
rules.md and .agent/rules.md. `.opencode/permissions.jsonc` stores the same native
permission object as the course artifact. check_governance verifies synchronization.
The standalone permissions file is not automatically loaded by OpenCode.

| Role | Read | Write | Execute |
|---|---|---|---|
| plan (default) | explicitly whitelisted project documents/source/tests | denied | confirmation for each command |
| build (after human plan/test approval) | same whitelist | confirmation within src/test/docs/scripts and project config | confirmation for each command |
| human | reviews frozen rules and approval records | rules.md and approval decisions | approves integration/publication |

Default rules deny unspecified access; scoped reads are allowlisted, while discovery
tools and shell require confirmation. Outside-directory access and subagent tasks
are denied. Shell commands require confirmation because Python/shell can bypass file-tool controls;
these permissions are harness controls, not a filesystem/process sandbox. Human
review is mandatory for commands, safety changes and arbitrary reads through code.
Agent-specific module path narrowing remains a future approved configuration.
Do not assert file permissions prove perfect containment; negative permission
tests and effective-config review are recorded separately from JSON validation.
