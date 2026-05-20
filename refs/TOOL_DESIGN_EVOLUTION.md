# Stakpak Agent: Tool Design Evolution

A chronological look at how the tool system evolved from May 2025 to May 2026, with commit hashes and dates. No fluff — just what changed, why it mattered, and what we learned.

---

## Phase 1: Getting Started (May 2025)

### 2025-05-18 — MCP Server Born
**Commit:** `e5ffc592`  
Added the first MCP server with basic tools: `read_file` and `run_command`. The agent could read files and run shell commands. That was it.

### 2025-05-19 — First Tool Call Works
**Commits:** `ef182a87`, `52f52332`, `8aacd374`  
Got the first `run_command` tool call actually executing and returning results. Took 3 commits to get the output formatting right.

### 2025-05-20 — Output Truncation
**Commits:** `f80b2752`, `494a4275`  
Added output clipping to `run_command`. Shell commands can dump megabytes of text. The LLM context window can't handle that. Truncation was added at the tool level, not the API level.

> **Lesson:** Always truncate tool output. The LLM doesn't need your 10,000-line log dump.

### 2025-05-27 — Text Editor Tools
**Commit:** `dd2c0d90`  
Added `view`, `str_replace`, `create`, `insert`. The basic file editing toolkit. These are still the core tools today.

### 2025-05-28 — Tool Descriptions Matter
**Commits:** `e7a7511b`, `cba5aa8e`, `ff7e4d28`  
Three commits in one day just improving the `generate_code` tool's description. Not the code — the text the LLM sees. Added details about output clipping, context parameters, and code writing instructions.

> **Lesson:** Tool descriptions are prompts. Bad descriptions = bad tool calls. Iterate on them like you iterate on system prompts.

### 2025-05-29 — Parallel Tool Calls
**Commits:** `84aea384`, `0efbb147`  
Fixed parallel tool call handling. The LLM can call multiple tools at once. The system had to fan out the calls and collect results without losing track.

### 2025-05-29 — Streaming Tool Results
**Commits:** `ad53c2a0`, `c303442a`  
Added streaming for tool results. Long-running tools now send progress updates to the TUI instead of blocking until completion.

---

## Phase 2: Search and Knowledge (June–August 2025)

### 2025-06-XX — Search Tools
**Commits:** `e382a1e6`, `9de7fb57`, `138a8163`  
Added `search_docs` with keyword support, URL filtering, and exclude keywords. The agent could now search technical documentation.

### 2025-06-XX — Memory Search
**Commit:** `8c52602e`  
Added `search_memory` tool. Search previous conversations and generated code for context reuse.

### 2025-06-XX — Rulebooks
**Commit:** `6bdf338e`  
Added `read_rulebook` tool. Load structured guidance documents (later renamed to "skills").

### 2025-08-16 — Generate Code Disabled
**Commit:** `0a5476fe`  
Disabled the `generate_code` tool entirely. It was too complex, too error-prone, and the agent could do code generation through conversation instead.

> **Lesson:** Sometimes the best tool change is removing the tool. If the LLM can do it through conversation, don't add a separate tool.

---

## Phase 3: Safety and Boundaries (September–October 2025)

### 2025-09-11 — Command Lists
**Commit:** `0d54052b`  
Added a `command` list parameter to `run_command`. The agent could now run multiple commands in sequence without multiple tool calls.

### 2025-09-22 — Reversible File Operations
**Commits:** `d23a8120`, `785404fd`  
Made `remove` and `str_replace` reversible. `remove` backs up files before deletion. `str_replace` outputs a udiff so you can see what changed.

> **Lesson:** File operations should be undoable. The LLM will make mistakes. Give users a way back.

### 2025-09-26 — Slack Tools
**Commit:** `60cd0bd0`  
Added Slack integration: `slack_read_messages`, `slack_read_replies`, `slack_send_message`. Optional — gated by a config flag.

### 2025-10-27 — Sandbox
**Commits:** `4d7d85cc`, `760e4b94`, `072cfd01`  
Added sandbox mode. Potentially dangerous commands run in an isolated container. Policy enforcement blocks known-dangerous commands.

> **Lesson:** Don't trust the LLM with the host system. Sandbox by default, escape hatch by exception.

---

## Phase 4: Async and Background Tasks (November–December 2025)

### 2025-11-03 — MCP Crate Upgrade
**Commit:** `fb6801f1`  
Upgraded the `rmcp` crate (the MCP protocol implementation). Breaking changes required fixes across all tool definitions.

> **Lesson:** MCP is still evolving. Pin your protocol version and upgrade carefully.

