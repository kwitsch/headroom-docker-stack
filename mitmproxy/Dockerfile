# syntax=docker/dockerfile:1
# mitmproxy with the LLM-routing addon baked in.
# Base pinned to a concrete version tag + digest (off the previous unpinned
# :latest). Resolve with:
#   docker inspect --format '{{index .RepoDigests 0}}' mitmproxy/mitmproxy:latest
#   docker inspect --format '{{index .Config.Labels "org.opencontainers.image.version"}}' mitmproxy/mitmproxy:latest
FROM mitmproxy/mitmproxy:12.2.3@sha256:00b77b5d8804c8ad18cb6caefbf9d5849e895e8986c5ce011f4ae30f4385962f
# Addon path stays /addons/redirect_headroom.py, matching the unchanged
# `-s /addons/redirect_headroom.py` flag in the compose command.
COPY redirect_headroom.py /addons/redirect_headroom.py
