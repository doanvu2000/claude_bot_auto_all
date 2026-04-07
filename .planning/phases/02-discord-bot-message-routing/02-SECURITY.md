---
phase: 02
slug: discord-bot-message-routing
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-08
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Discord API → Bot | Bot token authenticates; interaction payloads from Discord | Slash command payloads, user/guild IDs |
| User → Bot (via Discord) | User IDs in interactions checked against allowlist | User identity, command intent |
| config.json → Bot | Local file, trusted but validates structure | Guild IDs, user IDs, channel mapping |
| bot/.env → Bot | Contains Discord token secret | DISCORD_BOT_TOKEN |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Information Disclosure | bot/.env | mitigate | Token loaded from bot/.env; .gitignore covers bot/.env; .env.example has placeholder only | closed |
| T-02-02 | Elevation of Privilege | BotConfig.allowed_guild_ids | mitigate | Three-layer defense: setup_hook syncs to allowed guilds only; global_interaction_check rejects unauthorized guilds at runtime (authoritative); cog interaction_check as backup | closed |
| T-02-03 | Spoofing | Discord interactions | accept | Discord API guarantees user.id and guild_id via bot token auth | closed |
| T-02-04 | Tampering | config.json | accept | Local file; asyncio.Lock prevents concurrent save/reload corruption | closed |
| T-02-05 | Elevation of Privilege | cog interaction_check | mitigate | interaction_check is PRIMARY gate checking allowed_user_ids; default_permissions is UI hiding only (documented in code) | closed |
| T-02-06 | Spoofing | interaction.user.id | accept | Discord guarantees user identity via OAuth | closed |
| T-02-07 | Denial of Service | /reload command | mitigate | /reload gated by interaction_check; uses async _config_lock to prevent concurrent corruption | closed |
| T-02-08 | Tampering | auto-channel config write | mitigate | asyncio.Lock on save/reload; duplicate channel name check prevents channel spam | closed |
| T-02-09 | Information Disclosure | /status agent info | accept | Visible only to users passing guild + user allowlist; agent name/platform not sensitive | closed |
| T-02-10 | N/A | tests/ | accept | Test-only plan; no production attack surface | closed |
| T-02-11 | Denial of Service | AgentManager callbacks | mitigate | Connect/disconnect callbacks wrapped in try/except in server.py; channel.send() wrapped in try/except in discord_bot.py | closed |
| T-02-12 | Denial of Service | auto-channel creation | mitigate | discord.utils.get name check before create_text_channel prevents duplicate channels from reconnecting agents | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-03 | Discord API is trusted OAuth provider; no additional spoofing defense needed at bot level | operator | 2026-04-08 |
| AR-02-02 | T-02-04 | config.json is on bot operator's local machine; no remote write surface | operator | 2026-04-08 |
| AR-02-03 | T-02-06 | Discord user identity delegated to Discord OAuth | operator | 2026-04-08 |
| AR-02-04 | T-02-09 | /status data (agent name, platform) is operational metadata, not sensitive | operator | 2026-04-08 |
| AR-02-05 | T-02-10 | Test code introduces no production attack surface | operator | 2026-04-08 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-08 | 11 | 11 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-08
