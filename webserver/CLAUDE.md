# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## webserver service

nginx (`nginx.conf` + `html/`) reverse-proxies only `/dashboard`, `/stats*`, `/metrics`, `/health`,
`/livez`, `/readyz` to `headroom:8787` (never `/v1/*`), and serves the mitmproxy root CA under
`/ca/`.

`nginx.conf` and `html/` are baked into the image (`webserver/Dockerfile`), root-owned and
world-readable, so the old html-copy + `chmod` workaround (and its 403 bind-mount-permission
vector) is gone. Only the CA copy stays a runtime step in the compose `command:`: the `mitm-certs`
volume is populated by mitmproxy at run time and cannot be baked. If the CA is rotated, restart the
webserver (`docker compose restart webserver`).
