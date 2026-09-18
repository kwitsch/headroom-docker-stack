# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## mitmproxy service

`redirect_headroom.py` is an explicit HTTP(S) proxy addon on `:8080`. Only `--allow-hosts` domains
are TLS-intercepted (Anthropic/OpenAI/Gemini API hosts); everything else is a plain TCP tunnel.

The addon redirects exactly `POST /v1/messages` (`/v1/chat/completions`, Gemini `generateContent`)
to `headroom:8787`, rewriting the connection target but preserving the original `Host` header.
Routed requests are buffered; passthrough traffic and all `text/event-stream` responses **must**
stream — buffering SSE breaks Claude Code's Remote Control channel.

Each provider route is independently toggleable via `MITM_ROUTE_HEADROOM` / `MITM_ROUTE_OPENAI` /
`MITM_ROUTE_GEMINI` env vars, no file change needed.
