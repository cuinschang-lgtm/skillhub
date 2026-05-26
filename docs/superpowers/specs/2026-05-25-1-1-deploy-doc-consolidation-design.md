# SkillHub 1-1 部署文档与环境变量收敛设计

## 背景

当前仓库已经具备 Web、API、任务执行、存储与数据库等多组件运行能力，但部署相关信息分散在多个位置：

- 根 `README.md` 仍以 `textbook2skill` 工具链叙事为主
- `apps/web/README.md` 仍是 Next.js 模板内容
- `.env.example` 只包含少量变量，无法支撑完整启动
- `docker-compose.yml`、`render.yaml`、`apps/api/app/config.py`、`apps/web/src/lib/api-proxy.ts` 分别持有不同的运行信息
- 后端虽然已有 `/health`，但部署文档没有把启动顺序、变量映射和运行模式说清楚

这会导致两个实际问题：

- 新开发者很难判断“SkillHub 网站”应该如何本地启动和部署
- 变量名、运行模式和文档入口不一致，容易造成错误配置

## 目标

- 为 SkillHub 网站提供单一、明确的部署入口文档
- 补全环境变量模板，使本地开发和基础部署不再依赖读源码猜配置
- 收敛本地开发、Compose 部署、Render 部署的说明关系
- 明确 Web / API / Worker / 数据库 / Redis 的职责与启动顺序
- 明确健康检查入口与当前能力边界

## 非目标

- 不在本次重构运行时架构
- 不在本次引入新的部署平台
- 不把 demo task 体系改造成真正 Celery 集群
- 不在本次新增数据库迁移系统
- 不在本次实现更强的 `/ready` / `/live` 检查
- 不在本次大改根 README 的全部产品叙事，只做部署入口收敛

## 已确认事实

