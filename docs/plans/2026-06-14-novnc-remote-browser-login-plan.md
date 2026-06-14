# LittleGankNews noVNC 远程浏览器登录实施计划

日期：2026-06-14

状态：已实施

相关文档：

- [Phase 2 Worker/SSE/Profile/Health 计划](2026-06-13-phase2-worker-sse-profile-health-plan.md)
- [Twitter/X 浏览器监听监控系统实施计划](2026-06-13-twitter-browser-monitor-plan.md)
- [noVNC PoC 文档](../poc-remote-browser-novnc.md)

## 1. 目标

本阶段目标是把当前 Login Session 的“记录状态”能力，升级为可真实使用的服务器远程浏览器登录能力。管理员可以在前端创建登录会话，打开同域名下的 noVNC 页面，手动在服务器 Chromium 中登录 Twitter/X。系统不保存账号密码，只保存浏览器 Profile/Cookie 所在目录，并在用户确认登录完成后把 Monitoring Account 与 Browser Profile 标记为可用。

完成后系统应具备以下能力：

- 前端 Login Sessions 页面可以创建一个真实的远程浏览器会话。
- 后端创建 Login Session 时生成一次性访问 token，并返回可打开的 `vnc_url`。
- noVNC 通过 `https://ganknews.886668.shop/novnc/` 访问，不暴露裸 VNC/websockify 端口。
- noVNC 访问需要 token 校验，token 只在 session 为 `running` 且未过期时有效。
- 用户在 noVNC 中手动输入 Twitter/X 账号密码，密码不进入数据库和日志。
- 用户点击“完成登录”后，系统把相关 Browser Profile 和 Monitoring Account 标记为 `active`。
- 同一时间只允许 1 个远程浏览器登录会话，适配 4GB 服务器。

## 2. 边界

### 2.1 做什么

- 新增 `remote-browser` Docker 服务，运行 Chromium + noVNC/websockify。
- 通过 nginx `/novnc/` 路径反向代理 noVNC，并支持 WebSocket upgrade。
- Login Session 创建时自动进入 `running` 状态并生成 `vnc_url`。
- 增加 noVNC token 校验 API，供 nginx `auth_request` 使用。
- 前端 Login Sessions 页面展示远程浏览器入口，并禁用重复创建 running session。
- complete/cancel 时失效 token，并写入 SSE/WebEvent。

### 2.2 不做什么

- 不保存 Twitter/X 密码。
- 不破解验证码、不绕过风控、不自动重登。
- 不实现多用户并发 noVNC。
- 不让 API 容器挂载 Docker socket。
- 不在本阶段实现真实 Twitter/X DOM 解析。
- 不开放裸 `6080`、`5900`、Chrome remote debugging 等端口到公网。

## 3. 当前代码基线

| 模块 | 当前状态 |
|---|---|
| LoginSession model | 已有 `status`、`vnc_url`、`extra_data`、`browser_profile_id`、`monitoring_account_id` |
| Login Sessions API | 已有 create/list/get/complete/cancel，但 create 不启动远程浏览器、不设置 `vnc_url` |
| Login Sessions 前端 | 已有列表、新建、完成、取消；如果 `vnc_url` 非空会显示“打开” |
| Docker Compose | 已有 postgres/redis/api/web/scheduler/listener/detail/health，无 remote-browser |
| nginx | 已代理 `/api/` 和 SSE，无 `/novnc/` WebSocket 代理 |
| 安全 | `API_AUTH_ENABLED=false`，因此 noVNC 必须单独做 token 防护 |

## 4. 推荐架构

采用单实例 remote-browser 方案：

```text
用户浏览器
  -> https://ganknews.886668.shop/novnc/...
  -> web 容器 nginx
  -> remote-browser:6080
  -> noVNC/websockify
  -> Xvfb + Chromium
  -> /profiles 持久化 Profile
```

选择理由：

- 4GB 服务器资源有限，单实例最稳。
- 不需要 API 操作 Docker，不引入 Docker socket 安全风险。
- 与 Phase 2 的“同一时间只允许一个登录会话”边界一致。
- 实现量小，能先跑通人工登录闭环。

## 5. 状态机

| 状态 | 含义 | 行为 |
|---|---|---|
| `pending` | session 已创建但浏览器未就绪 | 最小版本可跳过，直接进入 `running` |
| `running` | noVNC token 有效，等待用户登录 | 前端显示远程浏览器入口 |
| `completed` | 用户确认登录完成 | 标记 Profile/Monitoring Account active，失效 token |
| `cancelled` | 用户取消 | 失效 token |
| `failed` | 启动或校验失败 | 保存错误信息 |

