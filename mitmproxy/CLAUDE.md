# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## mitmproxy service

`redirect_headroom.py` is an explicit HTTP(S) proxy addon on `:8080`. Only `--allow-hosts` domains
are TLS-intercepted (Anthropic/OpenAI/Gemini API hosts); everything else is a plain TCP tunnel.

The addon redirects exactly `POST /v1/messages` (`/v1/chat/completions`, Gemini `generateContent`)
to `headroom:8787`, rewriting the connection target but preserving the original `Host` header.
Routed requests are buffered; passthrough traffic and all `text/event-stream` responses **must**
stream — buffering SSE breaks Claude Code's Remote Control channel.

The addon is baked into the image (`mitmproxy/Dockerfile`, `COPY redirect_headroom.py
/addons/redirect_headroom.py`); editing routing logic requires a `VERSION` bump + CI rebuild. Each
provider route stays runtime-toggleable via the `MITM_ROUTE_HEADROOM` / `MITM_ROUTE_OPENAI` /
`MITM_ROUTE_GEMINI` env vars (compose `environment:`, defaulting to `1`), no rebuild needed.
