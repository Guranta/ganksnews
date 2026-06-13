# LittleGankNews Phase 2 详细实施计划

日期：2026-06-13

状态：待实施

相关文档：

- [文档索引](../README.md)
- [第一版详细实施计划](2026-06-13-littleganknews-v1-implementation-plan.md)
- [架构图](../architecture.md)
- [需求文档](../requirements.md)

## 1. Phase 2 目标

Phase 2 的目标是把 Phase 1 已完成的账号/Profile 管理台，扩展为可运行、可观测、可恢复的后台任务系统。此阶段不追求完整 Twitter/X 推文解析，而是先完成 Worker 基座、Redis Streams、SSE 实时事件、Profile 锁、登录态健康检查和前端观测页面。

Phase 2 完成后，系统应具备以下能力：

- Worker 可以独立启动并持续写入心跳。
- Redis Streams 可以创建、消费、ACK、重试和写入死信。
- 后端可以向 `lgn:web_events` 写入事件，并通过 SSE 推送给前端。
- 前端可以看到 Worker 状态、队列状态、近期事件和测试通知。
- Browser Profile 有独占锁机制，避免多个 Worker 同时打开同一个 Profile。
- Monitoring Account 和 Browser Profile 有基础健康检查入口，可以把登录态异常写回状态。
- Scheduler 可以生成基础 crawl job，但不要求此阶段完成真实 X 推文解析。

## 2. Phase 2 边界

### 2.1 做什么

- 实现 `app.streams` Redis Streams 封装。
- 实现 `app.workers` 基础运行框架。
- 实现 `scheduler`、`health`、`detail` 的最小可运行版本。
- 实现 `listener` 的占位版本，能领取任务、更新状态、写测试事件，但不做完整 X 解析。
- 实现 Worker 心跳写入 `worker_heartbeats`。
- 实现队列状态 API、Worker 状态 API、近期事件 API、SSE 流 API。
- 实现 Profile 独占锁，优先使用 Redis lock，数据库字段同步展示状态。
- 实现 Profile/Monitoring Account 健康检查任务框架。
- 实现前端 Workers、Queues、Events/Notifications 页面或面板。
- 实现测试事件链路：API -> Redis Stream -> SSE -> 前端 toast/通知列表。

### 2.2 不做什么

- 不实现完整 CloakBrowser Listener 推文解析。
- 不实现 Twitter/X DOM 或网络响应 parser 的稳定版本。
- 不做多 Profile 并发调度优化。
- 不做 noVNC 登录界面。
- 不自动重登 Twitter/X，不破解验证码，不绕过风控。
- 不做 Telegram、Slack、邮件等外部通知。
- 不做 Prometheus/Grafana。
- 不做 Elasticsearch/OpenSearch。

## 3. 当前代码基线

Phase 1 已完成以下基础：

| 模块 | 当前状态 |
|---|---|
| FastAPI | 已可运行，已有 `/api/v1` 路由聚合 |
| 数据库 | SQLAlchemy models + Alembic 初始迁移已完成 |
| PostgreSQL/Redis | Docker Compose 已配置 |
| 管理 API | target accounts、monitoring accounts、browser profiles、monitor lists 已完成 |
| 前端 | Dashboard 和账号/Profile/List 管理页已完成并汉化 |
| Worker 目录 | `apps/api/app/workers/` 目前为空模块 |
| Streams 目录 | `apps/api/app/streams/` 目前为空模块 |
| Browser 目录 | `apps/api/app/browser/` 目前为空模块 |
| Docker worker 服务 | `scheduler/listener/detail/health` 已在 compose 预留，但模块尚不存在 |

Phase 2 应尽量复用当前表结构，只有确实需要时才新增迁移。

## 4. 从 sub2api 借鉴的工程模式

`sub2api` 的 OpenAI 登录态模型不能直接迁移到 Twitter/X，因为它依赖 OAuth token 和 refresh token；Twitter/X Web 登录态应继续以浏览器 Profile 为唯一权威状态。

可迁移的是工程模式：

