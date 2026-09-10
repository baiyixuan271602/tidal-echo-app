server {
    listen ${PORT} default_server;
    server_name _;
    client_max_body_size 12m;

    # ---- PWA (chat UI) ----
    location /chat/ {
        root /app;
        try_files $uri $uri/ /chat/index.html;
    }
    location = /chat { return 302 /chat/; }
    location = / { return 302 /chat/; }

    # ---- relay API (strip /relay prefix -> relay :3011) ----
    location /relay/ {
        proxy_pass http://127.0.0.1:3011/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE must not be buffered (critical!)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