### 2025-11-22 — Local Tool Implementations
**Commit:** `5198cd89`  
Refactored to enable local tool implementations directly in the agent, not just through the MCP server proxy.

### 2025-12-10 — Text Sanitization
**Commits:** `eff704d5`, `fd706bef`  
Added `sanitize_text_output` and HTML-to-markdown sanitization. Tool outputs get cleaned before reaching the LLM.

### 2025-12-17 — Description Conciseness
**Commit:** `41bacde7`  
Improved conciseness and clarity of tool descriptions. Shorter descriptions = more room in the context window for other stuff.

### 2025-12-22 — Secret Redaction Cleanup
**Commit:** `6ef9b48d`  
Removed duplicate secret redaction from the MCP server. Redaction moved to a single location.

---

## Phase 5: Subagents and Skills (January–February 2026)

### 2026-01-06 — Secret Handling Moved
**Commit:** `a8849393`  
Removed secret handling from local tools entirely. Redaction now happens at the proxy layer, not per-tool.

> **Lesson:** Security concerns migrate up the stack. Start per-tool, move to centralized.

### 2026-01-28 — Subagent Model Customization
**Commit:** `d6db9a3d`  
Made subagent model customizable. Subagents can use different models than the parent agent.

### 2026-02-03 — Session Namespacing
**Commit:** `ecece7e5`  
Added session ID namespacing for subagent temp data. Subagents from different sessions don't collide.

### 2026-02-05 — Dynamic Subagents
**Commit:** `b238ec90`  
Added `dynamic_subagent_task` and `resume_subagent_task`. The AOrchestra 4-tuple model: (Instruction, Context, Tools, Model). Spawn background agents with limited tool access.

> **Lesson:** Subagents are a privilege escalation problem. Give them least-privilege tool access. Sandbox them. Limit their steps.

### 2026-02-06 — Resume and Approvals
**Commit:** `fd058205`  
Added pause/resume flow for subagents. Subagents pause when they need tool approval or user input. The parent can approve, reject, or provide input.

### 2026-02-09 — Warden Sandbox
**Commits:** `e869507a`, `05dedd3b`, `468d561a`  
Switched subagent sandboxing to use Warden sidecar instead of a custom image. Simpler, more standard.

### 2026-02-09 — Sandbox Awareness
**Commit:** `66e6f290`  
Made the main agent aware of when sandboxing is useful. It can recommend sandbox mode based on the task.

### 2026-02-10 — Skills Replace Rulebooks
**Commit:** `79af6a8e`  
Replaced `read_rulebook` with `load_skill`. Renamed the concept from "rulebooks" to "skills". Added local skills parsing from `./stakpak` and `~/.stakpak/skills`.

> **Lesson:** Naming matters. "Rulebook" sounds rigid. "Skill" sounds reusable. Same concept, better framing.

### 2026-02-10 — Skill Format Update
**Commit:** `753c0187`  
Changed skill format to match the Skills spec. Standardized metadata, tags, and URI format.

### 2026-02-12 — Pre-pull Images
**Commit:** `176a108f`  
Pre-pull sandbox container images in the background at session start. No more waiting for Docker pulls when spawning a subagent.

### 2026-02-15 — Backward Compatibility
**Commit:** `2e0ca9bc`  
Added backward-compat mapping from `read_rulebook` → `load_skill` for existing user configs. Old configs still work.

> **Lesson:** Rename tools carefully. Break old configs and users will be angry. Provide aliases.

### 2026-02-15 — Profile Passing
**Commit:** `e7c54841`  
Pass profile and config to subagents. Subagents inherit the parent's configuration.

### 2026-02-16 — Input Validation
**Commit:** `883300ac`  
Normalized tool inputs and hardened `search_docs` validation:
- Max 32 keywords
- Max 128 chars per keyword
- Max 1024 chars total query
- Reject empty keywords

> **Lesson:** Validate at the tool boundary. The LLM sends garbage. Fail fast with clear errors.

