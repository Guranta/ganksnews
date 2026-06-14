# LittleGankNews noVNC 401 Authorization Required 修复计划

日期：2026-06-14

状态：已实施

相关文档：

- [noVNC 远程浏览器登录实施计划](2026-06-14-novnc-remote-browser-login-plan.md)
- [监控账号添加与登录流程优化计划](2026-06-14-monitoring-account-onboarding-optimization-plan.md)

## 1. 问题现象

在“监控账号”页面点击“添加并登录”后，系统可以创建 MonitoringAccount、BrowserProfile 和 LoginSession，并打开 noVNC 地址。但远程浏览器页面或其后续连接会显示：

```text
401 Authorization Required
```

该错误不是 Twitter/X 登录失败，也不是 FastAPI 主 API 鉴权失败，而是 nginx 对 `/novnc/` 路径执行 `auth_request` 时返回的鉴权失败页面。

## 2. 根因判断

当前 noVNC URL 形态类似：

```text
/novnc/vnc.html?path=/novnc/websockify&token=<raw_token>&autoconnect=true
```

初始页面请求包含 `token` 查询参数，因此 nginx 可以把 `$arg_token` 转发到：

```text
/api/v1/login-sessions/novnc-auth?token=<raw_token>
```

但 noVNC 页面加载后会继续发起静态资源请求和 WebSocket 请求，例如：

```text
/novnc/websockify
```

这些后续请求不再携带 `token` 查询参数。若 nginx 对整个 `/novnc/` location 都使用同一套 `auth_request`，则后续请求中的 `$arg_token` 为空，API 校验失败，nginx 返回 `401 Authorization Required`。

## 3. 修复目标

修复后应满足：

- 初始 noVNC 页面仍必须带有效 token 才能访问。
- noVNC 静态资源和 WebSocket 请求可以在同一浏览器会话中继续通过鉴权。
- complete/cancel 后 token 失效，旧 noVNC 链接不能继续访问。
- 不暴露裸 VNC/websockify 端口。
- 不移除 noVNC token 防护。

## 4. 推荐方案

将 noVNC 页面加载和后续请求拆成两个 nginx location：

```text
/novnc/vnc.html
  -> 使用 URL query token 鉴权
  -> 鉴权成功后设置 novnc_token cookie

/novnc/
  -> 用 query token 或 cookie 鉴权
  -> 代理静态资源与 WebSocket
```

`/novnc-auth-internal` 的 token 选择逻辑：

```text
如果 $arg_token 非空：使用 $arg_token
否则：使用 $cookie_novnc_token
```

选择理由：

- 初始链接仍是一次性 token 入口。
- WebSocket 请求无需把 token 暴露在 WebSocket URL 中。
- cookie 只限定在 `/novnc/` 路径下。
- 改动集中在 nginx 配置，不需要改 LoginSession 数据模型。

## 5. nginx 修改计划

文件：`docker/nginx.conf`

### 5.1 修改 `/novnc-auth-internal`

目标：同时支持 query token 和 cookie token。

示例：

```nginx
location = /novnc-auth-internal {
    internal;

    set $auth_token "";
    if ($arg_token != "") {
        set $auth_token $arg_token;
    }
    if ($arg_token = "") {
        set $auth_token $cookie_novnc_token;
    }

    proxy_pass http://api:8000/api/v1/login-sessions/novnc-auth?token=$auth_token;
    proxy_set_header Host $host;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
}
```

### 5.2 新增 `/novnc/vnc.html` 精确匹配

目标：只在初始页面加载时设置 cookie，避免后续 WebSocket 请求用空 `$arg_token` 覆盖 cookie。

示例：

```nginx
location = /novnc/vnc.html {
    auth_request /novnc-auth-internal;
    auth_request_set $auth_status $upstream_status;

    add_header Set-Cookie "novnc_token=$arg_token; Path=/novnc/; Max-Age=3600; HttpOnly; SameSite=Strict" always;

    proxy_pass http://remote-browser:80/vnc.html;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 3600s;
    proxy_buffering off;
}
```

### 5.3 保留 `/novnc/` 通用代理

目标：静态资源和 WebSocket 继续鉴权，但主要通过 cookie 完成。

示例：

```nginx
location /novnc/ {
    auth_request /novnc-auth-internal;
    auth_request_set $auth_status $upstream_status;

    proxy_pass http://remote-browser:80/;
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

## 6. 验证计划

### 6.1 构建验证

执行：

```bash
docker compose build web
```

预期：web 镜像构建成功，nginx 配置随镜像更新。

### 6.2 noVNC 访问验证

操作：

1. 前端进入“监控账号”。
2. 点击“添加并登录”。
3. 输入新 username。
4. 提交后自动打开 noVNC 页面。

预期：

- `/novnc/vnc.html?...token=...` 返回 200。
- 浏览器收到 `novnc_token` cookie，路径为 `/novnc/`。
- `/novnc/websockify` 返回 `101 Switching Protocols`。
- 不再显示 `401 Authorization Required`。

### 6.3 token 失效验证

操作：

1. 创建并打开 noVNC。
2. 在 Login Sessions 页面点击“取消”或“完成”。
3. 刷新原 noVNC 页面。

预期：

- LoginSession token 已被后端移除或标记 revoked。
- 刷新旧 noVNC 链接不再可用。
- 后续访问 `/novnc/` 返回鉴权失败。

### 6.4 回归验证

检查以下流程不回退：

- `POST /api/v1/monitoring-accounts/with-login-session` 创建成功。
- 重复 username 返回 `409 Conflict`。
- 同时已有 running LoginSession 时再次创建返回 `409 Conflict`。
- complete 后 MonitoringAccount 为 `active`，BrowserProfile 为 `available`。
- cancel 后 MonitoringAccount 和 BrowserProfile 均回到 `needs_login`。

## 7. 部署计划

服务器执行：

```bash
git pull
docker compose build web
docker compose up -d web
```

如果外层还有独立反向代理，需要确认：

- `/novnc/` 路径会转发到 web 容器。
- 支持 WebSocket upgrade。
- 不额外剥离 Cookie 或 query string。

## 8. 风险与处理

| 风险 | 说明 | 处理 |
|---|---|---|
| Cookie 被空 token 覆盖 | 若在通用 `/novnc/` 中设置 cookie，WebSocket 请求会用空 `$arg_token` 覆盖旧 cookie | 只在 `/novnc/vnc.html` 精确 location 设置 cookie |
| Cookie 过期时间与 token TTL 不一致 | nginx cookie Max-Age 可能长于后端 token TTL | 后端仍校验 token hash 和 session 状态，cookie 只是传输凭据 |
| complete/cancel 后页面仍开着 | 页面本身可能停留，但刷新或新请求应失败 | complete/cancel 已移除 token hash，后续 auth 失败 |
| 外层代理不支持 WebSocket | noVNC 页面可打开但连接失败 | 部署时验证 `/novnc/websockify` 返回 101 |

## 9. 建议提交

```text
fix: noVNC 401 by splitting page-load and websocket auth
```

提交内容：

- 更新 `docker/nginx.conf`。
- `/novnc/vnc.html` 使用 query token 鉴权并设置 cookie。
- `/novnc/` 使用 cookie fallback 支持静态资源和 WebSocket。
- 保留后端 `novnc-auth` token 校验。