| 模式 | 对 LittleGankNews 的落地 |
|---|---|
| 账号状态机 | 监控账号和浏览器 Profile 使用状态驱动调度 |
| 凭证健康检查 | 用浏览器 Profile 打开轻量页面判断是否登录、是否风控 |
| 分布式锁 | 每个 Profile 同时只能被一个 Worker 使用 |
| 失败冷却 | 登录失效、限流、异常时跳过调度，不反复撞风控 |
| 人工处理标记 | `needs_login`、`challenged`、`suspended` 进入人工处理 |
| 敏感信息不入库 | 不保存完整 cookies，只保存状态、摘要和错误信息 |

## 5. 状态机设计

### 5.1 Monitoring Account 状态

现有枚举：

| 状态 | 含义 | 调度策略 |
|---|---|---|
| `active` | 可用于监听 | 可调度 |
| `needs_login` | 登录态失效 | 不调度，等待人工重新登录 |
| `challenged` | 遇到验证、风控、解锁页面 | 不调度，等待人工处理 |
| `suspended` | 账号被冻结或不可用 | 不调度 |
| `inactive` | 管理员停用 | 不调度 |

### 5.2 Browser Profile 状态

现有枚举：

| 状态 | 含义 | 调度策略 |
|---|---|---|
| `available` | Profile 可用且未被占用 | 可调度 |
| `in_use` | Worker 正在使用 | 不重复调度 |
| `needs_login` | Profile 登录态失效 | 不调度 |
| `error` | Profile 启动失败、路径无效或检测异常 | 不调度 |
| `unregistered` | 新登记但未通过健康检查 | 不调度 |

### 5.3 Crawl Job 状态

现有枚举：

| 状态 | 含义 |
|---|---|
| `pending` | 已创建，等待 Worker 领取 |
| `running` | Worker 正在处理 |
| `completed` | 成功结束 |
| `failed` | 失败，可重试或进入死信 |
| `cancelled` | 被取消 |

## 6. 后端模块规划

### 6.1 Streams 模块

新增目录和文件：

```text
apps/api/app/streams/
  __init__.py
  names.py
  messages.py
  client.py
  consumers.py
  dead_letter.py
```

职责：

| 文件 | 职责 |
|---|---|
| `names.py` | 统一定义 stream key、consumer group、event type |
| `messages.py` | 定义 Pydantic message payload |
| `client.py` | 封装 `XADD`、`XREADGROUP`、`XACK`、`XLEN`、`XPENDING` |
| `consumers.py` | 通用 consumer loop、重试、backoff |
| `dead_letter.py` | 写入 `lgn:dead_letter` 的统一逻辑 |

Stream 命名：

| Stream | Phase 2 用途 |
|---|---|
| `lgn:web_events` | SSE 推送事件 |
| `lgn:worker_events` | Worker 生命周期事件 |
| `lgn:account_events` | 账号/Profile 健康检查事件 |
| `lgn:crawl_jobs` | Scheduler 到 Listener 的任务流，可选，允许先用 DB `crawl_jobs` |
| `lgn:raw_tweets` | Phase 2 只写测试样例，Phase 3 才接真实 Listener |
| `lgn:dead_letter` | 多次失败后的死信 |

最小接口：

```python
async def xadd(stream: str, payload: dict, maxlen: int | None = None) -> str
async def ensure_group(stream: str, group: str) -> None
async def read_group(stream: str, group: str, consumer: str, count: int, block_ms: int) -> list[StreamMessage]
async def ack(stream: str, group: str, message_id: str) -> None
async def pending(stream: str, group: str) -> StreamPendingSummary
async def len(stream: str) -> int
async def to_dead_letter(source_stream: str, message: dict, error: str) -> str
```

### 6.2 Worker 基座

新增目录和文件：

```text
apps/api/app/workers/
  __init__.py
  base.py
  heartbeat.py
  locks.py
  scheduler.py
  listener.py
  detail.py
  health.py
```

职责：

| 文件 | 职责 |
|---|---|
| `base.py` | Worker 生命周期、信号处理、主循环、异常捕获 |
| `heartbeat.py` | upsert `worker_heartbeats` |
| `locks.py` | Redis Profile lock 获取/释放/续租 |
| `scheduler.py` | 创建/维护 crawl job，后续调度 Listener |
| `listener.py` | Phase 2 占位执行器，领取任务后写测试事件 |
| `detail.py` | Phase 2 消费测试 raw tweet / web event，不做真实解析 |
| `health.py` | 检查 Worker、队列、Profile 锁、过期状态 |

