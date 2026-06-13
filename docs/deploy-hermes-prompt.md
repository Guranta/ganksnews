# Hermes Agent 部署提示词

将以下内容复制粘贴给服务器上的 Hermes Agent。

---

## 部署任务

在服务器上部署 LittleGankNews 项目。域名 `ganknews.886668.shop` 已指向本机。

### 第一步：拉取代码

```bash
cd /opt
git clone https://github.com/Guranta/ganksnews.git littleganknews
cd littleganknews
```

如果已有代码，`git pull` 到最新。

### 第二步：创建 .env

```bash
cp .env.production .env
# 修改 POSTGRES_PASSWORD 为一个强密码
nano .env
```

需要修改的字段：
- `POSTGRES_PASSWORD` — 改为强随机密码（同时 `DATABASE_URL` 里的密码也要改）
- 其他字段保持默认即可

### 第三步：创建存储目录

```bash
mkdir -p storage/postgres storage/redis storage/artifacts storage/profiles storage/logs
```

### 第四步：构建并启动

```bash
docker compose build
docker compose up -d
```

### 第五步：运行数据库迁移

```bash
docker compose exec api alembic upgrade head
```

### 第六步：验证

1. 检查所有容器运行中：`docker compose ps`
2. 访问健康检查：`curl http://localhost/api/v1/health` 应返回 `{"status": "healthy"}`
3. 访问前端：浏览器打开 `http://ganknews.886668.shop`
4. 测试 SSE：前端 Events 页面点"发送测试事件"

### 常用运维命令

```bash
# 查看日志
docker compose logs -f api
docker compose logs -f scheduler
docker compose logs -f listener

# 重启某个服务
docker compose restart api

# 更新代码后重新部署
git pull
docker compose build
docker compose up -d
docker compose exec api alembic upgrade head
```

### 注意事项

- 服务器内存 4GB，Docker 构建时可能需要 swap
- PostgreSQL 和 Redis 端口不对外暴露（仅容器间通信）
- 前端 nginx 监听 80 端口，通过 `/api/` 反代到后端
- Worker 服务（scheduler/listener/detail/health）后台运行，`restart: unless-stopped`
- SSE 需要nginx 关闭 buffering（已配置）
