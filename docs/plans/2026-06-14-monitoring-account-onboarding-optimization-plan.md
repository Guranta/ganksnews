# LittleGankNews 监控账号添加与登录流程优化计划

日期：2026-06-14

状态：已实施

相关文档：

- [noVNC 远程浏览器登录实施计划](2026-06-14-novnc-remote-browser-login-plan.md)
- [Phase 2 Worker/SSE/Profile/Health 计划](2026-06-13-phase2-worker-sse-profile-health-plan.md)
- [Twitter/X 浏览器监听监控系统实施计划](2026-06-13-twitter-browser-monitor-plan.md)

## 1. 目标

当前添加一个可用监控账号需要跨三个页面操作：先在 Monitoring Accounts 创建账号，再在 Browser Profiles 创建并关联 profile，最后在 Login Sessions 创建远程登录会话并打开 noVNC。这个流程容易漏步骤，也会导致 Login Session 在没有 BrowserProfile 时只记录临时 profile 目录，形成数据库不可追踪的孤儿 profile 语义。

本阶段目标是把“添加监控账号并完成远程登录”收敛为一个主流程：管理员在监控账号页面输入 username，系统自动创建 MonitoringAccount、BrowserProfile 和 LoginSession，并直接返回 noVNC 地址供管理员登录。现有 Browser Profiles 和 Login Sessions 页面保留为高级管理与调试入口。

完成后系统应具备以下能力：

- 在 `/monitoring-accounts` 页面一键“添加并登录”。
- 后端一次性创建账号、浏览器 profile 和登录会话。
- 新账号未完成登录前状态为 `needs_login`，完成登录后变为 `active`。
- 自动创建的 BrowserProfile 与 MonitoringAccount 持久化关联，不再产生孤儿 profile 目录。
- 重复 username 返回友好的 `409 Conflict`，不再暴露数据库错误。
- 登录取消后 account/profile 回到 `needs_login`，状态语义保持一致。

## 2. 边界

### 2.1 做什么

- 新增一键 onboarding API：`POST /monitoring-accounts/with-login-session`。
- 自动创建 BrowserProfile，并与 MonitoringAccount 关联。
- 新账号默认状态改为 `needs_login`（优先 service 层实现，暂不强制 migration）。
- 修复 MonitoringAccount 重复创建的错误返回。
- 修改 Login Session complete/cancel 的状态联动。
- 前端 Monitoring Accounts 页面改造为主入口，成功后自动打开 noVNC。
- Login Sessions 页面保留高级入口，但不再鼓励无 profile 创建登录会话。

### 2.2 不做什么

- 不保存 Twitter/X 密码。
- 不自动输入账号密码或自动重登。
- 不绕过验证码、不处理风控挑战自动化。
- 不改造为多 noVNC 并发登录。
- 不重构整个 account/profile/login-session 模块。
- 不在本阶段批量修改历史账号状态，避免误伤已有可用账号。

## 3. 当前代码基线

| 模块 | 当前状态 |
|---|---|
| MonitoringAccount | 有 `platform`、`username`、`status`、`notes`，唯一约束为 `(platform, username)`，模型默认 `active` |
| BrowserProfile | 有 `name`、`profile_path`、`monitoring_account_id`、`status`，`profile_path` 唯一 |
| LoginSession | 可关联 `browser_profile_id` 和 `monitoring_account_id`，已有 noVNC `vnc_url` 和 token 机制 |
| Monitoring Accounts API | CRUD 完整，但 create 不处理重复用户名 409，默认状态不符合未登录语义 |
| Login Sessions API | create 可不传 profile；不传时后端只在 `extra_data.profile_dir` 记录目录，不创建 BrowserProfile 行 |
| 前端 | Monitoring Accounts、Browser Profiles、Login Sessions 是三个分散页面 |

## 4. 推荐方案

采用最小编排 API，不做大重构：

```text
用户在 /monitoring-accounts 点击“添加并登录”
  -> POST /api/v1/monitoring-accounts/with-login-session
  -> 创建 MonitoringAccount(status=needs_login)
  -> 创建 BrowserProfile(status=in_use, monitoring_account_id=account.id)
  -> 创建 LoginSession(status=running, 生成 vnc_url)
  -> 前端自动 window.open(vnc_url)
  -> 用户在 noVNC 中手动登录 Twitter/X
  -> 用户点击 Login Session “完成”
  -> MonitoringAccount(status=active), BrowserProfile(status=available)
```

选择理由：

- 改动集中，符合当前资源模型。
- 保留现有 CRUD 页面，不破坏高级管理能力。
- 避免 API 容器操作 Docker，也不增加新服务。
- 与当前 noVNC 单并发限制兼容。

## 5. 后端 API 设计

### 5.1 新增接口

```http
POST /api/v1/monitoring-accounts/with-login-session
```

