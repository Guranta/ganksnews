# LittleGankNews 架构图

## 1. 总体架构

```mermaid
flowchart LR
    subgraph Web[Frontend]
        UI[Vite React Dashboard]
        SSEClient[SSE Client]
        LatestTweets[Latest Tweets UI]
        LoginUI[Login Session UI]
    end

    subgraph API[Backend]
        FastAPI[FastAPI REST API]
        SSE[SSE Endpoint]
        LoginSessions[Login Sessions API]
    end

    subgraph RemoteBrowser[Remote Browser Login]
        NoVNC[noVNC]
        Xvfb[Xvfb]
        LoginBrowser[Chromium/CloakBrowser]
    end

    subgraph Workers[Workers]
        Scheduler[Scheduler]
        Listener[CloakBrowser Listener]
        Detail[Detail Worker]
        Health[Health Worker]
    end

    subgraph Queue[Redis Streams]
        RawTweets[(lgn:raw_tweets)]
        DetailJobs[(lgn:tweet_detail_jobs)]
        WebEvents[(lgn:web_events)]
        AccountEvents[(lgn:account_events)]
        WorkerEvents[(lgn:worker_events)]
        DeadLetter[(lgn:dead_letter)]
    end

    subgraph Storage[Storage]
        PG[(PostgreSQL)]
        Redis[(Redis)]
        Profiles[(Browser Profiles)]
        Artifacts[(Artifacts)]
    end

    X[Twitter/X Web]

    UI --> FastAPI
    LatestTweets --> FastAPI
    SSEClient --> SSE
    LoginUI --> LoginSessions
    FastAPI --> PG
    FastAPI --> Redis
    LoginSessions --> NoVNC
    NoVNC --> Xvfb
    Xvfb --> LoginBrowser
    LoginBrowser --> X
    LoginBrowser --> Profiles
    Scheduler --> PG
    Listener --> Profiles
    Listener --> X
    Listener --> RawTweets
    RawTweets --> Detail
    Detail --> PG
    Detail --> WebEvents
    Detail --> Artifacts
    WebEvents --> SSE
    SSE --> LatestTweets
    Health --> PG
    Health --> Redis
    DeadLetter --> FastAPI
```

## 2. Listener Worker 数据流

```mermaid
sequenceDiagram
    autonumber
    participant S as Scheduler
    participant L as Listener Worker
    participant B as CloakBrowser Profile
    participant X as Twitter/X Web
    participant Q as lgn:raw_tweets
    participant D as Detail Worker
    participant DB as PostgreSQL
    participant SSE as SSE Endpoint
    participant LT as Latest Tweets Page
    participant UI as Frontend

    S->>L: 分配目标账号 + Profile
    L->>B: 加载 Browser Profile
    L->>X: 打开目标页面 / X List
    X-->>L: DOM 变化 / 网络响应
    L->>L: 提取推文候选
    L->>Q: 写入 raw_tweets
    Q->>D: 消费推文事件
    D->>D: 按 tweet_id 去重
    D->>DB: 写入推文
    D->>SSE: 写入 web_events
    SSE-->>UI: 实时推送新推文
    SSE-->>LT: tweet.new 实时插入列表顶部
```

## 3. 账号与 Profile 工作流

```mermaid
flowchart TD
    Manual[手工登录 CloakBrowser] --> Copy[复制 Profile 到服务器 storage/profiles/]
    Copy --> Register[Monitoring Accounts 页面登记监听账号]
    Register --> Bind[Browser Profiles 页面登记 Profile 并绑定监听账号]
    Bind --> HealthCheck[Health Check 验证可用]
    HealthCheck -->|可用| Available[状态变为 available]
    HealthCheck -->|不可用| NeedsLogin[状态变为 needs_login，前端提示人工处理]

    WebLogin[Monitoring Accounts 点击服务器浏览器登录] --> CreateSession[创建 Login Session]
    CreateSession --> RemoteBrowser[打开 noVNC 远程浏览器]
    RemoteBrowser --> LoginX[用户登录 Twitter/X]
    LoginX --> Complete[用户点击我已完成登录]
    Complete --> LoginHealth[Health Check 验证登录态]
    LoginHealth -->|可用| CreateProfile[创建 Monitoring Account 并绑定 Browser Profile]
    LoginHealth -->|不可用| LoginIssue[标记 needs_login / challenged / error]

    Import[Target Accounts 页面粘贴导入] --> Upsert[后端 upsert 到 target_accounts]
    Upsert --> Active[状态为 active，纳入监听计划]
```

服务器浏览器登录是 Phase 2B 目标能力。MVP 同一时间只允许 1 个 login session，noVNC 必须通过短期 token 和受保护反向代理访问，禁止裸露 VNC 或 Chrome remote debugging 端口。

## 4. Worker 架构

```mermaid
flowchart TB
    Scheduler[Scheduler\n读取 active 目标账号\n分配任务\n维护 Profile 独占锁] --> Listener[Listener Worker\nCloakBrowser 加载 Profile\n打开 X 页面\n提取推文候选]
    Listener --> RawTweets[(lgn:raw_tweets)]
    RawTweets --> Detail[Detail Worker\n去重\n补全推文信息\n写入数据库]
    Detail --> WebEvents[(lgn:web_events)]
    Detail --> Artifacts[Artifacts 存储]

    Health[Health Worker\nWorker 心跳检查\n队列长度检查\nProfile 状态检查] --> PG[(PostgreSQL)]
    Health --> Redis[(Redis)]

    DeadLetter[(lgn:dead_letter)] --> API[FastAPI]
```

