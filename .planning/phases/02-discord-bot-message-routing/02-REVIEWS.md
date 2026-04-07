---
phase: 02
reviewers: [codex]
reviewed_at: 2026-04-07
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md]
---

# Cross-AI Plan Review — Phase 02

## Codex Review

### Plan 02-01: Bot Infrastructure

**Summary**
This is a solid foundation plan and the dependency split is mostly correct: config expansion, bot bootstrap, and lifecycle callback wiring belong in Wave 1. The biggest issue is that the plan appears to stop at infrastructure without explicitly defining the runtime routing path for future command delivery, so it supports Phase 2 scaffolding but does not yet fully prove the channel-to-agent delivery goal. The same-process, single-loop design is appropriate for the stack, but startup sequencing, config validation, and callback failure isolation need to be specified more clearly.

**Strengths**
- Clear alignment with D-01 and D-02: one process, one asyncio loop, WS server first, Discord second.
- Static config extension for guild allowlist and channel mapping matches ROUT-01, ROUT-02, and AUTH-04 cleanly.
- `setup_hook` for guild command sync is the right place for Discord app-command initialization.
- Adding connect/disconnect callbacks to `AgentManager` creates a clean integration point for AGNT-03 later.
- Keeping this wave focused on bootstrapping reduces coupling with command implementation.

**Concerns**
- **HIGH**: The plan does not explicitly define how a Discord channel ID resolves to an agent session at runtime. Without a concrete routing interface on `AgentManager`, ROUT-01 is only partially implemented.
- **HIGH**: Guild allowlist enforcement in `setup_hook` is not sufficient by itself. `setup_hook` runs at startup; it does not protect all later interactions or unexpected guild joins.
- **MEDIUM**: No explicit startup failure policy is described for invalid config, missing token, duplicate channel mappings, malformed IDs, or bot login failure.
- **MEDIUM**: Connect/disconnect callbacks can destabilize the transport layer if notification-side exceptions propagate back into agent lifecycle handling.
- **MEDIUM**: The plan says "8 files modified" but the scope implies cross-cutting boot logic, config, manager, and bot package changes. That is manageable, but easy to under-specify.
- **LOW**: ROUT-05 is listed, but "runs on user hardware" is more of a deployment property than something this plan materially implements.

**Suggestions**
- Define an explicit routing API now, such as `get_agent_for_channel(channel_id)` or `get_channel_for_agent(agent_id)`, with validation for one-channel-to-one-agent invariants.
- Validate config at startup and fail fast on duplicate mappings, empty allowlists where disallowed, malformed Discord IDs, or missing token path.
- Specify exception boundaries for lifecycle callbacks so agent connectivity cannot be broken by Discord-side send failures.
- Define bot startup behavior when Discord login fails after WS startup: exit process, retry with backoff, or run degraded transport-only mode.
- Add explicit handling for unauthorized guild presence at runtime, not just during command sync.

**Risk Assessment:** MEDIUM

---

### Plan 02-02: Slash Commands & Notifications

**Summary**
This plan covers most visible Phase 2 behavior and maps well to the user decisions: slash-only commands, embeds for `/status` and `/help`, hot reload, and agent presence notifications. The main risk is requirement drift: Phase success criterion 1 talks about user messages reaching agents, but the plan implements slash commands only and does not clearly state whether machine-bound actions are deferred to a later phase. Auto-channel creation also introduces scope and security complexity that is not fully accounted for in the stated requirements.

**Strengths**
- Good use of a cog boundary for command concerns.
- `/status`, `/help`, `/ping`, and `/reload` match D-08 directly.
- Embed-based output matches D-09 and should improve Discord usability.
- `interaction_check` for user and guild allowlist enforcement is the correct per-command control point.
- `default_permissions(administrator=True)` is a reasonable UX layer for hiding commands.
- Agent connect/disconnect notifications directly support AGNT-03 and D-20/21/22.

