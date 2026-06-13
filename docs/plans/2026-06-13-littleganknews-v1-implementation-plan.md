# LittleGankNews 第一版详细实施计划

日期：2026-06-13

状态：已确认，待实施

相关文档：

- [文档索引](../README.md)
- [开发与 Git 工作流](../development-workflow.md)
- [原始需求文档](../requirements.md)
- [原始架构图](../architecture.md)
- [早期浏览器监听计划](2026-06-13-twitter-browser-monitor-plan.md)
- [Phase 2 详细实施计划](2026-06-13-phase2-worker-sse-profile-health-plan.md)

## 1. 项目目标

LittleGankNews 第一版用于监控 Twitter/X 公开账号的新动态，面向 crypto/Web3 信息发现。系统不使用 X API v2，也不把 snscrape 作为主链路或备用链路，而是通过 CloakBrowser / Playwright 持久化浏览器 Profile 监听公开 Twitter/X 页面。

第一版先完成可运行、可管理、可观测的最小闭环：

- 在网页端管理被监控的 Twitter/X 目标账号。
- 在网页端管理用于登录和监听的 Twitter/X 监控账号。
- 在网页端登记和查看 CloakBrowser Browser Profile 状态。
- 使用 1 个已登录 Profile 监听 20-30 个公开目标账号。
- 发现新推文后写入 PostgreSQL。
- 前端 Latest Tweets 页面实时展示新推文。
- 使用 Web SSE 实时通知，先不做 Telegram。
- 保存解析失败、登录态异常、页面异常的 artifacts。
- 支持部署在普通 4GB Linux 测试服务器上。

## 2. 第一版边界

### 2.1 做什么

- 监控 20-30 个公开 Twitter/X 目标账号作为 Phase 1 测试规模。
- 支持后续逐步扩展到 100、500 个目标账号。
- 支持目标账号批量导入。
- 支持监听账号和 Browser Profile 的网页端登记、暂停、恢复、状态查看。
- 支持推文去重、入库、查询、搜索基础能力。
- 支持 Worker 心跳、Redis Stream 队列状态、错误证据查看。
- 支持网页端 SSE 实时通知。
- 预留 Telegram 表结构和接口扩展点，但 Phase 1 不实现 Telegram 发送。

### 2.2 不做什么

- 不使用 X API v2。
- 不使用 snscrape。
- 不破解验证码。
- 不绕过平台风控。
- 不采集私信、非公开账号或受限内容。
- 不承诺所有账号小于 1 分钟发现。
- Phase 1 不做关键词规则。
- Phase 1 不做情感分析、异常检测、多租户、复杂 RBAC。
- Phase 1 不做 Elasticsearch / OpenSearch。
- Phase 1 不做 noVNC 服务器登录界面。
- Phase 1 不做 Prometheus / Grafana，先用数据库心跳和前端健康页。

## 3. 已确认决策

| 类别 | 决策 |
|---|---|
| 部署目标 | Linux 服务器 |
| Phase 1 服务器 | 普通 4GB 服务器，优先小规模验证 |
| Phase 1 目标账号数量 | 20-30 个 |
| 数据源 | Twitter/X Web 页面 |
| 浏览器方案 | CloakBrowser + Playwright-compatible API |
| 登录态 | 持久化 Browser Profile |
| 监听账号登录 | Phase 1 支持手工登录 Profile 后复制到服务器；Phase 2B 规划 noVNC 服务器浏览器登录 |
| 后端 | FastAPI |
| ORM | SQLAlchemy 2.0 async |
| 迁移 | Alembic |
| 数据库 | PostgreSQL |
| 队列 | Redis Streams |
| 前端 | Vite + React + TypeScript |
| UI | shadcn/ui + Tailwind CSS |
| 表格 | TanStack Table |
| 请求状态 | TanStack Query |
| 图表 | Recharts |
| 实时通知 | Server-Sent Events |
| Phase 1 告警 | 只做网页端通知 |
| Artifacts | 本地文件系统 |

执行纪律：从当前阶段开始，每完成一个可验收步骤，都必须按 [开发与 Git 工作流](../development-workflow.md) 提交并推送到 GitHub 远端 `https://github.com/Guranta/ganksnews.git`。

## 4. 目标账号导入格式

第一版采用两种格式，优先支持纯文本，后续支持 CSV。

