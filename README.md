# Keystead

**Your agency does the work. Your keys stay with you.**

Keystead ("where the keys stay") lets an agency's AI agent make changes on a client's accounts while the client's credentials stay on the client's side. Nothing changes until the client types `approve` in the shared chat. It runs on [Switch](https://github.com/sandbox-quantum/switch): the agency's agent and the client's key-holder sit in one Switch room.

```text
        AGENCY SIDE                     SWITCH ROOM (private)                    CLIENT SIDE
 ┌──────────────────────┐      ┌───────────────────────────────────┐     ┌──────────────────────────┐
 │ DJ (person)          │ (1)  │ "@clientsite-agency verify ..."   │     │ client (person)          │
 │ @clientsite-agency   │─────▶│ (2) @keystead propose {json}      │────▶│ @keystead gate (no LLM)  │
 │ Claude Code / Codex  │      │ (3) KS-0001 card ◀────────────────│─────│  policy.py  default deny │
 │ holds NO client keys │      │ (4) "approve KS-0001"  ◀── client │     │  vault.py   AES-256-GCM  │
 │                      │◀─────│ (6) receipt, Ledger #14 · a91c3e  │◀────│  audit.jsonl hash chain  │
 └──────────────────────┘      └───────────────────────────────────┘     └────────────┬─────────────┘
                                                                          (5) one API call│ token never
                                                                                          ▼ leaves here
                                                                          Cloudflare DNS / octoDNS / Postiz
```

1. DJ asks the agency's agent for a change. 2. The agent posts a structured proposal to `@keystead`. 3. The gate checks policy and posts a card with an id and an expiry. 4. Only the client's typed `approve KS-0001` counts. 5. The gate runs one allowlisted action with a token only it can decrypt. 6. It posts a receipt with its ledger line.

## The problem

Clients send agencies their GoDaddy, Cloudflare, Instagram and hosting logins over WhatsApp. The agency gets full, permanent access, nobody rotates the passwords when the work ends, and nobody can tell who changed what. Keystead replaces "send me your password" with "approve KS-0007".

**The side that holds the keys has no LLM.** `@keystead` is a plain program: it parses a JSON block, matches rules, waits for a typed approval from a named person, then runs one action. A prompt injection has nothing to talk to, and an agent cannot approve its own request.

## 10-minute setup

You need [uv](https://docs.astral.sh/uv/), a Switch server with a messaging app, and (for the demo) a Cloudflare zone.

**1. Switch.** Install [Switch Console](https://docs.switchagents.ai/switch-rooms/getting-started) and let it run a local server with the bundled Mattermost. Create two Mattermost people: `dj` (agency) and `client`. Check the bridge URL: `curl -i $SWITCH_URL/health` must return 200 (401 means right host, wrong path).

**2. Keystead, on the client's machine** (run it as a separate OS user or in Docker, so no coding agent on that machine can read `data/` or `.env`):

```bash
git clone <this repo> keystead && cd keystead
uv sync
uv run keystead init                      # writes config/keystead.yaml and KEYSTEAD_MASTER_KEY into .env
$EDITOR config/keystead.yaml              # room name, approvers, proposers, zones, rules
$EDITOR .env                              # SWITCH_URL and KEYSTEAD_REG_TOKEN (the client's registration token)
uv run keystead secret set cloudflare_token   # hidden prompt; token scope: Zone > DNS > Edit, one zone
uv run keystead register                  # saves {id, api_key} to data/agent.json; Switch shows the key once
```

**3. In Switch Console, as the client:** set `@keystead`'s addressing to **anyone**. The gate makes its own decisions about who may do what. With the default owner-only addressing, Switch answers everyone except the client with its own "I only take instructions from my owner" message.

**4. The room.** In Switch Console choose *Create from template* and load `templates/keystead-room.template.yaml`. Fill `client` (e.g. `clientsite`), `client_user` (the client's Mattermost user) and `gate_agent` (`keystead`). This creates `@clientsite-agency` (Claude Code, Codex or OpenCode, with `agents/agency/CLAUDE.md` as its instructions) and the private room `keystead-clientsite` with DJ, the client and both agents. The client owns `@keystead`, so if the server won't let the deployer add it, the client adds `@keystead` to the room from Switch Console.

**5. Run the gate:**

```bash
uv run keystead run            # or: ./scripts/demo.sh  (steps 2 and 5 in one go)
                               # or: docker compose up -d keystead-gate
```

The gate posts `keystead online` in the room. The kickoff message has the agency agent send `@keystead help` and keep the action catalog.

### Commands

| Command | What it does |
| --- | --- |
| `keystead init` | Writes `config/keystead.yaml` and a new master key |
| `keystead secret set <name>` | Stores a secret with a hidden prompt (or from stdin). `secret list` shows names only |
| `keystead register` | Registers the gate as a custom, always-on Switch agent owned by the client |
| `keystead run` | Runs the gate |
| `keystead status` | Pending and recent proposals, pause and revoke state, ledger check |
| `keystead revoke` | Empties the proposer list, cancels pending proposals, logs it. `--undo` restores |
| `keystead audit verify` | Recomputes the hash chain and names the first broken line. `audit show` prints it |
| `keystead identities` | Which Switch sender id each person and agent is pinned to. `--reset` forgets them |

In the room, the client (approvers only) can also type `keystead status`, `keystead audit`, `keystead pause`, `keystead resume` and `keystead revoke`.

### In the room

````text
DJ:        @clientsite-agency verify clientsite.com for Search Console, value google-site-verification=abc123
agency:    I'll propose a TXT record on @ with the verification value.
           @keystead propose
           ```keystead
           {"action": "dns.add_record",
            "params": {"zone": "clientsite.com", "type": "TXT", "name": "@",
                       "content": "google-site-verification=abc123", "ttl": 1},
            "reason": "Verify clientsite.com in Google Search Console"}
           ```
keystead:  @client KS-0001 · dns.add_record on clientsite.com
           TXT  @  "google-site-verification=abc123"  TTL auto
           Asked by clientsite-agency for: Verify clientsite.com in Google Search Console
           Reply "approve KS-0001" or "deny KS-0001". Expires 22:57.
DJ:        approve KS-0001
keystead:  Only the client can approve KS-0001.
client:    approve KS-0001
keystead:  @clientsite-agency KS-0001 done. TXT @ is live, record id 9f2c…. Approved by client at 22:41. Ledger #14 · a91c3e
````

## How Switch is used

- **One room, two owners.** The agency owns `@clientsite-agency` (created from a Switch room template). The client owns `@keystead`, because the client registers it with their own registration token. Both sit in one private room bridged to Mattermost; Slack or Teams work the same way.
- **A custom agent on the agent protocol.** The gate is built on Switch's scripted-agent harness (`core/tests/e2e/follow_the_conversation/harness.py`): `POST /agents` with `connector_type: custom` and `connection_model: always_on`, then `GET /agents/{id}/events?scope=all&filter=all` (SSE), a heartbeat every 2 s (a 404 or 409 reopens the stream with the same connection id and `Last-Event-ID`), and `connect_to_room`, `list_participants`, `post_message` and `send_targeted_message` operations. `filter=all` matters: `approve KS-0001` is not addressed to the gate, and it still has to see it.
- **Identity.** Switch's participant ids (`list_participants`) and message sender ids (`@switch-…:server`) are different id spaces, and Switch says to treat ids as opaque. The gate checks at start that every approver is a person in the room (never an agent, never ambiguous) and that no name is both proposer and approver. It then pins each sender id to its participant name the first time that name speaks, stores the pin, and refuses any later message that uses a pinned name from a different id. For a strict setup, list the ids under `people.pins` in the config (`keystead identities` prints them).
- **Templates.** `templates/keystead-room.template.yaml` creates the agency agent, the room and the kickoff. It passes Switch's own `template_lint` with no errors or warnings.

**Trap to avoid:** Switch's in-chat permission prompt (allow once / for this session / reject) is not Keystead's approval. It lives in the agent's runtime, and Switch lets calls to an agent's registered MCP tools through without asking. The client's typed `approve KS-NNNN`, checked by the gate, is the only approval.

## Policy

Rules live in `config/keystead.yaml`. The first matching rule wins, and **the default is deny**.

```yaml
rules:
  - action: dns.list_records        # read-only: runs at once
    effect: allow
  - action: dns.add_record
    when:
      zone: {in: [clientsite.com]}
      type: {in: [TXT, CNAME]}      # also: equals, matches (full-match regex), ends_with
    effect: approve
    limit_per_day: 10
  - action: "*"
    effect: deny
```

Every condition in a rule must hold. A condition on a param the proposal leaves out resolves fail-closed: an `allow` rule does not match it, and an `approve` or `deny` rule does. `@keystead help` lists only actions some rule allows or sends for approval.

### Connectors

| Connector | Actions | Notes |
| --- | --- | --- |
| `cloudflare_dns` | `dns.add_record`, `dns.delete_record`, `dns.list_records` | `cloudflare` SDK. Token scope: Zone > DNS > Edit on the listed zones only |
| `octodns_dns` | the same three | Any [octoDNS](https://github.com/octodns/octodns) provider (Route 53, NS1, DigitalOcean, …). `uv sync --extra octodns` plus the provider package. `record_id` is `TYPE:name` |
| `postiz_social` | `social.publish_post` | Calls a separately running [Postiz](https://github.com/gitroomhq/postiz-app) over HTTP (`docker compose --profile social up`). Postiz is AGPL-3.0, so it stays its own service |

## Security model

Three guarantees: credentials never enter an LLM's context, nothing runs without a matching rule, and every approval comes from a named person and is bound to one exact change.

| Threat | What stops it |
| --- | --- |
| Prompt injection talks the key-holder into acting | The gate has no LLM. It only parses a JSON block and matches rules |
| The agency agent is tricked into proposing a bad change | Default-deny policy, unknown params rejected, and the client sees the exact change in the card before approving |
| An agent types `approve KS-0007` | Only pinned approver ids count. Agents are never approvers, and the gate refuses to start if one is configured as one |
| Someone else uses the client's display name | Sender ids are pinned per name; a different id with a pinned name is refused and logged |
| The change is swapped after approval | Proposals are immutable (SQLite trigger). Approval is bound to `payload_hash`, re-checked before execution |
| An old approval is replayed | Each id is approved once (atomic compare-and-set) and expires after 30 minutes |
| A secret leaks | Encrypted vault, separate OS user or container, secrets read only inside `execute()`, redaction of every stored secret on every outgoing message and stored result |
| A message posted by Switch "on behalf of" someone counts as approval | Approvals with `sender_kind: platform` or `on_behalf_of` set are rejected |
| The ledger is edited | Hash chain. `keystead audit verify` names the first broken line |
| Approval fatigue | `allow` rules for read-only actions, `limit_per_day` on the rest |
| The token is too powerful | Cloudflare token scoped to DNS Edit on one zone. One connector, one secret, plus a zone allowlist in config |
| The gate is down | Nothing runs. Proposals wait and expire, and the agency gets no receipt |

**Out of scope:** whoever runs the Switch server or the messaging app can impersonate users. Approval is only as strong as the client's Mattermost or Slack sign-in. Switch's own [shared responsibility](https://docs.switchagents.ai/switch-rooms/resources/shared-responsibility.md) page draws the same line.

## Data

All state lives in `data/` on the client's side: `agent.json` (gate id, API key, connection id), `vault.json` (AES-256-GCM, a fresh 12-byte nonce per value, master key in `KEYSTEAD_MASTER_KEY`), `keystead.db` (SQLite: proposals, identities, pause and revoke state) and `audit.jsonl` (`hash = sha256(prev_hash + canonical_json(line without hash))`).

## Tests

```bash
uv run pytest            # 48 tests: proposals, policy, approvals, vault, audit, connectors,
                         # and a full propose -> forged approvals -> approve -> execute flow
                         # over a fake Switch server
```

### Run the live check

`scripts/live_e2e.py` plays the demo against a real switch-core and Mattermost. ```bash
uv run python scripts/live_e2e.py
```

It checks: online, help, card, DJ's and the agent's forged approvals refused, the client's approval executing once (with a fake Cloudflare token, so the receipt is a redacted failure), revoke, `audit verify`, and no secret in chat, logs, database or ledger.

## License

Keystead is open-source software licensed under the [Apache-2.0](LICENSE) License. Built completely end to end.
