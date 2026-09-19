# syntax=docker/dockerfile:1
# nginx dashboard reverse proxy + CA download page.
# Base pinned by digest. Resolve with:
#   docker inspect --format '{{index .RepoDigests 0}}' nginx:alpine
# nginx.conf and html/ are baked here (root-owned, world-readable COPY
# layers) -> the old runtime html-copy + chmod workaround is gone. Only the
# CA copy stays runtime (compose command), since mitm-certs is populated by
# mitmproxy at run time.
FROM nginx:alpine@sha256:62ff2089abf5a9ed33bd232895bef5e22f7bb4b200675cec49a5ebc48e3d4ac8
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/
