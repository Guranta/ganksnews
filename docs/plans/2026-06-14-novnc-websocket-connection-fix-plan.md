# noVNC WebSocket Connection Fix Plan

Date: 2026-06-14

## Background

After redeploying LittleGankNews, the previous noVNC page 404 was resolved by routing `/novnc/vnc.html` to the dorowu image's actual noVNC page path:

```nginx
proxy_pass http://remote-browser:80/static/novnc/vnc.html;
```

The noVNC page now loads, and static assets such as `/novnc/app/ui.js` and `/novnc/core/rfb.js` are reachable. The remaining failure is that the noVNC UI displays an unable-to-connect message after page load.

This indicates the problem has moved from the initial page route to the WebSocket/VNC connection path.

## Current Behavior

The backend currently generates VNC URLs in two places:

- `apps/api/app/services/login_sessions.py`
- `apps/api/app/services/monitoring_accounts.py`

Current URL shape:

```text
/novnc/vnc.html?path=/novnc/websockify&token=<token>&autoconnect=true
```

The noVNC UI builds its WebSocket URL by prepending `/` to the `path` value. Because the generated `path` already starts with `/`, the browser may attempt a fragile double-slash WebSocket path:

```text
wss://ganknews.886668.shop//novnc/websockify
```

The desired WebSocket URL is:

```text
wss://ganknews.886668.shop/novnc/websockify
```

## Likely Root Cause

The generated `path` query parameter should not include a leading slash. dorowu/noVNC-style routing expects a path like:

```text
novnc/websockify
```

not:

```text
/novnc/websockify
```

Plain HTTP checks against `/novnc/websockify` returning 404 are not conclusive, because dorowu's internal nginx may only route that endpoint to websockify when the request includes WebSocket upgrade headers. The real success condition is `101 Switching Protocols` for the WebSocket request.

## Fix Plan

### 1. Update backend VNC URL generation

Change both `_build_vnc_url()` implementations to emit a WebSocket path without a leading slash.

Target output with `NOVNC_PUBLIC_BASE_URL=/novnc/`:

```text
/novnc/vnc.html?path=novnc/websockify&token=<token>&autoconnect=true
```

Implementation shape:

```python
def _build_vnc_url(session_id: uuid.UUID, token: str) -> str:
    base = settings.NOVNC_PUBLIC_BASE_URL.rstrip("/")
    ws_path = f"{base.lstrip('/')}/websockify"
    return f"{base}/vnc.html?path={ws_path}&token={token}&autoconnect=true"
```

Files:

- `apps/api/app/services/login_sessions.py`
- `apps/api/app/services/monitoring_accounts.py`

### 2. Keep the dorowu noVNC page route fix

Keep the `docker/nginx.conf` page route aligned with the verified dorowu path:

```nginx
location = /novnc/vnc.html {
    proxy_pass http://remote-browser:80/static/novnc/vnc.html;
}
```

### 3. Add an explicit WebSocket proxy location

Add an exact `/novnc/websockify` location before the generic `/novnc/` location. This removes ambiguity from prefix stripping and makes WebSocket debugging clearer.

Target nginx block:

```nginx
location = /novnc/websockify {
    auth_request /novnc-auth-internal?token=$arg_token;
    auth_request_set $auth_status $upstream_status;

    proxy_pass http://remote-browser:80/websockify;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_buffering off;
}
```

File:

- `docker/nginx.conf`

### 4. Preserve auth flow

The intended auth flow remains:

1. Initial page request includes `token=<token>`.
2. nginx validates the token through `/novnc-auth-internal`.
3. nginx sets `novnc_token` cookie with `Path=/novnc/`.
4. Static asset and WebSocket requests authenticate through the cookie fallback in `/novnc-auth-internal`.

No token should be required in the WebSocket URL itself.

### 5. Deployment verification

After deployment, create a fresh login session and confirm the returned `vnc_url` has this shape:

```text
/novnc/vnc.html?path=novnc/websockify&token=...&autoconnect=true
```

It must not contain:

```text
path=/novnc/websockify
```

Then check browser DevTools:

```text
Network -> WS -> /novnc/websockify
```

Expected result:

```text
101 Switching Protocols
```

If it does not return `101`, use the status code to branch:

- `401` or `403`: token/cookie/auth_request issue.
- `404`: WebSocket path, route, or upgrade handling issue.
- `400` or `426`: missing or malformed WebSocket upgrade headers.
- `502` or `504`: upstream remote-browser or proxy issue.

## Server Verification Commands

Use a real token from a fresh login session.

Check page route:

```bash
curl -k -i 'https://ganknews.886668.shop/novnc/vnc.html?path=novnc/websockify&token=<token>&autoconnect=true'
```

Check WebSocket handshake through the public domain:

```bash
curl -k -i \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==' \
  -H 'Cookie: novnc_token=<token>' \
  'https://ganknews.886668.shop/novnc/websockify'
```

Expected:

```text
101 Switching Protocols
```

Check through local web container port:

```bash
curl -i \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==' \
  -H 'Cookie: novnc_token=<token>' \
  'http://127.0.0.1:18080/novnc/websockify'
```

Check dorowu internal endpoint from the web container:

```bash
docker compose exec web wget -S -O- http://remote-browser:80/websockify
```

Note: this last plain HTTP request may return 404 without WebSocket upgrade headers. It is useful for logs, but not the final success criterion.

## 实施结论

状态：已实施

经代码审查确认，当前 `_build_vnc_url()` 生成的 `path=/novnc/websockify` 是正确的绝对路径格式。noVNC 客户端对绝对路径 `path` 能正确处理，生成的 WebSocket URL 为 `wss://host/novnc/websockify`，可命中 nginx `/novnc/` location 并 proxy_pass 到 `remote-browser:80/websockify`，这是 dorowu 镜像的正确 WebSocket 端点。

原计划中"去掉前导 `/`"的修改不必要，因此**未修改后端代码**。实际的 noVNC 连接问题由 401 鉴权修复（拆分 auth_request location）解决。

## Open Questions

- Does browser DevTools show `wss://.../novnc/websockify` or `wss://...//novnc/websockify`?
- Does the WebSocket request include `Cookie: novnc_token=<token>`?
- Does the outer HTTPS nginx configuration forward WebSocket upgrade headers for `/novnc/`?
- Is production running the same `docker/nginx.conf` committed in the repository?