### 4.1 推荐格式：纯文本，一行一个 username

适合手动整理、最快导入、错误最少。

```text
VitalikButerin
cz_binance
a16zcrypto
binance
solana
```

导入规则：

- 可以带 `@`，系统自动去掉。
- 自动 trim 空格。
- 自动跳过空行。
- 自动按 username 去重。
- 默认 status 为 `active`。
- 默认 priority 为 `normal`。

### 4.2 扩展格式：CSV

适合后续管理标签和备注。

```csv
username,tags,notes
VitalikButerin,ethereum;kols,core account
cz_binance,exchange;kols,
a16zcrypto,vc;research,
```

CSV 字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| username | 是 | Twitter/X username，可带或不带 `@` |
| tags | 否 | 分号分隔标签 |
| notes | 否 | 备注 |

Phase 1 前端先做纯文本粘贴导入；CSV 可同阶段实现，但不阻塞主链路。

## 5. 总体架构

```mermaid
flowchart LR
    subgraph Web[Frontend]
        UI[Vite React Dashboard]
        SSEClient[SSE Client]
    end

    subgraph API[Backend]
        FastAPI[FastAPI REST API]
        SSE[SSE Endpoint]
    end

    subgraph Workers[Workers]
        Scheduler[Scheduler]
        Listener[CloakBrowser Listener]
        Detail[Detail Worker]
        Health[Health Worker]
    end

    subgraph Queue[Redis Streams]
        RawTweets[(raw_tweets)]
        DetailJobs[(tweet_detail_jobs)]
        WebEvents[(web_events)]
        DeadLetter[(dead_letter)]
    end

    subgraph Storage[Storage]
        PG[(PostgreSQL)]
        Redis[(Redis)]
        Profiles[(Browser Profiles)]
        Artifacts[(Artifacts)]
    end

    X[Twitter/X Web]

    UI --> FastAPI
    SSEClient --> SSE
    FastAPI --> PG
    FastAPI --> Redis
    Scheduler --> PG
    Listener --> Profiles
    Listener --> X
    Listener --> RawTweets
    RawTweets --> Detail
    Detail --> PG
    Detail --> WebEvents
    Detail --> Artifacts
    WebEvents --> SSE
    Health --> PG
    Health --> Redis
    DeadLetter --> FastAPI
```

## 6. 推荐目录结构

```text
littleganknews/
  apps/
    api/
      app/
        main.py
        core/
        models/
        schemas/
        api/v1/
        services/
        repositories/
        workers/
        browser/
        streams/
        artifacts/
      alembic/
      alembic.ini
      pyproject.toml
    web/
      src/
        app/
        components/
        features/
        lib/
      package.json
      vite.config.ts
  docker/
    api.Dockerfile
    web.Dockerfile
    worker.Dockerfile
  storage/
    artifacts/
    profiles/
  docs/
  docker-compose.yml
  .env.example
  README.md
```

## 7. 数据库表规划

Phase 1 建立核心表，字段可以随实现细化，但必须保持迁移可追踪。

| 表 | 用途 | Phase 1 |
|---|---|---|
| `target_accounts` | 被监控 Twitter/X 目标账号 | 必做 |
| `target_account_import_batches` | 批量导入记录 | 必做 |
| `monitoring_accounts` | 用于登录监听的 Twitter/X 账号 | 必做 |
| `browser_profiles` | CloakBrowser Profile 元数据 | 必做 |
| `monitor_lists` | Twitter/X List 或内部监听集合 | 必做 |
| `monitor_list_memberships` | 目标账号与 List 映射 | 必做 |
| `tweets` | 推文主表 | 必做 |
| `tweet_media` | 图片、视频、链接等媒体 | 可简化 |
| `tweet_metric_snapshots` | 点赞、转发、回复等指标快照 | 可简化 |
| `worker_heartbeats` | Worker 心跳 | 必做 |
| `crawl_jobs` | 监听、详情、检查任务 | 必做 |
| `artifacts` | 截图、HTML、raw payload、错误栈 | 必做 |
| `web_events` | Web 实时事件记录 | 必做 |
| `notification_channels` | 通知渠道预留 | 可建表不启用 |
| `alert_rules` | 告警规则预留 | 可建表不启用关键词 |
| `alert_events` | 告警事件预留 | 可建表不启用 Telegram |

