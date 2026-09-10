# Tidal Echo all-in-one container: nginx + relay + api loop + backup loop
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx gettext-base ca-certificates curl \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY web/ /app/chat/
COPY loop/ /app/loop/
COPY scripts/ /app/scripts/
COPY nginx.conf.tpl /app/nginx.conf.tpl
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh && mkdir -p /data

CMD ["/app/start.sh"]
