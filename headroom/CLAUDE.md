# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## headroom service

`headroom` is the actual proxy/compression engine (external image
`ghcr.io/headroomlabs-ai/headroom:code-nonroot`). Not reachable directly from the tailnet; only
`mitmproxy` (API path) and `webserver` (dashboard, read-only) can reach it, via the `backend`
network.

All of its behavior (cache mode, model routing, rate limiting, output shaping) is baked into the
image as `ENV` lines in `headroom/Dockerfile`, each preceded by the reasoning behind the setting —
read those comments before changing anything. Retuning a setting requires a `VERSION` bump + CI
rebuild (and a matching `image:` tag bump in `docker-compose.yml`), not a live edit.
