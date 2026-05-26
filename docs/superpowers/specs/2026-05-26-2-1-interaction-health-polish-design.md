# SkillHub 2-1 交互收尾与健康检查设计

## 背景

在 `1-1` 和 `1-2` 完成后，SkillHub 已经具备：

- 可用的部署入口与环境变量文档
- 基础的前端数据层分层
- 从上传、编译进度到结果页的完整主流程

但当前体验仍存在两类明显短板：

- 部署侧只有最小 `GET /health`，只能表示 API 进程存活，不能表达数据库和本地存储是否可用
- 主流程页面仍有若干“交互未收口”问题，例如非法文件拖入无提示、进度页仅靠轮询、结果页加载时空白

这些问题不再属于架构性缺口，而是影响“是否足够可用、可判断、可交付”的收尾项，因此适合作为 `2-1` 单独处理。

## 目标

- 在不改变现有部署路径的前提下，增强 `/health` 的有效性
- 收紧 `upload -> progress -> benchmark` 主流程中的静默失败、空白加载和弱反馈问题
- 复用现有后端 WebSocket 进度通道，为进度页补齐实时体验
- 保持当前页面结构与路由不变，避免把 `2-1` 扩展成新的大规模重构

## 非目标

- 不新增 `/ready`、`/live` 等额外路由
- 不实现完整的 worker health、OCR/LLM 外部依赖探针
- 不引入新的前端状态管理库
- 不重做 `chat` 页面为流式输出、会话管理或自动重试
- 不新增任务取消、任务重试等后端动作接口
- 不在本次实现 benchmark 原始结果下钻

## 已确认事实

- API 当前已有 `GET /health`，返回固定 `{"status":"ok"}`，定义在 `apps/api/app/main.py`
- Render 当前依赖 `/health` 进行 API 健康检查，因此不应修改路由路径
- API 启动时已经会执行存储目录准备、数据库初始化、预置 demo skill 等启动逻辑
- 后端已有 `ws/progress/{task_id}` WebSocket 进度流，并已完成基于 token 的鉴权与 owner 校验
- 前端 `progress` 页面目前仍只通过轮询 `GET /api/tasks/{taskId}` 更新状态
- 前端 `benchmark` 页面在数据未加载完成时直接返回 `null`
- 前端 `upload` 页面对非 PDF 拖拽文件缺少明确错误反馈

## 设计原则

- 最小闭环：优先补齐“主流程可用性”，不追求一次性 polish 全站
- 保持兼容：保留现有路由、接口和部署配置的兼容性
- 前后端同频：健康检查和交互收尾都只实现当前代码能够真实支撑的能力
- WebSocket 优先，轮询兜底：优先使用已存在的实时通道，但保留退化路径
- 明确边界：对未实现的更强探针、chat 流式化等能力显式排除

## 方案选择

本次采用以下方案：

- 保留 `GET /health` 路由不变，仅增强返回结构与内部检查
- 将健康检查聚焦到 API 进程可直接验证的两类依赖：
  - 数据库可访问
  - 本地存储目录可访问
- 在 `upload` 页面补齐非法文件反馈与更明确的提交中状态
- 在 `progress` 页面改为 WebSocket 优先，轮询兜底
- 在 `benchmark` 页面补齐加载态，避免白屏

不采用以下方案：

- 不新增新的健康检查路由，避免同步修改部署平台配置
- 不把 Redis、worker、OCR、LLM key 强行纳入 `/health`
- 不在本次触碰 `chat` 页面发送链路与流式回复
- 不在本次引入全局 toast、skeleton 体系重构

## 健康检查设计

### 路由与兼容性

- 保留现有 `GET /health`
- 成功时返回 `200 OK`
- 返回体从单一 `status` 扩展为结构化对象

建议结构：

```json
{
  "status": "ok",
  "checks": {
    "database": "ok",
    "storage": "ok"
  }
}
```

当依赖异常时：

- 仍返回结构化结果
- 用明确字段表示失败项
- 整体状态切换为 `degraded` 或 `error`
- HTTP 状态码对依赖失败返回 `503`

### 检查范围

本次只检查当前 API 进程可以稳定验证的内容：

- `database`
- `storage`

具体含义：

- `database`：执行一次最小数据库可达性检查
- `storage`：确认 `settings.storage_dir` 存在且可访问

本次不检查：

- Redis
- worker
- OCR token
- 各类 LLM key
- 外部第三方服务连通性

原因是：

- 这些依赖并非所有运行模式都强制需要
- 当前代码没有统一、可靠、低成本的探针语义
- 强行纳入会让 `/health` 结果与真实运行场景脱节

### 文档同步

需要同步更新 `docs/deploy-skillhub.md` 的健康检查章节，明确：

- `/health` 现在检查了哪些项
- 哪些项仍未覆盖
- 它仍不是完整的 readiness/liveness 方案

## 前端交互收尾设计