Worker 统一行为：

- 启动时生成 `worker_id`，格式建议：`{worker_type}-{hostname}-{pid}`。
- 每 `WORKER_HEARTBEAT_INTERVAL_SECONDS` 秒写入一次心跳。
- 每轮主循环捕获异常并写入 `lgn:worker_events`。
- 收到 SIGTERM/SIGINT 时更新心跳状态为 `stopped`，释放已持有锁。
- 不使用 `while True` 裸循环，必须有 sleep/backoff。

### 6.3 Browser 模块

新增目录和文件：

```text
apps/api/app/browser/
  __init__.py
  profile_lock.py
  health_check.py
  playwright_adapter.py
```

Phase 2 先实现两层：

| 层 | 内容 |
|---|---|
| 无浏览器 fallback | 检查 profile path 是否存在、是否目录、权限是否可读 |
| Playwright health check | 可选；安装浏览器后打开 `X_LOGIN_CHECK_URL` 判断登录态 |

健康检查判断规则：

| 检查项 | 结果 |
|---|---|
| Profile 路径不存在 | `browser_profiles.status = error` |
| Profile 未绑定 monitoring account | 保持 `unregistered` 或返回配置错误 |
| 打开后跳转到 `/login` | `needs_login` |
| 页面出现 checkpoint/unlock/suspicious 文案 | `challenged` |
| 页面可见 Home/导航/账号菜单 | `available` |
| 浏览器启动失败 | `error` 并保存 artifact |

Phase 2 不要求健康检查百分百识别 Twitter/X 页面，只要求框架、状态写回和 artifact 链路可用。

## 7. API 规划

### 7.1 Workers API

新增：`apps/api/app/api/v1/workers.py`

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/workers` | 列出 Worker 心跳 |
| `GET` | `/api/v1/workers/summary` | 统计在线/离线 Worker 数量 |

在线判断：`updated_at >= now() - WORKER_OFFLINE_AFTER_SECONDS`。

### 7.2 Queues API

新增：`apps/api/app/api/v1/queues.py`

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/queues` | 列出所有 stream 的长度和 pending |
| `GET` | `/api/v1/dead-letter` | 查看死信消息 |
| `POST` | `/api/v1/dead-letter/{id}/retry` | Phase 2 可预留，不强制实现 |

### 7.3 Events API 和 SSE

新增：`apps/api/app/api/v1/events.py`

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/events/stream` | SSE 实时事件流 |
| `GET` | `/api/v1/events/recent` | 最近事件列表，默认 100 条 |
| `POST` | `/api/v1/events/test` | 写入测试事件，用于验证 SSE |

SSE 输出格式：

```text
event: tweet.new
id: 1710000000000-0
data: {"type":"tweet.new","payload":{...}}

event: heartbeat
data: {"ts":"2026-06-13T00:00:00Z"}
```

Phase 2 必须支持：

- 心跳事件，避免代理断开。
- 最近事件 replay，防止前端刷新丢失最新通知。
- 测试事件，从 API 写入 `lgn:web_events` 后前端立即收到。

### 7.4 Profile Health API

已有 Browser Profile 路由需要补齐动作接口：

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/v1/browser-profiles/{id}/health-check` | 触发单个 Profile 健康检查 |
| `POST` | `/api/v1/monitoring-accounts/{id}/check-login` | 检查该账号绑定 Profile 的登录态 |

Phase 2 可以同步执行，也可以入队后返回 job id。为了简单，优先同步执行路径检查，浏览器真实检查可切到异步 job。

## 8. 前端页面规划

### 8.1 Workers 页面

新增：`apps/web/src/features/workers/WorkersPage.tsx`

功能：

- 展示 Worker 类型、worker_id、状态、当前任务、最后心跳时间。
- 在线/离线用 Badge 标识。
- Dashboard 增加 Worker 在线摘要卡片跳转。