### 2026-02-17 — Ask User Tool
**Commit:** `3b96d089`  
Added `ask_user` tool. Structured user prompts with predefined options, multi-select, custom input, and quick-select with number keys. Auto-approved (it asks the user, so it doesn't need approval).

### 2026-02-17 — Secret Redaction to Proxy
**Commit:** `c95e26e5`  
Moved secret redaction from the MCP server to the proxy layer. One place to redact, not scattered across tools.

### 2026-02-17 — Sandbox Volume Fixes
**Commits:** `95d2af67`, `6c253d75`  
Pre-create named volumes before sandbox spawn. Use exact match for volume dedup to preserve workdir mount.

---

## Phase 6: Cleanup and Hardening (March–May 2026)

### 2026-02-19 — Merge Skills
**Commit:** `bfa4a9d7`  
Merged the skills feature branch into main. The tool set stabilized.

### 2026-02-20 — Volume Deduplication
**Commit:** `4521fc60`  
Fixed volume deduplication to use exact match. Preserves workdir mount correctly.

### 2026-04-04 — Subagent Model Resolution
**Commit:** `aa5b994b`  
Fixed subagent model resolution for local providers. Send `model_provider` in metadata alongside `model_id`. Use profile default model instead of falling back to a hardcoded model.

### 2026-04-22 — Auto-approve Rename
**Commit:** `60cd0feb`  
Renamed `subagent_task` to `dynamic_subagent_task` in auto-approve logic to match the actual tool name.

> **Lesson:** Tool names are API contracts. The auto-approve logic, the TUI, and the LLM all need the same name. One mismatch and the tool silently fails.

### 2026-04-27 — Search Memory Removed
**Commit:** `aaf40cc2`  
Removed `search_memory` tool entirely. Commented out the code. The memory search wasn't reliable enough.

> **Lesson:** If a tool doesn't work well, kill it. Don't let broken tools linger.

### 2026-05-01 — AK Knowledge Store in Sandbox
**Commit:** `df50557a`  
Mount the AK (knowledge store) in sandbox containers. Subagents can read persistent knowledge.

### 2026-05-04 — Model Resolution Chain
**Commit:** `d07f58f8`  
Replaced the simple downgrade heuristic with a 4-step model resolution chain for subagents:
1. Profile `[subagent].model` setting
2. Built-in default for the parent provider
3. Parent model verbatim (silent inherit)

### 2026-05-06 — Profile Propagation
**Commit:** `76b06461`  
Propagate active profile environment to child processes. Harden subagent command quoting.

---

## Current Tool Inventory

As of May 2026, the agent has 20 tools across 4 groups:

### Local Tools (15)
- `run_command` — sync shell execution
- `run_remote_command` — SSH shell execution
- `run_command_task` — async background local command
- `run_remote_command_task` — async background remote command
- `get_all_tasks` — list background tasks
- `cancel_task` — cancel a background task
- `wait_for_tasks` — wait for tasks to complete
- `get_task_details` — detailed task info
- `view` — read files/directories (with grep, glob, tree, remote)
- `str_replace` — string replacement in files
- `create` — create new files
- `generate_password` — secure password generation
- `view_web_page` — fetch web pages as markdown
- `remove` — delete files/directories (with backup)
- `ask_user` — structured user prompts

### Remote Tools (2)
- `search_docs` — web search for technical docs
- `load_skill` — load skills by URI

### Subagent Tools (2)
- `dynamic_subagent_task` — spawn background subagent
- `resume_subagent_task` — resume/pause subagent

### Slack Tools (3, optional)
- `slack_read_messages`
- `slack_read_replies`
- `slack_send_message`

### Removed Tools
- `insert` — merged into `str_replace`
- `generate_code` — disabled, too complex
- `search_memory` — removed, unreliable
- `read_rulebook` — renamed to `load_skill`
- `remote_code_search` — removed

---

## Design Principles That Emerged

1. **Tool descriptions are prompts.** Iterate on them. Measure tool call accuracy. Six commits for one description is normal.

2. **Validate at the boundary.** The LLM sends empty arrays, 10,000-char strings, and wrong formats. Fail fast with structured errors.

3. **Truncate everything.** Shell output, web pages, search results — cap them before they blow the context window.

4. **Async is a different beast.** Background tasks need start, poll, wait, cancel, and get-details. Don't add async unless you need it.

5. **Approval is your security model.** Read-only tools: auto-approve. Write tools: require approval. Subagent spawning: extra scrutiny.

6. **Remove broken tools.** `generate_code`, `search_memory`, `insert` — all removed because they didn't work well enough.

7. **Naming is a contract.** `cancel` → `cancel_task`, `subagent_task` → `dynamic_subagent_task`. Mismatches break auto-approve, TUI rendering, and the LLM's understanding.

8. **Security migrates up.** Started with per-tool secret redaction. Ended with centralized proxy-level redaction.

9. **Backward compat matters.** `read_rulebook` still works via alias to `load_skill`. Don't break user configs on renames.

10. **Sandbox by default.** Dangerous commands run in containers. Subagents get least-privilege tool access. The LLM is not trusted.