**Concerns**
- **HIGH**: The phase goal says users can send messages that reach the correct machine agent, but this plan contains no agent-targeted execution command. There is a mismatch between roadmap wording and planned implementation.
- **HIGH**: Auto-creating channels for unmapped agents conflicts with ROUT-02's "static config file" model unless the plan clearly defines persistence semantics.
- **HIGH**: `default_permissions(administrator=True)` does not replace server-side authorization. Allowlist checks must remain authoritative.
- **MEDIUM**: `/reload` can race with command execution or notification callbacks if config objects are replaced live without synchronization.
- **MEDIUM**: Agent status notifications need behavior for missing channel permissions, deleted channels, and stale mappings.
- **MEDIUM**: `/status` needs defined representation for disconnected but configured agents versus currently connected agents.
- **MEDIUM**: Auto-channel creation can produce channel spam if agents reconnect with unstable identifiers or duplicate names.
- **LOW**: `/ping` is useful but not tied to any listed Phase 2 requirement.

**Suggestions**
- Resolve the requirement mismatch explicitly: state that Phase 2 delivers slash-command control primitives, not free-form machine command execution (Phase 3).
- Define auto-channel creation semantics: persistence, naming, duplicate prevention.
- Treat `interaction_check` as mandatory security gate; document `default_permissions` as UI hiding only.
- Put `/reload` behind a lock and use atomic config replacement.
- Define notification error handling: log and continue on Discord API failures.
- Specify `/status` output for three cases: connected mapped, configured-but-offline, connected-but-unmapped.

**Risk Assessment:** MEDIUM-HIGH

---

### Plan 02-03: Tests

**Summary**
The test plan is directionally good and covers the core surfaces: routing, config, auth, commands, and notifications. The weakness is that it is too unit-heavy for a phase whose main failure modes are integration failures across Discord config, agent lifecycle events, and runtime routing.

**Strengths**
- Good separation of test concerns by domain.
- `test_auth.py` directly targets the most important security invariants.
- `test_config.py` is appropriate given the static-config dependency.
- Testing channel-name sanitization anticipates a real Discord integration edge case.

**Concerns**
- **HIGH**: No integration tests for end-to-end agent connect/disconnect to Discord notification flow.
- **HIGH**: No tests for `/reload` concurrency, invalid config reload, or rollback behavior.
- **MEDIUM**: No explicit tests for unauthorized guilds/users attempting every slash command path.
- **MEDIUM**: No tests for duplicate or conflicting channel mappings, malformed IDs.
- **MEDIUM**: No tests for Discord send failures (permissions, missing channels, HTTP exceptions).

**Suggestions**
- Add integration-style async test with mocked Discord objects for notification flow.
- Add reload tests: successful, invalid config rejected, concurrent reads during reload.
- Add negative auth tests for every command, not just helper predicates.
- Add config validation tests for duplicate mappings, non-numeric IDs.
- Add `/status` matrix tests covering connected, disconnected, configured-only, unmapped agents.

**Risk Assessment:** MEDIUM

---

## Consensus Summary

### Agreed Strengths
- Architecture decisions (single process, single loop, WS first) are sound and well-aligned with project constraints
- Security is considered early through guild and user allowlists at multiple layers
- Dependency ordering avoids building commands before infrastructure exists
- Testing treated as its own wave rather than omitted

### Agreed Concerns
- **Phase goal vs implementation scope mismatch**: Roadmap says "messages reach the correct machine agent" but Phase 2 only builds slash command infrastructure — command execution is Phase 3. This is correct scoping but the roadmap wording creates confusion.
- **Auto-channel creation complexity**: Introduces state mutation and operational complexity into an otherwise static-config phase. Persistence, naming, and duplicate prevention semantics need tightening.
- **Reload and notification concurrency**: Config replacement during command execution or notification callbacks is under-specified. Needs synchronization.
- **Auth defense-in-depth**: `default_permissions` is UI hiding only; `interaction_check` is the real security gate. This should be explicitly documented.
- **Test coverage gaps**: Unit-heavy approach misses integration-level failure modes (notification flow, reload safety, Discord API failures).

### Divergent Views
- None (single reviewer) — recommend running with additional AI CLI (gemini) for divergent perspective in future reviews.
