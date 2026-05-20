# Stakpak Agent — Tool Design Evolution

A practical case study of how agent tool definitions evolved over ~12 months in
the [stakpak/agent](https://github.com/stakpak/agent) repository, mined from git
history. Useful as a workshop reference for tool design.

> **Source files traced:**
> `mcp/server/src/tools.rs` (initial monolith) → split into
> `libs/mcp/server/src/{local_tools,remote_tools,subagent_tools}.rs`
> plus `libs/shared/src/models/tools/ask_user.rs`.
>
> **Time range:** 2025-05-18 (genesis) → 2026-05-19 (HEAD on `main`).
> **Total commits touching tool definitions:** ~178 (de-duped across
> branches).

---

## 1. Timeline at a glance

| Date       | Commit      | Milestone                                                 | Tools (post-commit)                                                                                                                  |
| ---------- | ----------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 2025-05-18 | `f89c0d7b`  | **Genesis MCP server**                                    | `run_command`, `read_file`                                                                                                           |
| 2025-05-27 | `dd2c0d90`  | Text editor toolkit                                       | + `view`, `str_replace`, `create`, `insert` (replaces `read_file`)                                                                  |
| 2025-06-08 | `9b4897ae`  | **Split into local/remote tools**, descriptions extracted | + remote: `generate_code`, `smart_search_code`                                                                                       |
| 2025-06-19 | `e382a1e6`  | Search tools                                              | + `search_docs`, `search_memory` (later), `local_code_search`, `read_rulebook`                                                       |
| 2025-06-29 | `f4d0bdfe`  | Password tool, drop `insert`                              | + `generate_password`; − `insert`                                                                                                    |
| 2025-07-05 | `ba386a43`  | Timeouts on `run_command`, drop `workdir`                 | API tightening                                                                                                                       |
| 2025-07-09 | `50274cba`  | **Async tools**                                           | + `run_command_task`, `get_all_tasks`, `get_task_details`, `cancel_task`                                                             |
| 2025-07-29 | `bbabd63c`  | Web fetching                                              | + `view_web_page`                                                                                                                    |
| 2025-08-14 | `7cb1e45f`  | **Subagent tool** (initial)                               | + `task` (renamed `subagent_task`); local tools become **dual local/remote** (SSH support added to `run_command`/`view`/etc.)         |
| 2025-08-15 | `e2e55fc1`  | `wait_for_tasks` for async coordination                   | + `wait_for_tasks`                                                                                                                   |
| 2025-08-16 | `28e1a65c`  | **Disable `generate_code`** (LLM does it directly)        | − (commented out)                                                                                                                    |
| 2025-09-22 | `efae0250`  | Reversible **`remove`** with auto-backup                  | + `remove`                                                                                                                           |
| 2025-09-24 | `3101b8a9`  | Reversible `str_replace` (udiff output)                   | refinement                                                                                                                           |
| 2025-11-05 | `eb316bdc`  | Disable `local_code_search`                               | − (commented out)                                                                                                                    |
| 2025-12-17 | `41bacde7`  | **Description compression pass**                          | -77 LOC of descriptions                                                                                                              |
| 2026-01-15 | `6d5c8603`  | Persistent shell sessions                                 | execution-layer change                                                                                                               |
| 2026-01-30 | `6baf4f34`  | `view` gains `grep` + `glob` params                       | replaces ad-hoc `find`/`grep` shell calls                                                                                            |
| 2026-02-05 | `b238ec90`  | **Dynamic subagents (AOrchestra 4-tuple)**                | `subagent_task` → `dynamic_subagent_task`                                                                                            |
| 2026-02-10 | `79af6a8e`  | **`load_skill` replaces `read_rulebook`**                 | + `load_skill`; − `read_rulebook`                                                                                                    |
| ~2026-04   | `3b96d089`  | **`ask_user` tool** for structured prompts                | + `ask_user`                                                                                                                         |
| 2026-05-19 | HEAD        | Current shape                                             | 17 active tools (see §6)                                                                                                             |

---

## 2. Tool count over time (active tool definitions)

```
2025-05-18 ░░ 2 tools          (run_command, read_file)
2025-05-27 ░░░░░ 5 tools       (+ view, str_replace, create, insert; – read_file)
2025-06-08 ░░░░░░░ 7 tools     (+ generate_code, smart_search_code)
2025-06-29 ░░░░░░░░░░░ 11      (+ password, search_docs, search_memory, rulebook, local_code_search, remote_code_search; – insert)
2025-07-09 ░░░░░░░░░░░░░░ 14   (+ run_command_task, get_all_tasks, get_task_details, cancel_task)
2025-08-15 ░░░░░░░░░░░░░░░░ 16 (+ subagent_task, wait_for_tasks, view_web_page)
2025-08-16 ░░░░░░░░░░░░░░░ 15  (– generate_code disabled)
2025-09-22 ░░░░░░░░░░░░░░░░ 16 (+ remove)
2025-11-05 ░░░░░░░░░░░░░░░ 15  (– local_code_search disabled)
2026-02-10 ░░░░░░░░░░░░░░░ 15  (load_skill replaces read_rulebook 1:1)
2026-02-05 ░░░░░░░░░░░░░░░ 15  (subagent_task → dynamic_subagent_task + resume_subagent_task)
2026-04-?? ░░░░░░░░░░░░░░░░ 17 (+ ask_user, + run_remote_command/_task split out)
```

The shape is **fast growth then slow contraction/refinement** — classic
toolbelt bloat correction.

---

## 3. Architectural inflection points

### 3.1. Genesis: the "two tool" agent (May 18, 2025)

The very first MCP server had exactly 2 tools, with strikingly generic
descriptions:

```rust
#[tool(description = "A system command execution tool that allows running
shell commands with full system access.")]
fn run_command(&self, command: String) -> Result<CallToolResult, McpError>

#[tool(description = "A system command execution tool that allows running
shell commands with full system access.")]   // ← same description, copy-paste
fn read_file(&self, path: String) -> Result<CallToolResult, McpError>
```

Note both tools shared the **same description** — a giveaway that the
description was an afterthought. This is a common starting state.

**Lesson #1 — Even copy-pasted descriptions ship.** Initial
prototypes don't get descriptions right, but they still work because the
tool _name_ is doing the heavy lifting at first.

---

### 3.2. The text-editor split (May 27, 2025)

`read_file` was deleted and replaced by a **purpose-built editor toolkit**:

| Replaced               | New tools                                |
| ---------------------- | ---------------------------------------- |
| `read_file(path)`      | `view(path, view_range?)`                |
| ad-hoc shell mutations | `str_replace`, `create`, `insert`        |

Why this matters:
- **`view` ≠ `read_file`**: it can list directories AND read files AND take a
  line range. One verb, multiple shapes.
- File mutation became **structured** (no more "echo > file.txt" tricks).
- This pattern (`view` / `str_replace` / `create`) became the canonical
  Anthropic-style file-editing toolset and remains intact through HEAD.

**Lesson #2 — Don't expose primitives, expose intents.** `read_file` is
a primitive; `view` is an intent that maps to many file-system operations.

---

### 3.3. Tool descriptions extracted to constants (June 8, 2025)

Commit `9b4897ae` ("Split mcp and allow to run standalone") split the
monolithic `tools.rs` into `local_tools.rs` + `remote_tools.rs` and introduced
**`tool_descriptions.rs`** — a dedicated file of `pub const X_DESCRIPTION`
strings shared between local and remote variants:

```rust
pub const RUN_COMMAND_DESCRIPTION: &str = "A system command execution
tool that allows running shell commands ...

SECRET HANDLING:
- Output containing secrets will be redacted ...
";
```

This is the moment **descriptions became first-class artifacts** rather
than inline prose. From here on, description changes show up as standalone
diffs against constants. The file was later removed when descriptions were
inlined again (cleaner diffs once tools weren't sharing them across crates).

**Lesson #3 — Descriptions are part of your API surface.** Treat them
like docstrings: version them, review them, test them.

---

### 3.4. Remote/SSH duality (Aug 14, 2025)

Up until commit `7cb1e45f`, every "local" tool was a separate function
from its remote/SSH equivalent. The subagent commit collapsed them:

```rust
// Before: separate tools
run_command(...)            // local only
remote_run_command(...)     // SSH

// After: single tool, branches by parameter
run_command(
    command,
    remote: Option<String>,        // user@host[:port]
    password: Option<String>,
    private_key_path: Option<String>,
)
```

The same path was applied to `view`, `str_replace`, `create`, `remove`. This
**halved the tool count** without losing functionality.

But the team then realized the dual-mode had a UX problem (LLMs forgot to
pass `remote=`), so by HEAD the design **partially reverted**:

```
HEAD has BOTH:
  run_command            (local-only, simpler signature)
  run_remote_command     (SSH, explicit)
  run_command_task       (local async)
  run_remote_command_task (SSH async)
```

**Lesson #4 — One tool with optional fields ≠ one tool with two
behaviors.** When two variants have measurably different mental models,
splitting them produces better LLM behavior even at the cost of more tools.

---

### 3.5. The "everything is async" wave (July 9, 2025)

Commit `50274cba` introduced the async task subsystem:

```
+ run_command_task        (fire-and-forget background command)
+ get_all_tasks           (status table)
+ get_task_details        (single task detail)
+ cancel_task             (kill a task)
+ wait_for_tasks          (block until tasks finish)  -- added later
```

This is a **5-tool feature** for one capability. Notice the mental model:
tools are not just verbs, they're **a state machine API** for managing
background work — `start → query → wait → cancel`.

**Lesson #5 — Long-running operations need a coherent task model.**
A single `run_command_async` returning a task ID is not enough; the
agent also needs `query`, `wait`, and `cancel` as explicit tools.

---

### 3.6. Reversibility (Sept 22–24, 2025)

Two commits in two days made mutating tools **reversible**:

- `efae0250`: `remove` tool **moves files to a backup directory** instead of
  unlinking. The description teaches the agent how to recover.
- `3101b8a9`: `str_replace` returns a **udiff** in its result, so the
  agent (and the user) can see/undo what changed.

This is a deliberate design choice: every destructive tool produces enough
output to undo itself.

**Lesson #6 — Mutating tools should be observable AND reversible.**
The tool's output is part of the tool's contract; use it to produce
audit/undo information for free.

---

### 3.7. Disabling tools that turned out worse than the LLM (Aug 16 / Nov 5, 2025)

Two notable removals:
- `28e1a65c`: **`generate_code` disabled** ("Disable generate_code tool")
- `eb316bdc`: **`local_code_search` disabled** ("Temporarily disable
  local_code_search")

Both tools were complex backends (a code-gen API and a Tantivy/Docker-based
indexer). They were disabled because the **frontier LLM with `view` + `grep`
+ `view_web_page` outperformed them**. The tool definitions are
commented out at HEAD, kept around as fossils.

**Lesson #7 — Sometimes the best tool design is _no tool_.** As LLMs
improve, sophisticated tools collapse into combinations of simple tools.
Audit your toolbelt periodically and prune.

---

### 3.8. Descriptions: long → short → long again

Three eras of `run_command`'s description:

**Era 1 (2025-05-18, genesis):** _generic_
> "A system command execution tool that allows running shell commands with full system access."

**Era 2 (2025-07-05, peak verbosity):** _maximal context_
> "A system command execution tool that allows running shell commands with full system access.
>
> SECRET HANDLING:
> - Output containing secrets will be redacted and shown as placeholders ...
> - You can use these placeholders in subsequent commands ...
> - Example: If you see 'export API_KEY=[REDACTED_SECRET:api-key:abc123]', ...
>
> If the command's output exceeds 300 lines the result will be truncated and
> the full output will be saved to a file in the current directory."

**Era 3 (2025-12-17, `41bacde7` — compression pass):** _terse_
> "Execute shell commands locally or remotely via SSH."

**Era 4 (HEAD, 2026-05-19):** _structured + practical_
> "Execute a shell command locally with full system access.
>
> If the command's output exceeds 300 lines the result will be truncated and the
> full output will be saved to a file in the current directory.
>
> For remote command execution via SSH, use the run_remote_command tool instead."

The final form keeps the **most important behaviors** (truncation, related
tool pointer) and drops everything that the LLM either already knew or that
was better moved to other documentation.

The compression commit (`41bacde7`) explicitly says *"Improve conciseness
and clarity of tool descriptions"* and removed **177 lines of description
text from `local_tools.rs`** (alongside 21 from remote_tools).

**Lesson #8 — Description length follows a U-curve.** Start short → grow
as you discover failure modes → compress once you understand what
matters. Aim to land in "structured + practical".

---

### 3.9. The `ask_user` tool (~2026-04)

`ask_user` is a unique tool: it doesn't actually do anything in the MCP
server — its handler returns `INTERACTIVE_REQUIRED`:

```rust
#[tool(description = "Ask the user one or more questions with predefined options. ...")]
pub async fn ask_user(...) -> Result<CallToolResult, McpError> {
    // This tool is handled specially by the TUI - it should never reach here
    Ok(CallToolResult::error(vec![
        Content::text("INTERACTIVE_REQUIRED"),
        ...
    ]))
}
```

The **TUI intercepts the tool call** and renders an interactive prompt with
multi-select / radio options. This pattern — *tool definition exists purely
to make the LLM emit a structured payload that the host then handles* — is
incredibly powerful.

**Lesson #9 — Tools don't have to be back-end calls.** A tool can be a
pure protocol/UI affordance. The schema is the value.

---

### 3.10. AOrchestra 4-tuple subagents (Feb 5, 2026)

`subagent_task` evolved from a simple "run another agent on this prompt"
tool into `dynamic_subagent_task` modeled on AOrchestra's 4-tuple
**(Instruction, Context, Tools, Model)**:

```rust
pub struct DynamicSubagentRequest {
    description: String,           // 3-5 word task name (UI tab label)
    instructions: String,          // I — what to do
    context: Option<String>,       // C — curated findings, what failed
    tools: Vec<String>,            // T — least-privilege tool list
    model: Option<String>,         // M — hidden from LLM, resolved by config
    max_steps: Option<usize>,
    enable_sandbox: bool,          // warden container isolation
}
```

Two notable design moves:
1. **`model` is `#[schemars(skip)]`** — hidden from the JSON schema so the
   LLM cannot pick a model. Resolution is done by the parent agent based on
   profile config.
2. **`tools: Vec<String>` is required** — you cannot delegate without
   committing to a tool list. This forces the parent to think about
   least-privilege.

**Lesson #10 — Hide what should not be agent-decided.** Use the
`#[schemars(skip)]` attribute (or your framework's equivalent) to keep
fields in your data type but out of the agent's choice surface.

---

## 4. Schema and parameter design patterns

Across all 178 commits, a few patterns emerged that you should consider:

### 4.1. From positional `#[tool(param)]` to `Parameters<Struct>`

Early (`f89c0d7b`):
```rust
fn run_command(
    &self,
    #[tool(param)]
    #[schemars(description = "The shell command to execute")]
    command: String,
) -> Result<CallToolResult, McpError>
```

Current (HEAD):
```rust
#[derive(Debug, Deserialize, schemars::JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct RunCommandRequest {
    #[schemars(description = "The shell command to execute")]
    pub command: String,
    #[schemars(description = "Optional description of the command to execute")]
    pub description: Option<String>,
    #[schemars(description = "Optional timeout for the command execution in seconds")]
    pub timeout: Option<u64>,
}

pub async fn run_command(
    &self,
    ctx: RequestContext<RoleServer>,
    Parameters(RunCommandRequest { command, description: _, timeout }): Parameters<RunCommandRequest>,
) -> Result<CallToolResult, McpError>
```

Benefits:
- `#[serde(deny_unknown_fields)]` catches LLM hallucinated parameters.
- Parameters are reusable as types in tests.
- Optional fields are explicit (`Option<T>`) — no ambiguity.
- The struct doc and field docs become the schema.

### 4.2. Rich enums via `description` for valid values

Where a free-form `String` could have been used, descriptions encode
validation hints:

```rust
#[schemars(description = "Display directory as a nested tree structure (default: false)")]
pub tree: Option<bool>,
```

```rust
#[schemars(description = "Optional line range to view [start_line, end_line].
                          Line numbers are 1-indexed. Use -1 for end_line to
                          read to end of file.")]
pub view_range: Option<[i32; 2]>,
```

Note the `[i32; 2]` array type with sentinel `-1` — this is a small DSL
encoded in the schema. The description is _also_ part of validation
("default: false", "1-indexed", "Use -1 for ...").

### 4.3. "Worked examples" land inside descriptions

The current `search_docs` description includes:

```
✅ keywords: ["stakpak", "cli", "latest"]
✅ keywords: ["kubernetes", "ingress", "nginx", "ssl"]
✅ legacy keywords: "kubernetes ingress nginx ssl"
```

Tool descriptions are a great place for **few-shot examples** because they
appear in every tool selection turn. Use them to encode the "happy path"
shape, not just the parameter types.

### 4.4. Pointers to other tools

Modern descriptions often **steer the LLM to better tools**:

> "For remote command execution via SSH, use the `run_remote_command` tool
> instead."

> "Use `view` instead of shell commands like `cat`, `ls`, `find` — it's
> faster and doesn't need approval."

This functions like cross-references in API docs. Useful when you have
overlapping tools and want to guide selection.

---

## 5. Anti-patterns observed (and corrected)

| Anti-pattern                                                                       | Where seen                                       | Fix                                              |
| ---------------------------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------ |
| Identical descriptions on different tools                                          | `f89c0d7b`                                       | Differentiate                                    |
| Unbounded shell command (no timeout, no truncation)                                | `f89c0d7b`–`b9c3da04`                            | Added `timeout`, output clipping (`5916a54a`)    |
| `workdir` parameter the LLM kept misusing                                           | through `ba386a43`                               | Removed in `ba386a43` ("remove workdir")          |
| One tool that does both local AND remote with magic string                         | `7cb1e45f`                                       | Split into `run_command` / `run_remote_command`  |
| `cancel_async_task` named ambiguously alongside `cancel_task`                      | through `d5f82585`                               | Renamed to disambiguate (`Rename cancel tool…`)  |
| Tools that re-implement what the model is good at (`generate_code`)                | `9b4897ae`–`28e1a65c`                            | Disabled in favor of `view` + `str_replace`       |
| Description bloat (paragraph-level secret-handling notes on every tool)            | `9b4897ae`–`41bacde7`                            | Compression pass `41bacde7`                      |
| Destructive ops with no recovery path                                              | `remove` original                                | `efae0250` — auto-backup + recoverable           |

---

## 6. The current toolbelt (HEAD, 2026-05-19)

**Local file & shell** (`local_tools.rs`):
- `run_command` — local shell, with timeout
- `run_remote_command` — SSH shell, with timeout
- `run_command_task` — local async (returns task_id)
- `run_remote_command_task` — SSH async
- `wait_for_tasks` — block on task IDs
- `cancel_task` — kill a task
- `get_all_tasks` — task table
- `get_task_details` — single task with full output
- `view` — file or directory listing, with `view_range` / `grep` / `glob` / `tree`
- `str_replace` — exact-match replacement (with udiff output)
- `create` — write new file (fails if exists)
- `remove` — recoverable delete (auto-backup)
- `generate_password` — cryptographically secure password
- `view_web_page` — fetch HTTPS URL → markdown
- `ask_user` — interactive multi-question UI prompt

**Remote/server** (`remote_tools.rs`):
- `search_docs` — vector search over technical docs
- `load_skill` — fetch a SKILL.md by URI
- ~~`search_memory`~~ (commented out at HEAD)
- ~~`generate_code`, `local_code_search`, `read_rulebook`~~ (replaced/commented out)

**Subagent** (`subagent_tools.rs`):
- `dynamic_subagent_task` — AOrchestra 4-tuple delegation
- `resume_subagent_task` — resume paused subagents (tool-approval pauses, etc.)

**Total: 17 active, 4 deprecated/disabled.**

---

## 7. Workshop takeaways

1. **Start with 2 tools, not 20.** `run_command` + `read_file` was enough
   to ship a working agent. Tools accreted from real failure modes.
2. **Tool _names_ matter more than descriptions for selection.** But
   descriptions matter for _correct invocation_.
3. **Verb-as-intent, not verb-as-primitive.** `view` (intent) beats
   `read_file` (primitive) because it absorbs sibling needs (directory
   listing, line ranges, tree view, grep, glob).
4. **Async = state machine.** A single `run_async` is not enough; you need
   `start / query / wait / cancel`.
5. **Reversibility is a feature.** `remove` with backup, `str_replace`
   with udiff. Make destructive operations cheap to undo.
6. **U-shaped descriptions.** Generic → bloated → tight + structured.
   Schedule a periodic compression pass.
7. **Hide non-agent fields.** `#[schemars(skip)]` on `model` is the
   reason subagents have predictable behavior.
8. **Some tools are pure protocol.** `ask_user` is "just" a schema; the
   host UI does the real work.
9. **Prune as the model improves.** `generate_code` and `local_code_search`
   were sophisticated tools that got worse than `view + grep + str_replace`
   on a frontier LLM. Disable, don't delete.
10. **Tool design is iterative.** 178 commits over ~12 months for ~17 tools.
    That's roughly **10 commits per tool**, or ~1 design change per tool
    per month. Plan for ongoing tuning.

---

## Appendix — How to reproduce this analysis

```bash
# All commits that touched any tool definition file:
git log --all --oneline --reverse \
  --pretty=format:"%h|%ad|%s" --date=short \
  -- 'mcp/server/src/tools.rs' \
     'libs/mcp/server/src/tools.rs' \
     'libs/mcp/server/src/local_tools.rs' \
     'libs/mcp/server/src/remote_tools.rs' \
     'libs/mcp/server/src/subagent_tools.rs'

# Tool list at any commit:
git show <commit>:libs/mcp/server/src/local_tools.rs |
  python3 -c "
import sys, re
content = sys.stdin.read()
pattern = re.compile(r'#\[tool\([^\]]*\)\]\s*(?:#\[[^\]]*\]\s*)*(?:pub\s+)?(?:async\s+)?fn\s+([a-z_]+)', re.DOTALL)
for m in pattern.finditer(content): print(m.group(1))
"

# Description-only diff for a single tool:
git log -p --follow -- libs/mcp/server/src/local_tools.rs |
  grep -E '^[+-].*description' | grep -i 'run_command'
```
