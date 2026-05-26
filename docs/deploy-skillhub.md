# SkillHub 部署指南

这份文档面向的是 **SkillHub 网站** 的运行与部署，不是 `textbook2skill` CLI/skill 编译工具本身的使用说明。

如果你想做的是：

- 运行 SkillHub Web + API 应用
- 在本地启动开发环境
- 用 Compose 起后端依赖
- 理解 Render 配置与环境变量

请从这份文档开始。

## 系统组成

当前仓库里的 SkillHub 网站由这些部分组成：

- `apps/web`：Next.js 前端，浏览器只访问站内 `/api/*`
- `apps/api`：FastAPI 后端，提供认证、任务、技能、聊天与 `/health`
- `skeleton`：教材编译流水线与 LLM/OCR 逻辑
- `postgres`：生产/Compose 推荐数据库
- `redis`：预留给任务系统/缓存使用
- `storage`：PDF、任务产物、生成 skill 的持久化目录

## 当前运行模式

### 1. 本地开发模式

这是当前最推荐的开发方式。

- 前端和后端分别启动
- 数据库和 Redis 可以按需用 Compose 提供
- 如果只是调试基础页面和 API，后端默认 SQLite 也可以运行
- 当前 demo task 体系并不等同于“真实 Celery worker 集群”

推荐启动顺序：

1. 准备环境变量
2. 启动 API
3. 启动 Web
4. 如需 Postgres/Redis，再单独起 Compose 依赖

### 2. Docker Compose 模式

当前仓库的 [docker-compose.yml](../docker-compose.yml) 主要覆盖：

- `postgres`
- `redis`
- `api`
- `worker`

当前限制：

- **没有 `web` 服务**
- `worker` 命令仍是 Celery 风格入口，与当前 demo task 体系存在错位风险
- 更适合视为“后端基础依赖 + API 演示环境”，不是完整生产部署方案

### 3. Render 模式

仓库里已有 [render.yaml](../render.yaml)，它定义了：

- `skillhub-web`
- `skillhub-api`
- `skillhub-db`

当前特点：

- API 已配置 `/health` 作为健康检查
- Web 与 API 已经分服务
- 还没有独立 worker 服务定义
- 配置里的域名值是示例/实例值，落地时应改成你自己的服务地址

## 本地开发

### 前置依赖

- Python 3.11 或更高
- Node.js 20 或更高
- `qpdf`、`poppler-utils`
- 可选：Postgres、Redis

macOS：

```bash
brew install qpdf poppler
```

### 1. 准备环境变量

复制根级环境变量模板：

```bash
cp .env.example .env
```

如果你单独运行前端，也可以在 `apps/web` 下用 shell 导出变量，不要求额外的 `.env.local.example`。

### 2. 启动 API

```bash
cd apps/api
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

默认情况下：

- 未配置 `DATABASE_URL` 时，API 会退回到 `apps/api/storage/skillhub.db`
- 未配置 `REDIS_URL` 时，基础 API 仍可启动

### 3. 启动 Web

```bash
cd apps/web
npm ci
npm run dev
```

默认访问：

- Web: `http://127.0.0.1:3000`
- API: `http://127.0.0.1:8000`

### 4. 可选：只启动后端依赖

如果你想用 Postgres + Redis 做本地联调：

```bash
docker compose up -d postgres redis
```

然后在 `.env` 中把 `DATABASE_URL`、`REDIS_URL` 指向 Compose 服务。

## 环境变量

以下变量已经与当前代码实现对齐。

### 必填：认证与基础运行

- `JWT_SECRET`
  - 后端 JWT 签发与校验所需
- `CORS_ORIGINS`
  - 允许访问 API 的前端地址列表

### 必填或强烈建议：API / 存储

- `DATABASE_URL`
  - 生产建议显式配置
  - 本地未配置时默认回退到 SQLite
- `STORAGE_DIR`
  - 持久化目录
- `REDIS_URL`
  - 任务系统/缓存相关；本地可留空，生产建议配置

### 前端代理

- `SKILLHUB_API_BASE_URL`
  - Web 访问后端的公网/显式地址
- `SKILLHUB_API_HOSTPORT`
  - 仅适合容器/内网场景，例如 `api:8000`

这两个变量二选一即可：

- 外网或 Render/Vercel 类部署：优先 `SKILLHUB_API_BASE_URL`
- 容器内联通：可用 `SKILLHUB_API_HOSTPORT`

### LLM / OCR

- `DEEPSEEK_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `MINERU_TOKEN`

说明：

- 只要你实际使用对应提供商，才需要配置相应 key
- 扫描版 PDF 的 OCR 需要 `MINERU_TOKEN`

### 行为开关

- `DEFAULT_LLM_PROVIDER`
- `ALLOW_PARTIAL_SKILL`

### 其他

- `PUBLIC_BASE_URL`
  - 当前主要出现在部署配置中，不是本地开发必填
- `SKILLHUB_SESSION_SECRET`
  - 当前代码路径不依赖它；如果部署平台已有历史配置，可保留，但不是当前应用运行必需项

## 健康检查

当前后端提供最小健康检查：

- `GET /health`

返回：

```json
{"status":"ok"}
```

这表示：

- API 进程存活

这**不表示**：

- 数据库一定可连接
- Redis 一定可连接
- OCR/LLM key 一定完整
- Worker 一定可用

## Compose 与部署边界

当前需要特别注意：

- `docker-compose.yml` 还不是完整的全栈部署方案
- `worker` 定义更像历史/预留配置，不应直接视为当前稳定生产方案
- `render.yaml` 是目前最完整的部署描述，但仍需按你自己的域名与环境覆盖变量

## 相关文件

- 根入口：[README.md](../README.md)
- 环境变量模板：[.env.example](../.env.example)
- 前端说明：[apps/web/README.md](../apps/web/README.md)
- Render 配置：[render.yaml](../render.yaml)
- Compose 配置：[docker-compose.yml](../docker-compose.yml)
- API 配置：[config.py](../apps/api/app/config.py)
- API 健康检查：[main.py](../apps/api/app/main.py)
- 前端代理配置：[api-proxy.ts](../apps/web/src/lib/api-proxy.ts)

## 当前限制

- 没有独立的 readiness/liveness 检查
- 没有完整的全栈 Compose 方案
- 没有独立的 worker 部署说明
- 根 README 仍保留 `textbook2skill` 工具链主叙事

这些都属于后续迭代项；本次文档收敛的目标是先让“怎么启动网站”变得可读、可找、可执行。