### 8.2 Queues 页面

新增：`apps/web/src/features/queues/QueuesPage.tsx`

功能：

- 展示 stream 名称、长度、pending 数、consumer group。
- 展示 dead letter 最近消息。
- 提供刷新按钮。

### 8.3 Events/Notifications 页面或组件

新增：

```text
apps/web/src/features/events/EventsPage.tsx
apps/web/src/hooks/useSseEvents.ts
```

功能：

- 连接 `/api/v1/events/stream`。
- 收到 `tweet.new`、`worker.status`、`account.status`、`test` 等事件后显示 toast。
- 页面展示最近事件列表。
- 提供“发送测试事件”按钮，调用 `/events/test`。

### 8.4 导航更新

在 `AppLayout.tsx` 增加：

- Workers：`/workers`
- Queues：`/queues`
- Events：`/events`

## 9. 数据库与迁移策略

Phase 2 优先不新增表，先复用现有：

| 表 | Phase 2 用途 |
|---|---|
| `worker_heartbeats` | Worker 状态展示 |
| `crawl_jobs` | 调度任务记录 |
| `browser_profiles` | 锁定者、锁定时间、健康检查时间、状态 |
| `monitoring_accounts` | 登录态检查时间、账号状态 |
| `artifacts` | 健康检查或 Worker 异常证据 |
| `web_events` | 最近事件持久化和 SSE replay |

如果实现过程中发现需要更完整状态，可新增一次小迁移：

| 字段 | 表 | 目的 |
|---|---|---|
| `error_message` | `browser_profiles` | 展示最近健康检查失败原因 |
| `rate_limited_until` | `monitoring_accounts` | 后续调度冷却 |
| `last_success_at` | `monitoring_accounts` | 最近成功使用时间 |
| `last_error_at` | `monitoring_accounts` | 最近失败时间 |

除非实现必须，否则 Phase 2 暂不增加这些字段，避免扩大迁移范围。

## 10. Profile 锁设计

### 10.1 Redis 锁

Key 格式：

```text
lgn:lock:browser_profile:{profile_id}
```

Value：

```json
{
  "worker_id": "listener-host-1234",
  "worker_type": "listener",
  "locked_at": "2026-06-13T00:00:00Z"
}
```

规则：

- 使用 `SET key value NX EX ttl` 获取锁。
- TTL 使用 `BROWSER_PROFILE_LOCK_TTL_SECONDS`。
- Worker 长任务时定期续租。
- 释放锁时只允许持有者释放，避免误删其他 Worker 的锁。
- Redis 锁是权威锁；数据库 `locked_by/locked_at/status` 用于展示。

### 10.2 数据库同步

获取锁成功后：

- `browser_profiles.status = in_use`
- `browser_profiles.locked_by = worker_id`
- `browser_profiles.locked_at = now()`

释放锁后：

- 如果健康状态正常，`status = available`
- `locked_by = null`
- `locked_at = null`

Health Worker 发现锁 TTL 已消失但数据库仍是 `in_use` 时，应自动修复为 `available` 或 `error`。

## 11. Scheduler 设计

Phase 2 Scheduler 的目标是验证调度闭环，不做复杂策略。

每轮执行：

1. 查询 `active` target accounts。
2. 查询 `active` monitoring accounts。
3. 查询 `available` browser profiles。
4. 跳过未绑定 monitoring account 的 profile。
5. 为每个 available profile 创建最多 1 个 `crawl_jobs` 测试任务。
6. 写入 `lgn:worker_events` 或 `lgn:crawl_jobs`。
7. 避免重复创建未完成任务。

Phase 2 调度频率：

```text
SCHEDULER_INTERVAL_SECONDS=15
LISTENER_MAX_PROFILES=1
```

验收时只需要看到 crawl job 从 `pending -> running -> completed/failed`。

## 12. Listener 占位设计

Phase 2 Listener 不做真实 Twitter/X 抓取，只验证 Worker 和 Profile 管线。

执行流程：

