# LittleGankNews 开发与 Git 工作流

日期：2026-06-13

状态：当前执行规则

## 1. Git 远端

项目 GitHub 远端：

```text
https://github.com/Guranta/ganksnews.git
```

本地远端名称统一使用 `origin`。

## 2. 每一步都上传 Git

从当前阶段开始，每完成一个可验收步骤，都必须执行一次 Git 提交和推送。

“一步”的定义：

- 完成一个文档变更。
- 完成一个后端模块。
- 完成一个前端页面。
- 完成一个数据库迁移。
- 完成一次 bug 修复。
- 完成一次可独立验证的重构。

不要把多个互不相关的大改动堆到同一个提交里。

## 3. 标准提交流程

每一步完成后按以下顺序执行：

```bash
git status --short
```

提交前必须确认：

- 只 stage 本步骤相关文件。
- 不提交 `.env`、真实 token、cookies、Browser Profile、数据库文件、Redis 文件、artifacts、logs。
- 不提交 `node_modules/`、`dist/`、`.venv/`、`__pycache__/`。
- 不提交用户临时文件，除非明确属于项目交付物。

## 4. 提交信息格式

推荐格式：

```text
docs: add phase 2 worker plan
feat(api): add worker heartbeat endpoint
feat(web): add workers status page
fix(api): correct browser profile status update
chore: configure docker worker services
```

常用类型：

| 类型 | 用途 |
|---|---|
| `docs` | 文档变更 |
| `feat` | 新功能 |
| `fix` | bug 修复 |
| `chore` | 构建、配置、依赖、脚手架 |
| `refactor` | 不改变行为的重构 |
| `test` | 测试 |

## 5. 推送规则

默认推送到：

```bash
git push origin main
```

如果远端已有提交导致推送失败，先执行：

```bash
git pull --rebase origin main
```

解决冲突后再推送。不要使用 `git push --force`，除非用户明确要求。

## 6. 初始提交范围

当前仓库初始提交应包含项目工程文件：

- `.env.example`
- `.gitignore`
- `apps/`
- `docker/`
- `docker-compose.yml`
- `docs/`

根目录下历史 HTML 草稿文件是否提交，需要单独确认；默认不作为工程初始提交的一部分。

## 7. 文档优先规则

需求、架构或阶段边界发生变化时，必须先更新文档，再修改代码。

Phase 2 及后续每个步骤都要满足：

1. 文档或代码变更完成。
2. 能运行的检查已运行，或明确记录未运行原因。
3. Git 提交已创建。
4. 提交已推送到 GitHub。

## 8. 安全规则

绝不提交以下内容：

- `.env`
- Twitter/X 登录 cookies
- OpenAI token 或其他 API token
- CloakBrowser / Chromium Profile 目录
- PostgreSQL 数据目录
- Redis 数据目录
- screenshots、HTML artifacts、错误栈中包含敏感信息的文件

`.gitignore` 必须持续覆盖这些路径。