## 6. 后端实施

### 6.1 配置项

新增配置：

```env
NOVNC_PUBLIC_BASE_URL=/novnc/
LOGIN_SESSION_TOKEN_TTL_SECONDS=1800
LOGIN_SESSION_MAX_CONCURRENT=1
```

### 6.2 Token 生成与存储

创建 session 时：

- 生成 `secrets.token_urlsafe(32)`。
- 在 `extra_data` 中保存 token hash、expires_at、public path。
- 返回的 `vnc_url` 带原始 token。
- 日志中不得打印完整 token。

`extra_data` 结构示例：

```json
{
  "novnc_token_hash": "sha256:...",
  "novnc_expires_at": "2026-06-14T12:00:00Z"
}
```

### 6.3 API 行为

`POST /api/v1/login-sessions`

- 检查 running session 数量，超过限制返回 `409 Conflict`。
- 创建 session。
- 设置 `status=running`、`started_at=now`、`vnc_url=/novnc/vnc.html?...token=...`。
- 写入 `login_session.created` / `login_session.running` 事件。

`GET /api/v1/login-sessions/novnc-auth`

- 从 query 或 header 读取 token。
- 校验 token hash、session 状态、过期时间。
- 成功返回 `204`，失败返回 `401/403`。
- 给 nginx `auth_request` 调用。

`POST /api/v1/login-sessions/{id}/complete`

- 标记 session `completed`。
- 失效 token。
- 如果关联了 Browser Profile，标记为 `active`。
- 如果关联了 Monitoring Account，标记为 `active`。
- 写入事件。

`POST /api/v1/login-sessions/{id}/cancel`

- 标记 session `cancelled`。
- 失效 token。
- 写入事件。

## 7. Docker / nginx 实施

### 7.1 remote-browser 服务

新增服务应满足：

- 运行 Chromium。
- 提供 noVNC/websockify 入口。
- 挂载 `./storage/profiles:/profiles`。
- 不把 noVNC 端口直接发布到宿主机。
- 设置较大的 `/dev/shm`，避免 Chromium 崩溃。

示例方向：

```yaml
remote-browser:
  build:
    context: .
    dockerfile: docker/remote-browser.Dockerfile
  restart: unless-stopped
  expose:
    - "6080"
  shm_size: "1gb"
  volumes:
    - ./storage/profiles:/profiles
```

### 7.2 nginx noVNC 代理

`/novnc/` 需要：

- WebSocket upgrade。
- `proxy_buffering off`。
- 长 read timeout。
- auth_request 到 API。

典型配置：

```nginx
location /novnc/ {
    auth_request /api/v1/login-sessions/novnc-auth;
    proxy_pass http://remote-browser:6080/;
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

## 8. 前端实施

Login Sessions 页面调整：

- 顶部说明“这里是服务器远程浏览器登录，不保存密码”。
- running session 卡片突出显示远程浏览器入口。
- 有 running session 时禁用“新建”。
- `vnc_url` 可以新窗口打开，优先不 iframe 内嵌，以减少 noVNC 路径和 WebSocket 兼容问题。
- 完成/取消按钮需要二次确认。

## 9. 安全要求

- noVNC token 有效期默认 30 分钟。
- complete/cancel 后立即失效。
- noVNC 原始端口不对公网开放。
- 不记录密码，不记录完整 token。
- 如果服务器前面有外部反向代理，必须支持 WebSocket upgrade。
- 建议给 `/novnc/` 加简单频率限制。

## 10. 验收清单

- `docker compose build` 成功。
- `docker compose up -d` 后 `remote-browser` 运行。
- `POST /api/v1/login-sessions` 返回 `status=running` 和非空 `vnc_url`。
- 创建第二个 running session 返回 `409`。
- 打开 `https://ganknews.886668.shop/novnc/...` 可看到 Chromium。
- 浏览器开发者工具中 noVNC WebSocket 返回 `101 Switching Protocols`。
- 无 token、过期 token、complete/cancel 后 token 均无法访问 noVNC。
- 用户可在 Chromium 中手动登录 `https://x.com`。
- 点击完成后 session 变为 `completed`，关联账号/Profile 变为 `active`。
- 重启 remote-browser 后，同一 Profile 仍保持登录态。

## 11. 实施顺序

1. 新增配置项和环境变量。
2. 实现 Login Session token 生成、并发限制和 `vnc_url` 回填。
3. 增加 noVNC auth endpoint。
4. 增加 remote-browser Docker 服务。
5. 增加 nginx `/novnc/` 代理。
6. 调整前端 Login Sessions 页面。
7. 在服务器验证 noVNC 登录闭环。