请求体：

```json
{
  "username": "someuser",
  "display_name": "Some User",
  "notes": "optional notes"
}
```

字段规则：

- `username` 必填。
- service 层规范化 username：`strip()` 并去掉开头 `@`。
- 第一版不强制 lower-case，避免和历史大小写数据产生兼容风险。
- `platform` 第一版固定使用 `twitter`，暂不暴露到前端。

响应体：

```json
{
  "account": {},
  "browser_profile": {},
  "login_session": {},
  "vnc_url": "/novnc/vnc.html?..."
}
```

新增 schema：

```python
class MonitoringAccountWithLoginSessionCreate(BaseModel):
    username: str
    display_name: str | None = None
    notes: str | None = None


class MonitoringAccountWithLoginSessionResponse(BaseModel):
    account: MonitoringAccountResponse
    browser_profile: BrowserProfileResponse
    login_session: LoginSessionResponse
    vnc_url: str | None
```

错误返回：

| 场景 | HTTP | detail |
|---|---:|---|
| username 为空 | 400 或 422 | `Username is required` |
| 账号已存在 | 409 | `Monitoring account already exists for platform=twitter username=...` |
| 已有 running login session | 409 | 复用现有并发限制错误 |

### 5.2 可选第二阶段接口

```http
POST /api/v1/monitoring-accounts/{account_id}/login-session
```

用途：给已有账号重新发起登录。第一阶段可以不做，避免扩大范围。

## 6. BrowserProfile 自动创建策略

自动创建时必须创建数据库行，不再只写 `LoginSession.extra_data.profile_dir`。

命名规则：

```text
twitter:@{username}
```

路径规则：

```text
{settings.BROWSER_PROFILES_DIR}/twitter/{monitoring_account_id}
```

示例：

```text
/app/storage/profiles/twitter/2c33f5f4-...
```

状态规则：

| 场景 | BrowserProfile.status |
|---|---|
| 自动创建且立即启动 LoginSession | `in_use` |
| 登录完成 | `available` |
| 登录取消 | `needs_login` |
| 登录失败（后续实现） | `error` 或 `needs_login` |

关联规则：

```python
BrowserProfile.monitoring_account_id = account.id
```

## 7. MonitoringAccount 状态流转

| 动作 | MonitoringAccount.status |
|---|---|
| 普通创建账号 | `needs_login` |
| 一键创建并启动登录 | `needs_login` |
| 用户确认登录完成 | `active` |
| 用户取消登录 | `needs_login` |
| 登录失败 | `needs_login`，如能识别挑战则后续可设 `challenged` |

`complete` 时建议同时更新：

```python
MonitoringAccount.last_login_check_at = now
```

## 8. 旧 LoginSession 创建接口调整

当前 `POST /login-sessions` 在没有 `browser_profile_id` 时会生成临时 `profile_dir`，但不会创建 BrowserProfile 行。建议修正为：

- 第一版前端不再提供“不关联 Profile”的主流程。
- 后端如果 `monitoring_account_id` 存在但 `browser_profile_id` 为空，返回 400，并提示使用 `/monitoring-accounts/with-login-session`。
- 如保留两个都为空的调试 session，也不要写 `extra_data.profile_dir`。

更严格版本：`POST /login-sessions` 必须传 `browser_profile_id`。

## 9. 前端改造计划

### 9.1 Monitoring Accounts 页面

文件：`apps/web/src/features/monitoring-accounts/MonitoringAccountsPage.tsx`

主按钮改为：

```text
添加并登录
```

Dialog 文案：

```text
添加监控账号并登录
系统将自动创建浏览器配置并打开远程浏览器。请在 noVNC 中手动完成 X/Twitter 登录。
```

提交调用：

```ts
api.monitoringAccounts.createWithLoginSession(data)
```

成功后：

- 自动 `window.open(result.vnc_url || result.login_session.vnc_url, "_blank", "noopener,noreferrer")`
- 关闭 dialog。
- toast 提示用户完成 noVNC 登录后去 Login Sessions 点击“完成”。
- invalidate：`monitoring-accounts`、`browser-profiles`、`login-sessions`、`dashboard`。

状态展示建议中文化：

| status | label |
|---|---|
| active | 已登录 |
| needs_login | 需要登录 |
| challenged | 需要验证 |
| suspended | 已封禁 |
| inactive | 未激活 |

### 9.2 API client 与类型

文件：`apps/web/src/types/index.ts`

新增：

```ts
export interface MonitoringAccountWithLoginSessionCreate {
  username: string;
  display_name?: string;
  notes?: string;
}

export interface MonitoringAccountWithLoginSessionResponse {
  account: MonitoringAccount;
  browser_profile: BrowserProfile;
  login_session: LoginSessionItem;
  vnc_url: string | null;
}
```

文件：`apps/web/src/api/index.ts`