关键约束：

```sql
unique(platform, username)      -- target_accounts
unique(platform, username)      -- monitoring_accounts
unique(profile_path)            -- browser_profiles
unique(platform, tweet_id)      -- tweets
unique(monitor_list_id, target_account_id)
```

## 8. API 规划

API 前缀：`/api/v1`

| 模块 | 接口 |
|---|---|
| Health | `GET /health`, `GET /health/ready` |
| Dashboard | `GET /dashboard/summary` |
| Target Accounts | `GET/POST /target-accounts`, `POST /target-accounts/import`, `PATCH/DELETE /target-accounts/{id}` |
| Monitoring Accounts | `GET/POST /monitoring-accounts`, `PATCH/DELETE /monitoring-accounts/{id}`, `POST /monitoring-accounts/{id}/check-login` |
| Browser Profiles | `GET/POST /browser-profiles`, `PATCH /browser-profiles/{id}`, `POST /browser-profiles/{id}/health-check` |
| Monitor Lists | `GET/POST /monitor-lists`, `GET/POST /monitor-lists/{id}/members` |
| Tweets | `GET /tweets/latest`, `GET /tweets/{id}`, `POST /tweets/search` |
| Events | `GET /events/stream`, `GET /events/recent`, `POST /events/test` |
| Workers | `GET /workers` |
| Queues | `GET /queues`, `GET /dead-letter` |
| Artifacts | `GET /artifacts`, `GET /artifacts/{id}`, `GET /artifacts/{id}/content` |

## 9. Redis Streams 规划

| Stream | 用途 |
|---|---|
| `lgn:raw_tweets` | Listener 产生的新推文候选 |
| `lgn:tweet_detail_jobs` | 详情补全任务 |
| `lgn:web_events` | 前端 SSE 事件 |
| `lgn:account_events` | 登录态、账号异常事件 |
| `lgn:worker_events` | Worker 状态事件 |
| `lgn:dead_letter` | 多次失败后的死信 |

处理原则：

- Consumer group 消费。
- 数据库唯一约束作为最终去重保护。
- 成功入库后再 `XACK`。
- 多次失败进入 dead letter。
- Pending 消息后续支持 reclaim。

## 10. Worker 规划

### 10.1 Scheduler

- 读取 active 目标账号、监听账号、Browser Profile 和 List 配置。
- 给 Listener 分配任务。
- 维护 Profile 独占锁。
- 检查过期任务和异常状态。

### 10.2 Listener Worker

- 使用 CloakBrowser / Playwright 加载指定 Profile。
- 打开 Twitter/X List 或 timeline 页面。
- 捕获 DOM 变化或网络响应。
- 提取推文候选并写入 `lgn:raw_tweets`。
- 检测登录失效、验证码、页面异常。
- 保存 screenshot、HTML、错误栈到 artifacts。

Phase 1 限制：

- 1 个 Listener。
- 1 个 Profile。
- 1 个 List 或 20-30 个目标账号相关页面。
- 避免高频刷新。

### 10.3 Detail Worker

- 消费 `lgn:raw_tweets`。
- 按 `tweet_id` 去重。
- 补全文本、URL、作者、发布时间、基础指标。
- 写入 `tweets`。
- 写入 `lgn:web_events` 触发前端通知。

### 10.4 Health Worker

- 写入 Worker 心跳。
- 检查 Worker 是否离线。
- 检查队列长度和 pending。
- 检查 Profile 是否卡在 `in_use`。

### 10.5 Fallback Poller

Phase 1 不强制实现。等 Listener 单链路跑通后再做低频补漏。

## 11. 前端页面规划

使用 shadcn/ui，风格简洁、清晰、适合管理台。

| 页面 | 功能 |
|---|---|
| Dashboard | 汇总卡片、今日推文、Worker 在线、队列状态、账号异常 |
| Target Accounts | 目标账号新增、批量粘贴导入、暂停、恢复、删除、搜索 |
| Monitoring Accounts | 监听账号新增、状态查看、标记需要登录、检查登录态 |
| Browser Profiles | Profile 路径登记、绑定监听账号、状态查看、健康检查 |
| Monitor Lists | List 配置、成员管理 |
| Latest Tweets | 最新推文流、按账号/时间/关键词过滤，SSE 实时插入 |
| Workers | Worker 心跳、状态、当前任务 |
| Queues | Redis Stream 长度、pending、dead letter |
| Artifacts | 查看错误截图、HTML、raw payload、错误栈 |
| Settings | 系统设置、SSE 测试、Telegram 预留 |

