# MOO Programming Quickstart

This quickstart distills key practices from the mooR book so automation authors can reason about in-MOO code when coordinating with the MCP server.

## Verb anatomy
- **Names & permissions** – Verbs live on objects and declare permissions such as `rxd`. Use wizard contexts when modifying system verbs.
- **Arguments** – mooR verbs accept positional arguments via the verb editor. Automation tools pass JSON arrays that map to those positions.
- **Task model** – Verb execution creates a task that may be suspended or queued. Long-running verbs should explicitly fork or notify to avoid blocking.
- **Return values** – Implicit `0` returns can confuse automation. Use explicit `return` statements for values consumed by MCP clients.

## Development cycle
1. Prototype source in files kept under version control (`doc/executed_moo/` contains canonical examples).
2. Use the REST toolbelt or MCP prompts to ensure verbs exist before uploading code.
3. Program verbs via REST (`program_verb`) so compilation errors are surfaced as JSON payloads.
4. Invoke verbs with representative arguments and capture outputs for later regression checks.
5. When modifying shared prototypes, notify downstream users because changes propagate to inherited objects.

## Defensive patterns
- Validate argument types early and return helpful error strings for automation clients.
- Reuse shared helpers like `$wiz_utils:ensure_player()` or `$fate:resolve_action()` rather than duplicating logic.
- Guard dangerous operations (recycling, teleportation, data writes) behind permission checks and audit history logging.
- For asynchronous flows, send presentations or notifications so humans see the result even if an automation client initiated the change.

## Working with MCP
- Treat the MCP `update-verb` prompt as a guide: it walks through resolution, ensuring, programming, and verification steps.
- When debugging, pair `eval_expr` calls with telnet sessions to cross-validate behavior.
- Document any custom verbs you introduce by adding markdown resources alongside this quickstart.
