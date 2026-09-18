# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

## webserver service

nginx (`nginx.conf` + `html/`) reverse-proxies only `/dashboard`, `/stats*`, `/metrics`, `/health`,
`/livez`, `/readyz` to `headroom:8787` (never `/v1/*`), and serves the mitmproxy root CA under
`/ca/`.

On container start it copies `html/` + the CA cert into the docroot as root and `chmod a+rX`s them,
working around restrictive bind-mount/volume permissions that otherwise cause 403s for the
unprivileged nginx worker.
