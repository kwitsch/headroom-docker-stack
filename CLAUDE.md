# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

This repository is maintained in English. All text must be written in English, including:

- Commit messages
- Pull requests (titles and descriptions)
- Documentation
- Code comments
- Variable, function, and identifier names

## What this is

A Docker Compose stack (`ts-headroom-stack`) that exposes a Headroom AI proxy (for Claude Code /
Anthropic / OpenAI / Gemini API traffic) on a private Tailscale tailnet, with mitmproxy doing the
TLS interception/routing and nginx serving a dashboard + CA download page. There is no application
source to build — this repo is entirely Docker Compose config, one nginx config, one Python
mitmproxy addon, and env templates.

## Commands

```bash
cp .env.example .env                     # fill in TS_AUTHKEY, then...
cp headroom/headroom.env.example headroom/headroom.env   # copy the Headroom config template
docker compose up -d                     # start the stack
docker compose config                    # validate/render the compose file (closest thing to a lint)
docker compose logs -f <service>         # tail logs: tailscale | headroom | mitmproxy | webserver | autoheal
docker compose restart webserver         # required after the mitmproxy CA rotates
docker compose down                      # stop the stack
```

There is no build step, linter, or test suite in this repo. Verify changes by bringing the stack
up and exercising the real endpoints (see "Endpoints" below) or `docker exec headroom headroom
output-savings` for the output-shaper.

## Architecture

Four services share Tailscale's network namespace (`network_mode: service:tailscale`), so from the
tailnet's point of view they all live behind one IP/MagicDNS name; `headroom` sits on a separate
internal-only `backend` network and is reachable only through the other two:

```text
Tailnet client (Claude Code, HTTPS_PROXY + mitm CA)
        │  (Tailscale IP / MagicDNS)
        ▼
┌───────────────────────── netns: tailscale ─────────────────────────┐
│  tailscale (gateway)                                               │
│  mitmproxy   :8080  ── addon: api.anthropic.com → headroom:8787    │
│  webserver   :80    ── /dashboard,/stats* → headroom · /ca/ → CA   │
└──────────────────────────────┬─────────────────────────────────────┘
                       backend (internal)
                               │
                          headroom :8787 ── egress ──► api.anthropic.com
```

- **tailscale** — the only network entry point; `mitmproxy` and `webserver` are attached via
  `network_mode: service:tailscale`, not their own networks. `TS_ACCEPT_DNS=false` is required or
  Docker's embedded DNS (container name resolution) breaks.
- **mitmproxy** — explicit HTTP(S) proxy on `:8080`, routes select LLM API requests to `headroom`.
  See `mitmproxy/CLAUDE.md`.
- **headroom** — the proxy/compression engine, reachable only via `mitmproxy`/`webserver` on the
  `backend` network. See `headroom/CLAUDE.md`.
- **webserver** — nginx dashboard reverse proxy + CA download. See `webserver/CLAUDE.md`.
- **autoheal** — restarts any container labeled `autoheal=true` that Docker reports unhealthy
  (Docker doesn't do this on its own); currently only `headroom` carries that label. Needs
  `docker.sock` access.

State lives in three named volumes: `ts-state` (Tailscale node identity), `headroom-data`
(`/data` — savings history, TOIN models, TTL learning; must persist across restarts), and
`mitm-certs` (mitmproxy's root CA, mounted read-only into `webserver`).

Startup ordering matters and is enforced via `depends_on: condition: service_healthy` +
`restart: true`: `mitmproxy`/`webserver` wait for `tailscale`'s healthcheck, and both also wait
for `headroom`. This exists specifically to survive reboots (see README's "Boot robustness"
section) — don't remove the healthchecks or `start_period` values without understanding why they're
there.
