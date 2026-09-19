# syntax=docker/dockerfile:1
# Headroom AI proxy — self-contained image.
# Base: official code-nonroot variant (extras proxy,code -> tree-sitter
# CodeCompressor; non-root user; Debian-slim base so shell/Python work for
# the compose healthcheck). Pinned by digest per the repo's production
# convention (resolve with:
#   docker inspect --format '{{index .RepoDigests 0}}' \
#     ghcr.io/headroomlabs-ai/headroom:code-nonroot ).
# No RUN/USER/chown: layering only ENV preserves the base user and /data
# ownership behavior.
FROM ghcr.io/headroomlabs-ai/headroom:code-nonroot@sha256:3775bff649bae45180f0c011fe4dfcc0d0a4329e72fd74ebfb9ddf9ab97d3225

# =============================================================================
# Headroom configuration (baked; retuning needs a VERSION bump + CI rebuild).
# Scenario: 1 user, Claude Code, Anthropic team plan (subscription).
# Strategy: maximize prefix-cache stability, compress only in the live zone;
#           recompact cold turns instead of resending them.
# =============================================================================

# --- Network (container) ---
ENV HEADROOM_HOST=0.0.0.0
# HEADROOM_PORT stays coupled to the compose healthcheck URL (:8787/readyz).
ENV HEADROOM_PORT=8787

# --- Core: cache mode instead of token mode ---
# Claude Code lives on the Anthropic prompt cache; "cache" freezes old turns
# and compresses only new content -> no cache bust from rewritten prefixes.
ENV HEADROOM_MODE=cache

# Forward original request bytes unchanged while no transform changes the
# body -> the Anthropic cache key stays stable.
ENV HEADROOM_PROXY_PYTHON_FORWARDER_MODE=byte_faithful

# Union the anthropic-beta header per session (Claude Code drops beta tokens
# between turns; without sticky union -> cache miss mid-session).
ENV HEADROOM_BETA_HEADER_STICKY=enabled

# Strip internal x-headroom-* headers before upstream (default, pinned).
ENV HEADROOM_STRIP_INTERNAL_HEADERS=enabled

# --- Cold-prefix optimization ---
# On a cold provider cache, recompact the prefix instead of resending it 1:1;
# TTL observation sharpens cold detection.
ENV HEADROOM_COLD_RECOMPACT=1
ENV HEADROOM_DEDUPE=1
ENV HEADROOM_CACHE_TTL_LEARN=1

# Reasoning compaction: a no-op for Claude (encrypted handle, cheap to
# resend) -> only latency risk, no gain.
ENV HEADROOM_THINKING_COMPACT=0

# --- Cost-aware model routing ---
# Rule 1: Anthropic requests <= 5000 input tokens without tools -> Haiku
#   (from_models restricts to Anthropic models; placed BEFORE the Opus rule,
#   first match wins).
# Rule 2: remaining Opus 5 requests -> Opus 4.8.
ENV HEADROOM_MODEL_ROUTER_ENABLED=1
# Single-quoted so Docker keeps the embedded double quotes literal.
ENV HEADROOM_MODEL_ROUTES='[{"name":"small-no-tools-to-haiku","from_models":["claude-opus-5","claude-opus-5[1m]","claude-sonnet-5","claude-sonnet-5[1m]","claude-opus-4-8"],"max_input_tokens":5000,"require_no_tools":true,"to_model":"claude-haiku-4-5"},{"name":"opus5-to-opus48","from_models":["claude-opus-5","claude-opus-5[1m]"],"to_model":"claude-opus-4-8"}]'

# --- Resources ---
# WORKERS=1: single uvicorn process -> in-memory state (TOIN, TTL) stays
# consistent; multiple workers fragment it.
ENV HEADROOM_WORKERS=1
# limit_concurrency: outer uvicorn gate; beyond this many in-flight requests
# the server returns 503 (no queueing). A clean 503 beats an OOM kill that
# would destroy in-memory state. Tune against `docker stats`.
ENV HEADROOM_LIMIT_CONCURRENCY=64

# --- Rate limiting OFF ---
# Headroom's own limiter is pure overhead for 1 user + subscription (real
# quota sits with Anthropic). Triple-secured: toggle off + both limits ~inf.
ENV HEADROOM_RATE_LIMIT_ENABLED=0
ENV HEADROOM_RATE_LIMIT_REQUESTS_PER_MINUTE=1000000
ENV HEADROOM_RATE_LIMIT_TOKENS_PER_MINUTE=1000000000

# --- Telemetry & state ---
# Telemetry is purely local, feeds /stats and the dashboard.
ENV HEADROOM_TELEMETRY=on
# Cost tracking OFF: meaningless under a team plan and LiteLLM can't map the
# routed model IDs (throws a red line per request). Savings tiles unaffected.
ENV HEADROOM_COST_TRACKING_ENABLED=0
# Savings state, TOIN models and TTL observations must survive restarts.
ENV HEADROOM_STATELESS=false
# HEADROOM_WORKSPACE_DIR stays coupled to the headroom-data:/data mount.
ENV HEADROOM_WORKSPACE_DIR=/data

# --- Output shaping (output-token reduction) ---
# Cache-safe: appends a terse note to the system-prompt TAIL, lowers thinking
# effort on routine post-tool turns. Requires the beta channel to activate.
ENV HEADROOM_ROLLOUT_CHANNEL=beta
ENV HEADROOM_OUTPUT_SHAPER=1
# 10% unshaped control group -> the dashboard shows a MEASURED number.
ENV HEADROOM_OUTPUT_HOLDOUT=0.1
