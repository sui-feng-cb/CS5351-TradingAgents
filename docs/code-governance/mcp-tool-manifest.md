# Coding-agent tools

No project MCP server is configured. Do not infer authorization for inherited MCP
servers or install plugins/providers without human direction.

| Tool | Plan | Build | Human boundary |
|---|---|---|---|
| read/glob/grep/list | whitelist | whitelist | secrets/outside paths denied |
| edit | denied | ask on whitelist | rules.md remains human-only |
| shell | ask | ask | inspect every command; no global changes |
| webfetch/search | ask | ask | API/live calls need explicit approval |
| task/subagents | denied | denied | no delegation configured |
| skill | project names allowed | project names allowed | summaries must be factual |
| Git commit/push | denied | denied | requires later user authorization |

Actual native rules and their limitations are in permission-model.md.
