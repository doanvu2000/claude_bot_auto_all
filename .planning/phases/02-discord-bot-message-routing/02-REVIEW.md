---
status: issues_found
phase: 02
depth: standard
files_reviewed: 13
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
---

# Code Review: Phase 02

## Summary

Phase 02 implements the Discord bot foundation, slash commands, channel-to-agent routing, and WebSocket agent management. Overall code quality is good with proper async patterns, layered auth checks, and reasonable error handling. Key concerns: a reload_config race condition that can leave config partially updated on failure, non-atomic file writes in save_config, and channel name sanitization divergence between code and tests.

## Findings

### R02-01 [critical] reload_config partially mutates state on JSON parse failure
**File:** bot/config.py:99-114
**Description:** `reload_config` reads the file and then calls `json.loads(content)`. If parsing succeeds but a subsequent `int()` conversion fails on a malformed guild ID (e.g., `"abc"`), `allowed_guild_ids` may be partially updated while `allowed_user_ids` and `channel_mapping` retain old values. The config ends up in an inconsistent state. The test `test_reload_invalid_json_raises` only tests malformed JSON (which fails before any mutation), not malformed values inside valid JSON.
**Suggestion:** Read all new values into local variables first, then assign to `self` only after all parsing succeeds:
```python
async def reload_config(self) -> None:
    async with self._config_lock:
        async with aiofiles.open(self.config_path, "r") as f:
            content = await f.read()
        data = json.loads(content)
        discord_cfg = data.get("discord", {})
        # Parse into locals first
        new_guilds = [int(gid) for gid in discord_cfg.get("allowed_guild_ids", [])]
        new_users = [int(uid) for uid in discord_cfg.get("allowed_user_ids", [])]
        new_mapping = {str(k): str(v) for k, v in discord_cfg.get("channel_mapping", {}).items()}
        # Atomic swap
        self.allowed_guild_ids = new_guilds
        self.allowed_user_ids = new_users
        self.channel_mapping = new_mapping
```

### R02-02 [warning] save_config is not atomic -- partial writes on crash
**File:** bot/config.py:66-87
**Description:** `save_config` opens the file with mode `"w"` (which truncates immediately), then writes. If the process crashes or loses power mid-write, `config.json` will be truncated or partially written. On next startup, `load_bot_config` will fail to parse it.
**Suggestion:** Write to a temporary file in the same directory, then rename (atomic on most filesystems). On Windows, use `os.replace()`:
```python
import tempfile, os
tmp_path = self.config_path + ".tmp"
async with aiofiles.open(tmp_path, "w") as f:
    await f.write(new_content)
os.replace(tmp_path, self.config_path)
```

### R02-03 [warning] Channel name sanitization does not strip leading/trailing hyphens
**File:** bot/discord_bot.py:120-122
**Description:** The sanitization logic replaces spaces and underscores with hyphens, then filters to alphanumeric + hyphen. Names like `"___underscores___"` produce `"---underscores---"` which Discord may reject or display oddly. The test in `test_notifications.py:155` adds `.strip("-")` but the production code does not.
**Suggestion:** Add `channel_name = channel_name.strip("-")` after the filter step in `_auto_create_channel`, or add a leading/trailing hyphen strip. Align test and production logic.

### R02-04 [warning] _remove_agent fires async callback via create_task but is a sync method
**File:** bot/server.py:131-139
**Description:** `_remove_agent` is a synchronous method that calls `asyncio.create_task()` to schedule the disconnect callback. If `_remove_agent` is ever called outside an async context (no running event loop), `create_task` will raise `RuntimeError`. More importantly, any exception in the callback task will be silently swallowed as an unhandled task exception unless a `done_callback` is added.
**Suggestion:** Either make `_remove_agent` async and `await` the callback (like `_authenticate` does for connect), or add a `done_callback` to log exceptions from the fire-and-forget task:
```python
task = asyncio.create_task(self.on_agent_disconnect(machine_name))
task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
```

### R02-05 [warning] Unused import: signal in server.py (used only in standalone start_server)
**File:** bot/server.py:7
**Description:** The `signal` import is used by `start_server()` at the bottom of the file, but `start_server()` is a standalone entry point that is never called by the bot (which uses `__main__.py` instead). On Windows, `signal.SIGTERM` is not supported and will raise `AttributeError` if `start_server()` is invoked.
**Suggestion:** Guard the SIGTERM handler: `if hasattr(signal, 'SIGTERM'): signal.signal(signal.SIGTERM, _signal_handler)`. Or remove `start_server()` entirely if it is dead code.

### R02-06 [warning] /reload syncs commands to guilds inside interaction handler -- potential timeout
**File:** bot/cogs/general.py:144-148
**Description:** The `/reload` command loops over all allowed guilds and calls `tree.sync()` for each. Discord interaction responses must be sent within 3 seconds. If there are multiple guilds or Discord API is slow, the sync loop may exceed the timeout, causing the interaction to fail with "This interaction failed."
**Suggestion:** Send the response first (or `defer()` the interaction), then sync commands in the background:
```python
await interaction.response.defer(ephemeral=True)
await self.bot.bot_config.reload_config()
for guild_id in self.bot.bot_config.allowed_guild_ids:
    ...
await interaction.followup.send("Config reloaded successfully.")
```

### R02-07 [warning] f-string in logger calls -- loguru evaluates even at suppressed levels
**File:** bot/__main__.py:28, bot/discord_bot.py:69, bot/server.py:103 (and others)
**Description:** Multiple files use `logger.info(f"...")` with f-strings. Loguru evaluates the f-string even if the log level is above INFO. This is a minor performance concern but worth noting for consistency.
**Suggestion:** Use loguru's lazy formatting: `logger.info("WebSocket server started on ws://{}:{}", config.ws_host, config.ws_port)`.

### R02-08 [info] Tests test logic predicates rather than actual bot methods
**File:** tests/test_auth.py, tests/test_routing.py, tests/test_commands.py
**Description:** Most tests replicate the routing/auth logic inline (e.g., `mapping.get(str(channel_id))`) rather than calling the actual `get_agent_for_channel()` or `interaction_check()` methods. This means the tests verify the test's own implementation, not the production code. If production logic drifts, tests will still pass.
**Suggestion:** In a future phase, add integration tests that instantiate `TerminalBot` or `GeneralCog` with mocked Discord objects and call the actual methods. The current approach is acceptable for phase 02 but should not be the final test layer.

### R02-09 [info] config.json ships with empty allowlists -- bot accepts no commands until configured
**File:** config.json:7-8
**Description:** Both `allowed_guild_ids` and `allowed_user_ids` are empty arrays. The bot will start successfully but silently reject all slash commands. This is technically secure (deny-by-default) but may confuse first-time setup.
**Suggestion:** Add a startup log warning when allowlists are empty: `logger.warning("No allowed guilds/users configured -- all commands will be rejected")`.

### R02-10 [info] Duplicate auth check: guild allowlist checked in both global tree check and cog interaction_check
**File:** bot/discord_bot.py:48-55, bot/cogs/general.py:33-34
**Description:** The guild allowlist is checked twice for every interaction: once in the global `tree.interaction_check` and again in `GeneralCog.interaction_check`. This is documented as intentional defense-in-depth, but it adds a (very small) overhead and could cause confusion if the two checks diverge after a config reload race.
**Suggestion:** No action required -- the dual-check is a reasonable defense-in-depth pattern. Documenting it (as already done) is sufficient.