Phase 1 必须完成：Dashboard、Target Accounts、Monitoring Accounts、Browser Profiles、Latest Tweets、Workers、Queues。

## 12. 账号和 Profile 工作流

### 12.1 目标账号导入

1. 打开 Target Accounts 页面。
2. 粘贴一行一个 username 的文本。
3. 后端标准化 username。
4. 后端 upsert 到 `target_accounts`。
5. 前端显示新增、更新、失败数量。
6. Scheduler 后续把 active 目标账号纳入监听计划。

### 12.2 监听账号和 Profile 准备

1. 在安全机器上启动 CloakBrowser。
2. 创建 Profile。
3. 手工登录 Twitter/X 监听账号。
4. 确认可以访问目标页面或 X List。
5. 关闭浏览器，确保 Profile 落盘。
6. 将 Profile 目录复制到 Linux 服务器 `storage/profiles/`。
7. 在 Monitoring Accounts 页面新增监听账号元数据。
8. 在 Browser Profiles 页面登记 Profile 路径并绑定监听账号。
9. 点击 health check。
10. Worker 验证可用后状态变为 `available`。

## 13. 4GB Linux Phase 1 资源策略

普通 4GB 服务器先做测试，不追求 500 账号规模。

建议配置：

| 项 | Phase 1 设置 |
|---|---:|
| 目标账号 | 20-30 |
| 监听账号 | 1 |
| Browser Profile | 1 |
| Listener Worker | 1 |
| Detail Worker | 1 |
| Health Worker | 1 |
| Scheduler | 1 |
| PostgreSQL | 1 容器 |
| Redis | 1 容器 |
| 浏览器并发 | 1 Profile |

限制：

- 不开启多浏览器并发。
- 不做 500 账号扩容测试。
- 不开启 Grafana/Prometheus。
- Artifacts 设置保留天数，避免磁盘爆满。
- 前端查询默认分页，避免大列表一次性加载。

## 14. Docker 服务规划

Phase 1 服务：

```text
postgres
redis
api
web
scheduler
listener
detail
health
```

建议宿主机目录：

```text
/opt/littleganknews/
  .env
  docker-compose.yml
  storage/
    postgres/
    redis/
    artifacts/
    profiles/
    logs/
```

## 15. 环境变量规划

`.env.example` 至少包含：

```dotenv
APP_NAME=LittleGankNews
APP_ENV=development
LOG_LEVEL=INFO

API_HOST=0.0.0.0
API_PORT=8000
API_CORS_ORIGINS=http://localhost:5173
API_AUTH_ENABLED=false

WEB_PORT=5173
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SSE_URL=http://localhost:8000/api/v1/events/stream

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=littleganknews
POSTGRES_USER=littleganknews
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+asyncpg://littleganknews:change-me@postgres:5432/littleganknews

REDIS_URL=redis://redis:6379/0

ARTIFACTS_DIR=/app/storage/artifacts
BROWSER_PROFILES_DIR=/app/storage/profiles
ARTIFACT_RETENTION_DAYS=14

BROWSER_PROVIDER=cloakbrowser
BROWSER_HEADLESS=false
BROWSER_DEFAULT_TIMEOUT_MS=30000
BROWSER_PROFILE_LOCK_TTL_SECONDS=300

WORKER_HEARTBEAT_INTERVAL_SECONDS=10
SCHEDULER_INTERVAL_SECONDS=15
LISTENER_MAX_PROFILES=1
DETAIL_WORKER_CONCURRENCY=1
FALLBACK_POLLER_ENABLED=false

X_BASE_URL=https://x.com
X_LOGIN_CHECK_URL=https://x.com/home
X_LISTEN_MODE=list

STREAM_PREFIX=lgn
STREAM_MAX_RETRIES=5

SSE_HEARTBEAT_SECONDS=15
SSE_REPLAY_RECENT_LIMIT=100

TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_DEFAULT_CHAT_ID=
```

## 16. 实施阶段

### Phase 0：文档与工程准备