## 5. 部署拓扑

```mermaid
flowchart TB
    subgraph Server[4GB Linux 服务器]
        subgraph Docker[Docker Compose]
            PG[(PostgreSQL)]
            Redis[(Redis)]
            API[FastAPI API]
            Web[Vite React Dashboard]
            RemoteBrowser[Remote Browser
Xvfb + noVNC + Chromium]
            Scheduler[Scheduler]
            Listener[Listener Worker]
            Detail[Detail Worker]
            HealthWorker[Health Worker]
        end

        subgraph Storage[本地存储]
            Profiles[storage/profiles/\nBrowser Profiles]
            Artifacts[storage/artifacts/\n截图 HTML 错误栈]
            Logs[storage/logs/]
        end
    end

    X[Twitter/X Web]

    User[管理员] --> Web
    Web --> API
    Web --> RemoteBrowser
    API --> PG
    API --> Redis
    Listener --> X
    Listener --> Profiles
```

## 6. 核心模块职责

| 模块 | 职责 | 关键点 |
|------|------|--------|
| FastAPI API | REST API + SSE，账号/Profile/推文管理 | CRUD + 批量导入 + SSE 推送 |
| Latest Tweets UI | 展示最新入库推文 | `/tweets` 页面，SSE `tweet.new` 实时插入 |
| Login Sessions API | 创建服务器远程浏览器登录会话 | noVNC 短期 token、完成/取消、状态事件 |
| Remote Browser | 提供服务器侧可交互浏览器 | Xvfb + noVNC + Chromium/CloakBrowser，MVP 单会话 |
| Scheduler | 读取配置，给 Listener 分配任务 | Profile 独占锁、过期任务检查 |
| Listener Worker | CloakBrowser 加载 Profile，打开 X 页面，提取推文 | DOM 监听、网络响应捕获、登录失效检测 |
| Detail Worker | 消费 raw_tweets，去重，补全信息，入库 | tweet_id 去重 + 数据库唯一约束 |
| Health Worker | Worker 心跳检查、队列长度检查、Profile 状态检查 | 标记离线 Worker、卡死 Profile |
| Redis Streams | 解耦采集、处理、通知 | Consumer group + ACK + dead letter |
| PostgreSQL | 推文、账号、配置、心跳持久化 | Alembic 迁移、唯一约束去重 |
| Artifacts | 保存截图、HTML、raw payload、错误栈 | 保留天数限制、不提交 git |

## 7. Redis Streams 规划

| Stream | 用途 | 生产者 | 消费者 |
|--------|------|--------|--------|
| `lgn:raw_tweets` | Listener 产生的新推文候选 | Listener | Detail Worker |
| `lgn:tweet_detail_jobs` | 详情补全任务 | Scheduler | Detail Worker |
| `lgn:web_events` | 前端 SSE 事件 | Detail Worker | SSE Endpoint |
| `lgn:account_events` | 登录态、账号异常事件 | Listener/Health | API/前端 |
| `lgn:worker_events` | Worker 状态事件 | All Workers | Health Worker |
| `lgn:dead_letter` | 多次失败后的死信 | All Consumers | API/前端 |

处理原则：

- Consumer group 消费。
- 数据库唯一约束作为最终去重保护。
- 成功入库后再 `XACK`。
- 多次失败进入 dead letter。
- Pending 消息后续支持 reclaim。

## 8. 数据库核心表

| 表 | 用途 |
|---|---|
| `target_accounts` | 被监控 Twitter/X 目标账号 |
| `target_account_import_batches` | 批量导入记录 |
| `monitoring_accounts` | 用于登录监听的 Twitter/X 账号 |
| `browser_profiles` | CloakBrowser Profile 元数据 |
| `login_sessions` | 服务器远程浏览器登录会话，保存 noVNC 登录流程状态 |
| `monitor_lists` | Twitter/X List 或内部监听集合 |
| `monitor_list_memberships` | 目标账号与 List 映射 |
| `tweets` | 推文主表 |
| `tweet_media` | 图片、视频、链接等媒体 |
| `tweet_metric_snapshots` | 点赞、转发、回复等指标快照 |
| `worker_heartbeats` | Worker 心跳 |
| `crawl_jobs` | 监听、详情、检查任务 |
| `artifacts` | 截图、HTML、raw payload、错误栈 |
| `web_events` | Web 实时事件记录 |
| `notification_channels` | 通知渠道预留 |
| `alert_rules` | 告警规则预留 |
| `alert_events` | 告警事件预留 |

---

## 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-06-13 | 初始版本（X API + snscrape 方案） | - |
| v2.0 | 2026-06-13 | 全面改为 CloakBrowser 浏览器监听架构，移除 X API / snscrape 路线，对齐 V1 实施计划 | - |
| v2.1 | 2026-06-13 | 补充 Phase 2B 服务器远程浏览器登录架构，使用 noVNC 登录会话生成 Browser Profile | - |
| v2.2 | 2026-06-13 | 明确 Latest Tweets 页面和 Tweets API 为推文展示入口，SSE `tweet.new` 实时插入 | - |
