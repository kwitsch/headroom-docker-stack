# ts-headroom-stack

Docker Compose stack: Tailscale gateway + Headroom AI proxy behind mitmproxy + dashboard/CA webserver.

## Architecture

```
Tailnet client (Claude Code, HTTPS_PROXY + mitm CA)
        │
        ▼  (Tailscale IP / MagicDNS)
┌───────────────────────── netns: tailscale ─────────────────────────┐
│  tailscale (gateway)                                               │
│  mitmproxy   :8080  ── addon: api.anthropic.com → headroom:8787    │
│  webserver   :80    ── /dashboard,/stats* → headroom · /ca/ → CA   │
└──────────────────────────────┬─────────────────────────────────────┘
                       backend (internal)
                               │
                          headroom :8787 ── egress ──► api.anthropic.com
```

| Service   | Reachability                                                                                        |
| --------- | --------------------------------------------------------------------------------------------------- |
| tailscale | Gateway; mitmproxy + webserver share its netns                                                      |
| mitmproxy | Tailnet, port `8080` (explicit HTTP(S) proxy)                                                       |
| webserver | Tailnet, port `80` (dashboard reverse proxy, CA download)                                           |
| headroom  | **only** on the `backend` network; the API path is exclusively reachable via the mitmproxy redirect |

Isolation:

- `backend` is `internal: true` → no published ports, no egress.
- Headroom additionally has `egress`, only for the upstream (`api.anthropic.com`).
- nginx deliberately does **not** proxy `/v1/*` — only dashboard/stats/health.

## Structure

```
.
├── docker-compose.yml
├── .env.example
├── headroom/
│   └── headroom.env.example         # Cache mode, model router, TOIN (team-plan-optimized)
├── mitmproxy/redirect_headroom.py  # Path routing: only POST /v1/messages → Headroom
└── webserver/
    ├── nginx.conf
    └── html/index.html
```

## Persistence (named volumes)

| Volume          | Container                              | Content                                    |
| --------------- | -------------------------------------- | ------------------------------------------ |
| `ts-state`      | tailscale `/var/lib/tailscale`         | Node state, keys                           |
| `headroom-data` | headroom `/data`                       | Savings history, TOIN models, TTL learning |
| `mitm-certs`    | mitmproxy `~/.mitmproxy` · nginx `:ro` | Root CA & keys                             |

Docker-managed — no host preparation or chown needed.
Backup e.g. via `docker run --rm -v ts-headroom-stack_mitm-certs:/v -v $PWD:/b alpine tar czf /b/mitm-certs.tgz -C /v .`

## Multi-provider (Anthropic, OpenAI, Gemini)

The addon routes three providers to Headroom (the original host stays in
the Host header, Headroom picks the upstream):

| Provider  | Host                              | Path                                                             | Headroom support                                           |
| --------- | --------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------- |
| Anthropic | api.anthropic.com                 | `POST /v1/messages`                                              | documented                                                 |
| OpenAI    | api.openai.com                    | `POST /v1/chat/completions`                                      | documented (`OPENAI_TARGET_API_URL` for a custom upstream) |
| Gemini    | generativelanguage.googleapis.com | `POST /v1{beta}/models/*:generateContent\|streamGenerateContent` | **not documented** -> check the first request              |

Disable without a file change (env on the mitmproxy service):
`MITM_ROUTE_OPENAI=0`, `MITM_ROUTE_GEMINI=0`, `MITM_ROUTE_HEADROOM=0` (all).
Paths of the three hosts that are not routed (e.g. `count_tokens`, `/v1/embeddings`,
`/v1/responses`, Gemini `:countTokens`) pass through unchanged to the provider.
Clients need the mitm root CA for all three hosts.

## Remote Control & streaming (important)

The mitmproxy addon MUST stream (`request.stream`/`response.stream = True` for
every flow). Otherwise mitmproxy buffers whole bodies -> Claude Code's
Remote Control SSE channel on api.anthropic.com stalls and breaks. Only exactly
`POST /v1/messages` is redirected to Headroom; everything else (including
`count_tokens`, Remote Control traffic) streams through unchanged.