交付物：

- 本计划文档。
- 更新 `docs/README.md`。
- 后续更新 `docs/requirements.md` 和 `docs/architecture.md`。
- `.env.example`。
- 基础目录结构。
- Docker Compose 草案。

验收标准：

- 当前技术路线明确为浏览器监听。
- Phase 1 明确为 Web Dashboard + SSE。
- Telegram 明确为后续预留。

### Phase 1：基础后端、数据库、前端管理台

交付物：

- FastAPI 可运行。
- PostgreSQL + Redis 可运行。
- Alembic 初始迁移。
- 目标账号、监听账号、Profile API。
- 前端可导入目标账号、登记监听账号、登记 Profile。

验收标准：

- 能从前端导入 20-30 个目标账号。
- 能从前端登记 1 个监听账号和 1 个 Profile。
- Dashboard 能显示基础统计。

### Phase 2：队列、Worker、SSE

详细计划见：[Phase 2 Worker / SSE / Profile Health / noVNC Login 详细实施计划](2026-06-13-phase2-worker-sse-profile-health-plan.md)。

交付物：

- Redis Streams 封装。
- Worker heartbeat。
- Scheduler / Health Worker。
- SSE `/events/stream`。
- 前端通知中心。
- Profile lock 和健康检查。
- Login Session API。
- noVNC 服务器浏览器登录会话，用于生成 Browser Profile。

验收标准：

- Worker 状态可在前端查看。
- 队列状态可在前端查看。
- 测试事件可通过 SSE 推送到前端。

### Phase 3：CloakBrowser 单 Profile PoC

交付物：

- Browser Profile 加载。
- 登录态检查。
- Listener Worker 打开 X 页面。
- 推文候选提取。
- Detail Worker 入库。
- Latest Tweets 页面实时显示。

验收标准：

- 1 个 Profile 可打开 X 页面。
- 至少能提取并入库推文候选。
- 前端能看到新推文。
- 新推文可触发 SSE。
- 异常时有 artifact。

### Phase 4：20-30 目标账号连续测试

交付物：

- 导入 20-30 个目标账号。
- 连续运行 24-72 小时。
- 记录发现延迟、队列积压、解析失败、账号状态。

验收标准：

- 不重复入库同一 tweet。
- Worker 崩溃后可重启。
- 登录失效、解析失败可在前端定位。
- 形成是否扩展到 100 账号的运行结论。

## 17. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| X 页面结构变化 | 解析失败或漏抓 | 保存截图、HTML、raw payload，parser 版本化 |
| 4GB 内存不足 | 浏览器崩溃或系统变慢 | Phase 1 只跑 1 Profile，限制并发 |
| 登录态失效 | Listener 停止采集 | 标记 `needs_login`，前端提示人工处理 |
| 风控或验证码 | 账号不可用 | 不绕过，标记 `challenged`，人工处理 |
| Profile 复制后不可用 | 无法启动监听 | 做 health check，保留 artifacts |
| Redis pending 堆积 | 推文延迟 | 重试、dead letter、增加消费者 |
| PostgreSQL 查询变慢 | 前端卡顿 | 分页、索引、限制默认时间范围 |
| Artifacts 泄露敏感信息 | 安全风险 | 脱敏、限制目录权限、不提交 git |

## 18. 开放问题

- CloakBrowser 在 Linux 上的具体安装和 Playwright 连接方式需要 Phase 3 验证。
- 第一批 20-30 个目标账号名单待准备。
- 第一批监听账号待准备。
- Phase 1 是否部署公网。如果公网访问，需要至少增加基础鉴权或反向代理保护。

## 19. 立即执行顺序

1. 写入本计划文档。
2. 更新 `docs/README.md`。
3. 更新 `docs/requirements.md`，废弃 X API / snscrape 当前方案。
4. 更新 `docs/architecture.md`，改为浏览器监听架构。
5. 创建工程骨架。
6. 创建 `.env.example`。
7. 创建 Docker Compose。
8. 实现 FastAPI + Alembic + PostgreSQL + Redis。
9. 实现账号/Profile 管理 API。
10. 实现前端管理页面。
11. 实现 Redis Streams、Worker heartbeat、SSE。
12. 做 CloakBrowser 单 Profile PoC。
13. 跑 20-30 账号 Phase 1 测试。