1. 领取一个 `pending` crawl job。
2. 获取该 job 关联的 Profile 锁。
3. 将 job 状态更新为 `running`。
4. 做轻量 profile path 检查。
5. 写入一个 `lgn:web_events` 测试事件。
6. 将 job 状态更新为 `completed`。
7. 释放 Profile 锁。

如果失败：

- job 标记为 `failed`。
- 写入 `lgn:dead_letter` 或 `lgn:worker_events`。
- 保存 error artifact。
- 释放锁。

## 13. Health Worker 设计

Health Worker 每轮执行：

| 检查项 | 动作 |
|---|---|
| Worker 心跳过期 | 在 API 展示为 offline，不一定写库 |
| Redis stream 长度 | 统计并写 worker heartbeat metadata |
| Redis pending | 统计并暴露给 Queues API |
| Profile 锁卡住 | Redis 锁不存在但 DB 仍 `in_use` 时修复 |
| Profile 路径异常 | 标记 `browser_profiles.status = error` |
| 最近事件持久化 | 保证 `web_events` 可供 replay |

Phase 2 不要求自动 reclaim pending 消息，但要把 pending 统计展示出来。

## 14. SSE 设计

### 14.1 事件类型

| 事件类型 | 用途 |
|---|---|
| `test` | 手动测试事件 |
| `worker.status` | Worker 启停、异常 |
| `account.status` | 账号或 Profile 状态变化 |
| `crawl.job` | crawl job 状态变化 |
| `tweet.new` | Phase 2 可用假数据，Phase 3 接真实推文 |
| `heartbeat` | SSE 保活 |

### 14.2 事件持久化

写入 `lgn:web_events` 时，同步或异步落库到 `web_events` 表：

| 字段 | 内容 |
|---|---|
| `event_type` | 事件类型 |
| `payload` | JSON payload |
| `stream_id` | Redis stream id |

Phase 2 允许先由 API 写库，Worker 写 Redis；后续统一成事件服务。

## 15. 配置项

需要确认 `.env.example` 包含或补齐：

```dotenv
STREAM_PREFIX=lgn
STREAM_MAX_RETRIES=5
STREAM_CONSUMER_BLOCK_MS=5000
STREAM_CONSUMER_BATCH_SIZE=10

WORKER_HEARTBEAT_INTERVAL_SECONDS=10
WORKER_OFFLINE_AFTER_SECONDS=30
SCHEDULER_INTERVAL_SECONDS=15
HEALTH_CHECK_INTERVAL_SECONDS=30

BROWSER_PROFILE_LOCK_TTL_SECONDS=300
BROWSER_HEADLESS=false
BROWSER_DEFAULT_TIMEOUT_MS=30000
BROWSER_PROFILE_HEALTH_CHECK_BROWSER_ENABLED=false

SSE_HEARTBEAT_SECONDS=15
SSE_REPLAY_RECENT_LIMIT=100
```

## 16. 实施顺序

### Step 1：Streams 基础

交付：

- `app.streams.names`
- `app.streams.client`
- stream group 初始化
- 单元级或脚本级验证 `XADD/XREADGROUP/XACK`

验收：

- 可以写入 `lgn:web_events`。
- 可以读取并 ACK。
- 可以查看 stream 长度。

### Step 2：Worker 基座和心跳

交付：

- `WorkerBase`
- heartbeat upsert
- `python -m app.workers.health` 可运行
- `python -m app.workers.scheduler` 可运行

验收：

- `worker_heartbeats` 出现记录。
- 停止 Worker 后 API 能判断 offline。

### Step 3：Workers API 和前端 Workers 页面

交付：

- `/api/v1/workers`
- `/api/v1/workers/summary`
- 前端 `/workers`

验收：

- 页面能显示 scheduler、health、listener、detail 的心跳。

### Step 4：Queues API 和前端 Queues 页面

交付：

- `/api/v1/queues`
- `/api/v1/dead-letter`
- 前端 `/queues`

验收：

- 页面能看到 `lgn:web_events`、`lgn:worker_events` 等 stream 长度。

### Step 5：SSE 和测试事件

交付：

- `/api/v1/events/stream`
- `/api/v1/events/recent`
- `/api/v1/events/test`
- 前端 SSE hook 和事件页面

验收：

