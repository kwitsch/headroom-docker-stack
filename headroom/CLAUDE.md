# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## headroom service

`headroom` is the actual proxy/compression engine (external image
`ghcr.io/headroomlabs-ai/headroom:code-nonroot`). Not reachable directly from the tailnet; only
`mitmproxy` (API path) and `webserver` (dashboard, read-only) can reach it, via the `backend`
network.

All of its behavior (cache mode, model routing, rate limiting, output shaping) is configured
through `headroom.env` (copied from `headroom.env.example`), which is heavily commented with the
reasoning behind each setting — read it before changing anything there.