## MITM scope

- `--allow-hosts '^api\.anthropic\.com:443$'` → only this domain is intercepted; OAuth (`platform.claude.com`), MCP proxy, downloads etc. remain a plain TCP tunnel without CA trust.
- The addon routes exclusively `POST /v1/messages` to Headroom — WebFetch safety check, feature flags and telemetry on `api.anthropic.com` go to Anthropic unchanged.

## Headroom image

Variant: `ghcr.io/headroomlabs-ai/headroom:code-nonroot`
(extras `proxy,code` → tree-sitter CodeCompressor; non-root; Debian-slim base).

- **Pinning:** Versioned tags only exist for the base variant; for
  `code-nonroot`, pin by digest:
  `docker pull ghcr.io/headroomlabs-ai/headroom:code-nonroot`
  → take the digest from `docker inspect --format '{{index .RepoDigests 0}}' ...`
  and put it into Compose (`image: ...@sha256:...`).
- **Volume ownership (non-root):** If `/data` is not writable on first start
  (root-owned volume), determine the image user's uid and
  chown the volume once:
  ```bash
  UID=$(docker inspect --format '{{.Config.User}}' ghcr.io/headroomlabs-ai/headroom:code-nonroot)
  docker run --rm -v ts-headroom-stack_headroom-data:/data alpine chown -R "$UID" /data
  ```
- **Not included:** the `memory`/`relevance` extras — the planned
  memory A/B test (bge-small embedder) would need a separate image again.

## Boot robustness (fix for the 04:30 reboot race)

After nightly reboots, Headroom stayed persistently unhealthy (it started before
the Tailscale gateway, and the `http_client` check never recovered). Countermeasures:

1. **Tailscale healthcheck** (`tailscale status`) + `depends_on:
condition: service_healthy` with `restart: true` on headroom, mitmproxy
   and webserver -> enforces start order; on a Tailscale restart
   the netns sharers restart with it (requires Docker Compose >= 2.17).
2. **autoheal watchdog**: restarts containers labeled `autoheal=true`
   that are persistently unhealthy (Docker does not do this itself).
   Trade-off: docker.sock access (root-equivalent), `network_mode: none`.
3. **`start_period: 120s`** on the Headroom healthcheck: the boot phase does
   not count as a failure.

On the systemd side (installer, not this repo): `After=network-online.target`

- `docker compose up -d --wait` in the stack unit.

## Known gotcha: 403 Forbidden

nginx workers run unprivileged. Two causes previously led to 403:

1. Restrictive host permissions on the bind mounts (e.g. `chmod -R go-rwx`
   in the deploy directory) — workers couldn't read `webserver/html/`.
2. The `mitm-certs` volume with 0700 permissions owned by the mitmproxy user — workers couldn't
   enter the CA directory.

Fix in Compose: on startup, the webserver copies html + CA into the
docroot as root and sets `a+rX` (waits in a loop until mitmproxy has generated
the CA, max. 3 min). If the CA is rotated, restart the webserver
(`docker compose restart webserver`).

## Setup

```bash
cp .env.example .env # fill in TS_AUTHKEY
docker compose up -d
```

## Client configuration (Claude Code)

```bash
export HTTPS_PROXY=http:// < ts-hostname > :8080
# Load the root CA: http://<ts-hostname>/ca/mitmproxy-ca-cert.pem
export NODE_EXTRA_CA_CERTS=/path/to/mitmproxy-ca-cert.pem
claude
```

Requests to `api.anthropic.com` go through mitmproxy → Headroom (compression) → Anthropic.

## Endpoints (tailnet)

| URL                              | Function                   |
| -------------------------------- | -------------------------- |
| `http://<ts-hostname>/`          | Landing page               |
| `http://<ts-hostname>/dashboard` | Headroom dashboard         |
| `http://<ts-hostname>/stats`     | Live stats (JSON)          |
| `http://<ts-hostname>/ca/`       | mitmproxy root CA download |
| `http://<ts-hostname>:8080`      | HTTP(S) proxy (mitmproxy)  |
