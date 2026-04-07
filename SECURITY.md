# SECURITY.md — Phase 02: Discord Bot Message Routing

**ASVS Level:** 1
**Audit Date:** 2026-04-08
**Phase:** 02 — discord-bot-message-routing (Plans 01, 02, 03)
**Result:** SECURED — 11/11 threats closed

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-02-01 | Information Disclosure | mitigate | CLOSED | bot/config.py:139 — `load_dotenv(dotenv_path="bot/.env")`; config.py:145-149 raises ValueError if token absent; .gitignore line 2 covers `bot/.env`; bot/.env.example present; bot/.env not git-tracked |
| T-02-02 | Elevation of Privilege | mitigate | CLOSED | bot/discord_bot.py:48-55 — `@self.tree.interaction_check` rejects unauthorized guild_ids at runtime (layer 2); discord_bot.py:58-65 — setup_hook syncs only to allowed guilds (layer 1); bot/cogs/general.py:24-43 — cog interaction_check as backup (layer 3) |
| T-02-03 | Spoofing | accept | CLOSED | See accepted risks log below |
| T-02-04 | Tampering | accept | CLOSED | See accepted risks log below |
| T-02-05 | Elevation of Privilege | mitigate | CLOSED | bot/cogs/general.py:24-43 — `interaction_check` checks `allowed_user_ids` (AUTH-01) as PRIMARY gate; general.py:16 — `default_permissions(administrator=True)` annotated "UI HIDING ONLY" with explicit code comment; general.py:25 docstring: "PRIMARY security gate" |
| T-02-06 | Spoofing | accept | CLOSED | See accepted risks log below |
| T-02-07 | Denial of Service | mitigate | CLOSED | bot/cogs/general.py:136-157 — `/reload` guarded by interaction_check (allowed_user_ids); calls `await self.bot.bot_config.reload_config()` which uses `async with self._config_lock` (bot/config.py:99) |
| T-02-08 | Tampering | mitigate | CLOSED | bot/config.py:73,99 — both `save_config` and `reload_config` use `async with self._config_lock`; bot/discord_bot.py:126-129 — duplicate channel name check prevents channel spam via `discord.utils.get(guild.text_channels, name=channel_name)` before creation |
| T-02-09 | Information Disclosure | accept | CLOSED | See accepted risks log below |
| T-02-10 | N/A (tests) | accept | CLOSED | See accepted risks log below |
| T-02-11 | Denial of Service | mitigate | CLOSED | bot/server.py:105-109 — `on_agent_connect` callback wrapped in try/except; server.py:134-138 — `on_agent_disconnect` callback wrapped in try/except via asyncio.create_task with outer try/except; discord_bot.py:93-97 and 180-183 — channel.send() wrapped in try/except in both connect and disconnect notification paths |
| T-02-12 | Denial of Service | mitigate | CLOSED | bot/discord_bot.py:126-143 — duplicate channel check: `existing = discord.utils.get(guild.text_channels, name=channel_name)` maps to existing channel instead of creating new one, preventing channel spam from reconnecting agents |

---

## Accepted Risks Log

| Threat ID | Category | Rationale |
|-----------|----------|-----------|
| T-02-03 | Spoofing — Discord interactions | Discord API guarantees `user.id` and `guild_id` authenticity via bot token authentication. The bot token is the trust anchor; no additional verification of Discord-issued payloads is needed or practical. |
| T-02-04 | Tampering — config.json | config.json resides on the bot operator's local machine. No remote write path exists. asyncio.Lock (config.py:64,73,99) prevents corruption from concurrent in-process save/reload. Risk is accepted as a local file security boundary. |
| T-02-06 | Spoofing — interaction.user.id | Discord guarantees user identity via OAuth token. We trust Discord's `user.id` value the same way a server trusts a session token issued by an OAuth provider. No additional layer is warranted at ASVS Level 1. |
| T-02-09 | Information Disclosure — /status agent info | `/status` output (agent name, platform string) is only visible to users who pass both guild and user allowlist checks (interaction_check). Agent name and platform are not sensitive secrets; they are operational identifiers. |
| T-02-10 | N/A — tests/ | Plan 03 is test-only. Test files add no production attack surface. Tests validate security controls (AUTH-01, AUTH-04, config lock, callback isolation). |

---

## Unregistered Threat Flags

None. All three SUMMARY files (`02-01-SUMMARY.md`, `02-02-SUMMARY.md`, `02-03-SUMMARY.md`) report `## Threat Flags: None` — no new attack surface was detected by the executor during implementation.

---

## Notes

- `default_permissions(administrator=True)` in `bot/cogs/general.py` is explicitly documented in code as "UI HIDING ONLY" and is NOT treated as an authorization control. The authoritative gate is `interaction_check`.
- The `_config_lock` in `BotConfig` is shared by both `save_config` and `reload_config`, preventing the race condition where auto-channel creation writes config while `/reload` reads it.
- `bot/.env` is excluded from git via `.gitignore` line matching `.env`; confirmed not tracked (`git ls-files bot/.env` returns empty).