- 点击“发送测试事件”后，前端收到 toast。
- 刷新页面后能看到最近事件。

### Step 6：Profile 锁

交付：

- Redis Profile lock
- DB `locked_by/locked_at/status` 同步
- Health Worker 修复 stale lock

验收：

- 同一 Profile 同时只能被一个 Worker 拿到。
- Worker 异常退出后 TTL 到期，Health Worker 能恢复状态。

### Step 7：Profile 健康检查框架

交付：

- `browser.health_check`
- `/browser-profiles/{id}/health-check`
- `/monitoring-accounts/{id}/check-login`
- artifacts 错误保存

验收：

- Profile 路径不存在时变为 `error`。
- Profile 路径存在时至少能完成基础检查。
- 浏览器真实检查可以通过配置开关启用，不阻塞 Phase 2 验收。

### Step 8：Scheduler -> Listener -> Event 闭环

交付：

- Scheduler 创建测试 crawl job。
- Listener 占位处理 job。
- Listener 写入 web event。
- SSE 推送到前端。

验收：

- crawl job 能从 `pending` 到 `completed`。
- Browser Profile 锁能正确获取和释放。
- 前端能收到 Listener 产生的测试事件。

## 17. 验收标准

Phase 2 完成标准：

- `docker compose up scheduler listener detail health` 不再因模块不存在而退出。
- Dashboard 或 Workers 页面能显示至少 4 类 Worker 的心跳状态。
- Queues 页面能显示 Redis Streams 长度和 pending 摘要。
- `/api/v1/events/test` 能触发前端 SSE toast。
- Browser Profile health check 能更新 `last_health_check_at` 和状态。
- 同一 Profile 的 Redis 锁能防止并发使用。
- Listener 占位任务能创建、运行、完成并释放锁。
- 失败任务能记录 error message，并至少写入 worker event 或 dead letter。

## 18. 测试计划

### 18.1 后端测试

建议命令：

```bash
cd apps/api
pytest
```

测试重点：

- Stream client 的 `XADD/XREADGROUP/XACK`。
- Worker heartbeat upsert 幂等。
- Redis lock 的获取、续租、释放、非持有者不可释放。
- Queues API 返回结构稳定。
- SSE test event 可被消费。

### 18.2 手工验收

1. 启动 postgres、redis、api、web。
2. 启动 scheduler、listener、detail、health。
3. 前端打开 Workers 页面，确认 Worker 在线。
4. 前端打开 Queues 页面，确认 stream 可见。
5. 前端打开 Events 页面，发送测试事件。
6. 添加一个不存在路径的 Browser Profile，执行 health check，确认状态变为 `error`。
7. 添加一个存在路径的 Browser Profile，执行 health check，确认 `last_health_check_at` 更新。
8. 触发 Scheduler 测试任务，确认 Listener 完成 job 并推送事件。

## 19. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| SSE 连接被代理断开 | 前端收不到事件 | 加 heartbeat，前端自动重连 |
| Redis pending 堆积 | 事件延迟 | Phase 2 展示 pending，Phase 3 再实现 reclaim |
| Worker 异常退出导致 DB 锁残留 | Profile 无法继续调度 | Redis TTL + Health Worker 修复 DB 状态 |
| 过早引入真实浏览器检查导致不稳定 | Phase 2 拖慢 | 浏览器检查做配置开关，默认先 path check |
| Profile 状态误判 | 调度错误 | 保守处理，疑似异常标记人工处理，不自动重登 |
| 事件重复推送 | 前端重复 toast | 使用 stream id / event id 去重 |

## 20. Phase 2 完成后的下一步

Phase 3 才进入真实 CloakBrowser 单 Profile PoC：

- Playwright/CloakBrowser adapter 稳定加载 Profile。
- 打开 `https://x.com/{username}` 或 X List 页面。
- 捕获 DOM/网络响应。
- 提取 tweet candidate。
- Detail Worker 去重入库。
- Latest Tweets 页面展示真实推文。
- 解析失败保存截图、HTML、raw payload。

Phase 2 的核心价值是确保 Phase 3 做真实浏览器采集时，已经有可靠的后台任务、锁、状态、事件和观测基础。
