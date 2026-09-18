# mitmproxy addon: routes LLM API requests (Anthropic, OpenAI, Gemini) ->
# Headroom. Conditional streaming (stream = internal buffering flag,
# NOT a header):
#   - Requests:  only passthrough flows stream (RC uplink, remaining tunnel).
#                Routed requests are buffered (small JSON bodies,
#                Headroom needs them in full).
#   - Responses: only text/event-stream streams (the Remote Control channel and
#                SSE responses from all three providers). Buffering SSE
#                stalls the RC channel and breaks Remote Control.
#
# Provider routing (each toggleable via env, without a file change):
#   MITM_ROUTE_HEADROOM=0  -> no routing at all (MITM only)
#   MITM_ROUTE_OPENAI=0    -> OpenAI passthrough
#   MITM_ROUTE_GEMINI=0    -> Gemini passthrough
# Headroom endpoints: /v1/messages and /v1/chat/completions are documented;
# the native generativelanguage route is NOT -> check the first
# Gemini request after enabling it (404 from the proxy => set MITM_ROUTE_GEMINI=0).
import logging
import os
import re

from mitmproxy import http

log = logging.getLogger(__name__)

HEADROOM_HOST = "headroom"
HEADROOM_PORT = 8787
MARKER = "x-mitm-routed"

ROUTE = os.environ.get("MITM_ROUTE_HEADROOM", "1") != "0"
ROUTE_OPENAI = os.environ.get("MITM_ROUTE_OPENAI", "1") != "0"
ROUTE_GEMINI = os.environ.get("MITM_ROUTE_GEMINI", "1") != "0"

# Exact (host, path) pairs; the query string is stripped before comparison.
EXACT_ROUTES = {
    ("api.anthropic.com", "/v1/messages"): True,
    ("api.openai.com", "/v1/chat/completions"): ROUTE_OPENAI,
}
# Gemini (Google AI Studio API): /v1beta|/v1 + models/{model}:generateContent
GEMINI_HOST = "generativelanguage.googleapis.com"
GEMINI_PATH = re.compile(r"^/v1(beta)?/models/[^/:]+:(generateContent|streamGenerateContent)$")


def _match(r: http.Request) -> bool:
    if r.method != "POST":
        return False
    path = r.path.split("?", 1)[0]
    if EXACT_ROUTES.get((r.pretty_host, path), False):
        return True
    return ROUTE_GEMINI and r.pretty_host == GEMINI_HOST and bool(GEMINI_PATH.match(path))


def requestheaders(flow: http.HTTPFlow) -> None:
    r = flow.request
    if MARKER in r.headers:                      # loop guard
        r.stream = True
        log.info(f"PASS (loop guard) {r.path}")
        return
    routed = ROUTE and _match(r)
    flow.metadata["routed"] = routed
    log.info(f"{'ROUTE' if routed else 'PASS '} {r.method} {r.pretty_host}{r.path}")
    if routed:
        orig_host = r.pretty_host
        r.headers[MARKER] = "1"
        r.host, r.port = HEADROOM_HOST, HEADROOM_PORT
        r.scheme = "http"
        r.host_header = orig_host                # keep the original host for Headroom
        # deliberately NOT r.stream: body is buffered to Headroom
    else:
        r.stream = True                          # passthrough, unbuffered


def responseheaders(flow: http.HTTPFlow) -> None:
    ct = flow.response.headers.get("content-type", "")
    if "text/event-stream" in ct or not flow.metadata.get("routed"):
        flow.response.stream = True
