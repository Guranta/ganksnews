# LittleGankNews 文档索引

本目录保存 Twitter/X 公开用户监控系统的需求、架构和实施计划。文档目标是让任何 Agent 或开发者无需依赖历史会话即可理解项目并继续推进。

## 文档地图

| 文档 | 说明 | 状态 |
|---|---|---|
| [development-workflow.md](development-workflow.md) | 开发与 Git 工作流，规定每完成一个可验收步骤都提交并推送到 GitHub | 当前执行 |
| [requirements.md](requirements.md) | 需求文档，基于 CloakBrowser 浏览器监听方案，描述 20-30 目标账号 Phase 1 需求 | 已更新 |
| [architecture.md](architecture.md) | 架构图，基于 CloakBrowser + Redis Streams + SSE 的浏览器监听架构 | 已更新 |
| [plans/2026-06-13-littleganknews-v1-implementation-plan.md](plans/2026-06-13-littleganknews-v1-implementation-plan.md) | 第一版详细实施计划，按 Linux 4GB 测试服务器、20-30 目标账号、Web Dashboard + SSE 优先落地 | 当前执行 |
| [plans/2026-06-13-phase2-worker-sse-profile-health-plan.md](plans/2026-06-13-phase2-worker-sse-profile-health-plan.md) | Phase 2 详细实施计划，覆盖 Redis Streams、Worker 基座、SSE、Profile 锁和健康检查状态机 | 待实施 |
| [plans/2026-06-13-twitter-browser-monitor-plan.md](plans/2026-06-13-twitter-browser-monitor-plan.md) | 早期浏览器监听方案背景参考 | 背景参考 |
| [research/dashboard-ui-recommendations.md](research/dashboard-ui-recommendations.md) | 前端 UI 技术栈调研 | 已确认 |

## 当前决策

- GitHub 远端使用 `https://github.com/Guranta/ganksnews.git`。
- 从当前阶段开始，每完成一个可验收步骤都必须提交并推送到 GitHub。
- 主链路舍弃 X API。
- 不使用 snscrape 作为主链路或备用链路。
- 使用 CloakBrowser / Playwright 持久化 Browser Profile 监听公开 Twitter/X 页面。
- Phase 1 先在普通 4GB Linux 服务器上测试 20-30 个目标账号。
- Phase 1 前端必须支持两类账号管理：被监控目标账号和用于登录监听的监控账号。
- Phase 1 告警优先做 Web Dashboard + SSE 实时通知，Telegram 仅预留后续扩展。
- 技术栈：Python 3.12, Node 22 LTS, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Redis Streams, Vite + React + TS, shadcn/ui + Tailwind CSS。

## 建议阅读顺序

1. 先读 [development-workflow.md](development-workflow.md)，了解每一步提交和推送规则。
2. 再读 [plans/2026-06-13-littleganknews-v1-implementation-plan.md](plans/2026-06-13-littleganknews-v1-implementation-plan.md)，了解当前最新执行方向。
3. 如果要继续实现后台任务系统，读 [plans/2026-06-13-phase2-worker-sse-profile-health-plan.md](plans/2026-06-13-phase2-worker-sse-profile-health-plan.md)。
4. 再读 [requirements.md](requirements.md)，了解 Phase 1 功能和非功能需求。
5. 再读 [architecture.md](architecture.md)，了解浏览器监听架构和数据流。
6. 最后读 [plans/2026-06-13-twitter-browser-monitor-plan.md](plans/2026-06-13-twitter-browser-monitor-plan.md)，了解早期浏览器监听方案背景。

## 文档维护规则

- 新增、删除、重命名文档时必须同步更新本索引。
- 实施计划放入 `docs/plans/`。
- 需求变更必须先更新文档，再修改代码。
- 文档进度与代码进度不一致时，先补齐文档再继续开发。
