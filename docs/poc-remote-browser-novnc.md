# Remote Browser / noVNC PoC

## 概述

Phase 2 的远程浏览器登录方案基于 noVNC，允许用户通过浏览器完成 X/Twitter 的登录验证。
这是一个文档化的概念验证，不是生产级实现。

## 架构

```
用户浏览器 → noVNC (web) → websockify → Xvfb + Chromium → X 登录页
```

## Docker Compose 服务定义 (PoC)

```yaml
# docker-compose.yml 中添加的 remote-browser 服务
remote-browser:
  image: theasp/novnc:latest
  ports:
    - "8080:8080"  # noVNC web 端口
  environment:
    - DISPLAY_WIDTH=1280
    - DISPLAY_HEIGHT=720
    - RUN_XVFB=yes
    - RUN_FLUXBOX=yes
    - RUN_NOVNC=yes
  volumes:
    - browser-data:/home/user/browser-profiles
  networks:
    - lgn-network
```

## Login Session 集成流程

1. 用户创建 Login Session (POST /api/v1/login-sessions)
   - 可选指定 browser_profile_id 和 monitoring_account_id
2. API 创建 session，状态变为 `pending`
3. 后端启动 remote-browser 容器 (或复用已有)
4. 更新 session 状态为 `running`，设置 `vnc_url`
5. 前端嵌入 noVNC iframe，用户操作浏览器完成 X 登录
6. 用户点击"完成登录"，前端调用 POST /api/v1/login-sessions/{id}/complete
7. 后端验证浏览器 cookies，提取登录状态
8. 绑定到 browser_profile + monitoring_account

## 安全注意事项

- noVNC 端口不应直接暴露到公网
- 生产环境需要添加 token 认证
- 每次 login session 应使用独立的浏览器实例
- 登录完成后应立即关闭 VNC 连接

## Phase 3 计划

- 基于 CloakBrowser/Playwright 的 headless 登录
- 不再依赖 noVNC 的人工操作
- 支持 CAPTCHA 检测和通知
- 自动化 cookie 提取和 session 绑定