新增：

```ts
createWithLoginSession: (data: MonitoringAccountWithLoginSessionCreate) =>
  request<MonitoringAccountWithLoginSessionResponse>(
    "/monitoring-accounts/with-login-session",
    { method: "POST", body: JSON.stringify(data) }
  )
```

### 9.3 Login Sessions 页面

文件：`apps/web/src/features/login-sessions/LoginSessionsPage.tsx`

最小调整：

- 创建成功后自动打开 `vnc_url`。
- 不再把“不关联 Profile”作为推荐路径。
- 如果保留“不关联”，明确标注为调试模式。

### 9.4 Browser Profiles 页面

文件：`apps/web/src/features/browser-profiles/BrowserProfilesPage.tsx`

轻量加说明：

```text
浏览器配置通常会在添加监控账号并登录时自动创建；此页面用于高级管理。
```

## 10. 后端实施步骤

1. 在 `schemas/monitoring_accounts.py` 新增组合 create/response schema。
2. 在 `services/monitoring_accounts.py` 新增 `MonitoringAccountAlreadyExists`、`normalize_username()`。
3. 修复普通 `create_monitoring_account()`：规范化 username、查重、默认 `needs_login`、捕获 `IntegrityError`。
4. 新增 `create_monitoring_account_with_login_session()` 编排逻辑。
5. 在 `api/v1/monitoring_accounts.py` 新增 `POST /with-login-session`，注意放在动态路径前。
6. 修改 `api/v1/login_sessions.py`：complete 补 `last_login_check_at`，cancel 联动 account/profile 回到 `needs_login`。
7. 修改 `services/login_sessions.py`：停止无 profile 时写孤儿 `profile_dir`；必要时对缺 profile 的账号登录返回 400。
8. 补充必要 SSE/WebEvent，至少保持现有 login session event 不回退。

## 11. 前端实施步骤

1. 更新 `types/index.ts`，新增组合请求/响应类型。
2. 更新 `api/index.ts`，新增 `createWithLoginSession()`。
3. 改造 `MonitoringAccountsPage.tsx`：主按钮、dialog、mutation、成功打开 noVNC、状态中文化。
4. 微调 `LoginSessionsPage.tsx`：创建成功自动打开 noVNC，弱化无 profile 模式。
5. 微调 `BrowserProfilesPage.tsx`：说明自动创建策略。

## 12. 验证清单

### 12.1 后端验证

- `POST /monitoring-accounts/with-login-session` 输入新 username 返回 201。
- 返回中包含 `account`、`browser_profile`、`login_session`、`vnc_url`。
- 新 account 状态为 `needs_login`。
- 新 profile 状态为 `in_use`，且 `monitoring_account_id` 指向 account。
- 新 login session 状态为 `running`，且包含可用 `vnc_url`。
- 再次用同 username 创建返回 409。
- 已有 running session 时再次 onboarding 返回 409。
- `POST /login-sessions/{id}/complete` 后 account 为 `active`，profile 为 `available`，`last_login_check_at` 更新。
- `POST /login-sessions/{id}/cancel` 后 account/profile 为 `needs_login`。

### 12.2 前端验证

- `/monitoring-accounts` 点击“添加并登录”可成功创建。
- 成功后自动打开 noVNC 新窗口。
- 列表中账号显示为“需要登录”。
- Login Sessions 页面出现 running 会话。
- 点击完成后账号状态变为“已登录”。
- 重复 username 时 toast 显示 409 友好错误。

### 12.3 部署验证

- `docker compose up -d --build api web` 成功。
- `docker compose restart web` 后 nginx 能解析 remote-browser 新 IP。
- `https://ganknews.886668.shop/novnc/` 只能通过带 token 的链接访问。
- Postgres/Redis/remote-browser 端口不暴露到公网。

## 13. 风险与兼容

| 风险 | 说明 | 处理 |
|---|---|---|
| 历史账号状态 | 旧账号可能仍是 `active` 但实际未登录 | 第一版不批量改历史数据，避免误伤 |
| username 大小写 | DB 唯一约束大小写敏感 | 第一版只 trim + 去 `@`，不强制 lower-case |
| 并发竞态 | 两个请求同时创建相同 username | 先查重，再捕获 `IntegrityError` 返回 409 |
| noVNC 单实例 | 同时只能一个 running session | 保留当前 `LOGIN_SESSION_MAX_CONCURRENT=1` |
| 旧 LoginSession API | 可能仍被手动用于调试 | 第一版可保留调试能力，但不再创建孤儿 profile 目录 |

## 14. 建议提交粒度

1. `fix: normalize monitoring account creation defaults and duplicate handling`
2. `feat: add monitoring account onboarding with login session`
3. `feat: add one-click account login onboarding UI`
4. `fix: align login session cancel and complete state transitions`