- 根 `README.md` 更偏向 skill 工具链使用，而非 SkillHub Web 部署入口
- `apps/web/README.md` 基本没有实际部署价值
- 根 `.env.example` 缺失 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET`、`STORAGE_DIR`、前端 API 地址等关键变量
- `docker-compose.yml` 没有 `web` 服务，且 `worker` 命令与当前 demo task 体系存在错位风险
- `render.yaml` 是当前最接近“可部署描述”的文件，但没有成为显式文档入口
- 后端已有最小 `/health`，但没有更细的 readiness/liveness 检查

## 设计原则

- 文档先于重构：先把当前真实运行方式说清楚，再考虑后续架构演进
- 单一入口：部署说明应有一个主入口，其他文档只做引用
- 贴近现状：文档必须与当前代码行为一致，不编造尚未存在的能力
- 明确边界：区分“已支持”“部分支持”“未支持”
- 最小改动：优先收敛说明和模板，不扩展到系统级重构

## 方案选择

本次采用以下方案：

- 新增一份面向 SkillHub 网站的部署主文档
- 补全根 `.env.example`，把当前运行所需变量按 Web / API / Worker 分类说明
- 让根 `README.md` 增加清晰的“网站部署入口”指引
- 把 `apps/web/README.md` 从模板内容改成指向主文档的轻量说明
- 在文档中明确 Compose / Render 的现状能力与限制

不采用以下方案：

- 不直接重写整份根 `README.md` 为运维手册，因为仓库仍同时承载工具链说明
- 不在本次先修 Compose 运行逻辑，再反推文档，因为当前问题首先是入口混乱
- 不新增第二份独立的 Web `.env.local.example`，优先把根级模板收敛完整

## 交付物设计

### 部署主文档

新增一份部署主文档，建议路径：

- `docs/deploy-skillhub.md`

该文档应覆盖：

- 系统组成：Web / API / Worker / Postgres / Redis / Storage
- 运行模式说明：
  - 本地开发模式
  - Compose 模式
  - Render 模式
- 启动顺序
- 环境变量说明
- 健康检查说明
- 当前限制与已知不一致项

### 根 README 入口收敛

根 `README.md` 不做全量重写，但应新增一个明显可见的入口区块：

- 说明当前仓库既包含 skill 工具链，也包含 SkillHub 网站
- 对“想部署网站”的用户直接指向 `docs/deploy-skillhub.md`
- 避免用户继续把 CLI 使用说明误认为网站部署文档

### Web README 收敛

`apps/web/README.md` 需要从模板状态收敛为真实说明：

- 说明这是 SkillHub Web 前端
- 本地开发命令保留
- 环境变量和完整部署说明统一指向根文档
- 删除无价值模板内容

### 环境变量模板收敛

根 `.env.example` 需要补全并按类别分组：

- 通用认证类：
  - `JWT_SECRET`
  - `CORS_ORIGINS`
- API / 存储类：
  - `DATABASE_URL`
  - `REDIS_URL`
  - `STORAGE_DIR`
- 前端代理类：
  - `SKILLHUB_API_BASE_URL` 或 `SKILLHUB_API_HOSTPORT`
  - `SKILLHUB_SESSION_SECRET`
- LLM / OCR 类：
  - `DEEPSEEK_KEY`
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `MINERU_TOKEN`
- 行为开关类：
  - `DEFAULT_LLM_PROVIDER`
  - `ALLOW_PARTIAL_SKILL`

模板里需要明确：

- 哪些变量是必填
- 哪些变量是可选
- 哪些变量仅用于特定部署方式

## 运行模式说明

### 本地开发模式

需要明确说明：

- Web 与 API 分别启动
- 数据库和 Redis 可用 Compose 起辅助服务
- 当前 demo task 体系与真实 Celery worker 不完全等价
- 若只做基本页面/API 调试，最低依赖集合是什么

### Compose 模式

当前 Compose 的说明必须诚实反映现状：

- 当前文件主要覆盖 Postgres / Redis / API / Worker
- 尚未覆盖 Web 服务
- `worker` 命令与当前 demo task 执行体系存在错位风险

因此文档中应把 Compose 标注为：

- “后端基础依赖 + API 演示环境”
- 而不是“完整生产部署方案”

### Render 模式

Render 文档需要说明：

- 当前仓库已有 `render.yaml`
- API 健康检查使用 `/health`
- Web 与 API 已分服务定义
- 目前没有独立 worker 服务定义
- 域名类变量需要按实际环境覆盖，而不是照抄仓库中的实例值

## 健康检查说明

当前文档只需要准确描述现状：

- API 提供 `/health`
- 返回最小 `ok/status`
- 它表示“进程存活”，不表示数据库、Redis、OCR、LLM 全部就绪

文档中应明确区分：

- 当前已支持：基本存活检查
- 当前未支持：readiness / dependency probe / worker health

## 具体改动范围

本次设计对应以下改动：

- 新增 `docs/deploy-skillhub.md`
- 修改根 `README.md`，增加网站部署入口
- 修改 `apps/web/README.md`，去掉模板化内容并收敛到主文档
- 修改根 `.env.example`，补全当前真实依赖变量与说明

本次不改动：

- `docker-compose.yml` 的运行逻辑
- `render.yaml` 的服务定义
- API `/health` 返回结构
- Worker 实现方式

## 验收标准

- 新开发者只读根 `README.md` 就能找到 SkillHub 网站部署入口
- `docs/deploy-skillhub.md` 能说明本地开发、Compose、Render 三种运行方式
- 根 `.env.example` 覆盖当前代码实际依赖的关键变量
- `apps/web/README.md` 不再是模板内容
- 文档中明确指出 Compose / health / worker 的当前边界，不误导读者

## 测试与验证

实现完成后至少验证以下内容：

- 逐项核对 `.env.example` 与 `apps/api/app/config.py`、`apps/web/src/lib/api-proxy.ts` 的变量一致性
- 逐项核对部署文档中的命令、路径、文件名是否真实存在
- 确认根 README 和 Web README 都能正确跳转到主部署文档
- 人工检查“首次阅读仓库的人是否能看懂如何启动网站”

## 风险与缓解

风险：

- 文档如果超前于代码，会再次造成误导
- `.env.example` 若一次性塞入太多变量，会降低可读性
- 如果不明确标注 Compose 限制，读者仍会误判它是完整方案

缓解：

- 只写当前代码已存在的能力
- 按“必填/可选/模式专属”组织变量
- 在部署文档里显式写出“当前限制”

## 后续衔接

`1-1` 完成后，后续更适合继续推进：

- `1-2` 前端 `types / api-client / hooks` 收敛
- `2-1` 搜索 debounce、聊天会话、settings 接口与更完整 health 检查

## 产出

本次设计最终应产出：

- 一份单一入口的 SkillHub 网站部署文档
- 一份与当前代码一致的根级环境变量模板
- 两份完成入口收敛后的 README（根 README 与 Web README）