### Upload 页

目标文件：

- `apps/web/src/app/(dashboard)/upload/page.tsx`

本次收尾内容：

- 对拖拽和文件选择统一做 PDF 校验
- 非 PDF 文件给出明确错误提示，而不是静默忽略
- 提交中按钮保持禁用，并给出更明确的处理中提示
- 保持现有提交流程与接口不变

本次不做：

- 真实上传百分比
- 分片上传
- 上传重试

### Progress 页

目标文件：

- `apps/web/src/app/(dashboard)/progress/[taskId]/page.tsx`
- `apps/web/src/hooks/use-task.ts`

本次收尾内容：

- 由 `useTask()` 统一承载实时状态获取
- 优先订阅 WebSocket 进度流
- 当 WebSocket 连接失败、被拒绝或异常断开时，自动回退到现有轮询模式
- 页面增加更明确的“连接中 / 已回退到轮询 / 已完成跳转中 / 失败”文案

状态策略：

- 首次进入页面时，先拉一次任务详情，确保有初始状态
- 若 WebSocket 成功建立，以 WebSocket 消息作为主数据源
- 若 WebSocket 不可用，则继续使用定时轮询
- 任务完成且存在 `skill_id` 时，维持当前自动跳转结果页行为

本次不做：

- 取消任务
- 重试任务
- 页面离开后的后台通知

### Benchmark 页

目标文件：

- `apps/web/src/app/(dashboard)/benchmark/[skillId]/page.tsx`
- `apps/web/src/hooks/use-benchmark.ts`

本次收尾内容：

- 数据未完成加载时显示占位内容，而不是返回 `null`
- 保持现有错误态和结果展示结构
- 保持并发获取 skill 详情和 benchmark 结果的行为

本次不做：

- `raw_results` 展开查看
- 图表重构
- 新的结果分析组件

### Chat 页边界

`chat` 页当前仍有进一步 polish 空间，但本次只把它作为边界声明，不进入实现：

- 不做流式输出
- 不做自动滚动
- 不做失败后一键重试
- 不做会话持久化

原因是这些改动会把 `2-1` 从“主流程收尾”扩展成“聊天体验重做”。

## 模块设计

### 后端

建议新增或调整：

- 在 `apps/api/app/main.py` 中增强 `/health`
- 视需要新增轻量健康检查辅助函数，避免把检查逻辑直接堆在路由里

后端输出应满足：

- 返回结构稳定、可文档化
- 失败时不泄露内部敏感路径或原始异常细节
- 不引入新的外部依赖

### 前端

建议沿用 `1-2` 已建立的数据层：

- `useTask()` 扩展为“详情 + WebSocket + 轮询兜底”的统一 hook
- `progress/page.tsx` 仅负责阶段映射与展示
- `benchmark/page.tsx` 仅增加 loading 占位，不改变布局结构
- `upload/page.tsx` 在页面内完成文件校验与错误提示增强

## 验收标准

- `GET /health` 能返回结构化结果，而不再只是固定字符串状态
- 当数据库或存储异常时，健康检查能给出可区分的失败信息
- `upload` 页对非 PDF 文件有明确错误提示
- `progress` 页优先使用 WebSocket，异常时仍能回退到轮询
- `progress` 页不会因实时连接失败而完全失去更新能力
- `benchmark` 页在加载中不再出现空白页
- 主流程 `upload -> progress -> benchmark` 行为保持连贯

## 测试与验证

后端至少验证：

- 健康检查正常返回
- 健康检查在依赖异常时返回预期状态

前端至少验证：

- `npm run lint` 通过
- 上传页非法文件提示可见
- 合法 PDF 仍可正常创建任务
- 进度页在 WebSocket 可用时能实时更新
- 进度页在 WebSocket 不可用时仍能通过轮询更新
- 结果页加载中可见占位内容，加载后正常展示

## 风险与缓解

风险：

- WebSocket 事件结构与前端期望不一致，可能导致状态映射错误
- 健康检查若直接暴露异常原文，可能引入新的信息泄露
- 过度追求实时化可能让 `useTask()` 逻辑变复杂

缓解：

- 先以“初始详情请求 + WebSocket 增量更新 + 轮询兜底”的保守策略实现
- 健康检查仅返回归一化状态，不直接暴露底层异常对象
- 把实时连接状态收敛在 hook 内，页面只消费统一输出

## 后续衔接

`2-1` 最小闭环完成后，再继续推进更合适的后续项：

- `chat` 流式输出与交互 polish
- benchmark 原始结果下钻
- 更完整的 readiness / liveness / worker health
- 部署后 smoke check 脚本

## 产出

本次设计最终应产出：

- 一版增强后的 `/health`
- 一版 WebSocket 优先、轮询兜底的进度 hook
- 一版完成错误/加载收尾的 `upload`、`progress`、`benchmark` 页面
- 一份同步更新的健康检查部署说明
