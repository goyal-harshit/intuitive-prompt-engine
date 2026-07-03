# ---- IntuitivePromptEngine frontend (static SPA behind nginx) --------------
# The SPA has no build step, so we just copy it into nginx and drop in a config
# that reverse-proxies /api and /ws to the backend container.
FROM nginx:1.27-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
