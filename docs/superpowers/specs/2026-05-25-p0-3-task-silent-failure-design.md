# SkillHub P0-3 任务静默失败修复设计

## 背景

当前任务创建链路如下：

1. 前端调用 `POST /api/v1/tasks`
2. 后端在数据库中创建 `Task`，初始状态为 `pending`
3. 后端调用 `run_pipeline_task.delay(...)`
4. 本地演示环境下，`delay()` 通过 `DemoCeleryApp` 启动独立 Python 子进程执行 `demo_task_runner`

当前风险点在于：

- 如果 `.delay()` 阶段或子进程启动阶段就失败，任务可能已经写入数据库，但没有进入真正执行
- 这类失败可能不会回写到 `Task.status`
- 用户看到的结果是任务停留在 `pending/queued`，但后台实际已经静默失败

这属于 P0 级阻塞问题，因为它会直接破坏任务系统的可观测性和可用性。

## 目标

- 修复任务在 worker/runner 启动阶段的静默失败
- 确保启动失败能够显式落库为 `failed`
- 保持现有正常任务执行链路不变
- 不引入额外的完整调度系统或后台巡检机制

## 非目标

- 不在本次接入真实 Celery/Redis 基础设施
- 不新增定时看门狗扫描长期挂起任务
- 不重构整个任务状态机
- 不扩大到部署配置、README 或 `.env.example` 的全链路重写

## 已确认事实

- `apps/api/app/api/v1/tasks.py` 在创建 `Task` 后立即调用 `run_pipeline_task.delay(str(task.id))`
- `apps/api/app/tasks/celery_app.py` 的 demo 实现只是 `subprocess.Popen(...)` 后返回 task id
- `apps/api/app/tasks/demo_task_runner.py` 当前没有最外层“失败写回数据库”的兜底
- `apps/api/app/tasks/pipeline_task.py` 已经覆盖了“任务函数运行中抛异常”的失败落库

## 设计原则

- 让失败显式化，而不是让任务永远停在 `pending`
- 优先修复最短失败路径，不扩大到完整调度基础设施
- 保持正常执行路径和现有 API 形状稳定
- 将错误信息写入数据库，便于前端直接展示

## 方案选择

本次采用以下方案：

- 在任务提交阶段捕获 worker 启动失败
- 在 demo runner 最外层增加异常兜底
- 将启动前失败统一回写为 `Task.status = failed`

不采用以下方案：

- 不采用全量 Celery/Redis 重构，因为范围过大
- 不采用任务看门狗扫描方案，因为会引入新的后台机制，超出本次最小修复范围

## 架构设计

### 提交阶段兜底

`apps/api/app/api/v1/tasks.py` 需要在 `.delay()` 调用阶段对异常进行处理。

目标行为：

- 如果 `.delay()` 本身抛错，不能继续返回一个表面上成功的 `pending` 任务
- 必须立即把任务改成 `failed`
- 必须保存 `error_message`

### demo worker 启动兜底

`apps/api/app/tasks/demo_task_runner.py` 需要增加最外层异常捕获。

目标行为：

- 即使任务函数还没真正执行到 `pipeline_task.py`
- 只要 runner 在导入模块、读取参数、加载 callable、调用任务前后抛异常
- 都必须显式回写数据库

### 运行中失败沿用现有逻辑

`apps/api/app/tasks/pipeline_task.py` 当前已有：

- 捕获运行期异常
- 将任务标记为 `failed`
- 写入 `error_message`

这部分保持不变，不做重构。

## 组件改动

### `apps/api/app/api/v1/tasks.py`

需要完成以下改造：

- 将 `.delay()` 包在显式异常处理里
- 启动失败时，把任务状态改为 `failed`
- 记录可读 `error_message`
- 避免返回一个永远不会执行的“假成功”任务

### `apps/api/app/tasks/celery_app.py`

该文件可能需要最小辅助改造，用于：

- 对 demo worker 启动失败提供更明确的异常语义
- 如有必要，暴露 runner 所需的公共辅助函数

原则是最小改动，不把它改造成完整任务队列实现。

### `apps/api/app/tasks/demo_task_runner.py`

需要完成以下改造：

- 增加最外层 `try/except`
- 在异常路径中定位当前目标任务
- 回写 `status = failed`
- 写入 `error_message`
- 必要时补充 `completed_at`

### `apps/api/app/tasks/pipeline_task.py`

原则上不做功能性改动，仅在实现过程中复用已有失败写回模式。

## 状态流转

正常路径：

- `pending` -> `running` -> `completed`

本次新增要兜住的失败路径：

- `pending` -> `failed`
  - 适用于 `.delay()` 启动失败
  - 适用于 demo runner 导入/启动即失败

已有路径继续保留：

- `running` -> `failed`
  - 适用于 pipeline 执行中失败

## 错误处理

- `.delay()` 抛异常时：
  - 立即回写 `failed`
  - `error_message` 包含异常类型和简要原因
- demo runner 初始化失败时：
  - 回写 `failed`
  - `error_message` 包含导入/调用阶段错误
- pipeline 运行中失败时：
  - 保持当前行为

错误处理原则：

- 不允许静默吞错
- 不允许任务长期停留在 `pending/queued`
- 前端应能通过现有任务接口拿到失败状态和错误文本

## 前端影响

本次无需前端结构调整。

原因：

- 前端已经会读取任务状态和错误信息
- 一旦后端把静默失败显式落库，前端现有任务页与进度页即可展示失败结果

## 验收标准

- 人为制造 `.delay()` 启动失败时，任务不会永久停留在 `pending`
- 人为制造 demo runner 初始化失败时，任务会变为 `failed`
- 正常任务仍能继续进入 `running`
- 任务列表与任务详情接口能正确返回失败状态与错误信息
- 取消任务和完成任务路径不回归

## 测试与验证

实现完成后至少验证以下内容：

- 后端能正常启动
- 正常创建任务后，状态能进入 `running`
- 模拟启动失败时，任务能进入 `failed`
- 模拟 runner 初始化失败时，任务能进入 `failed`
- 任务详情接口返回 `error_message`

如环境允许，可补充：

- 检查进度页对失败任务的展示是否符合预期

## 风险与缓解

风险：

- 如果只在 `.delay()` 一处兜底，仍可能漏掉子进程启动后的早期崩溃
- 如果 runner 回写失败逻辑实现不稳，可能再次出现“失败但无状态变化”
- 过度改造任务 shim 容易引入新回归

缓解：

- 提交阶段与 runner 阶段双层兜底
- 尽量复用现有 `pipeline_task.py` 的失败写回模式
- 仅修改本次静默失败直接相关文件

## 产出

本次设计对应的实现产出应包括：

- 一个不再静默失败的任务创建链路
- 一个能把 runner 启动异常显式回写到任务表的 demo worker 包装层
- 一组可通过现有任务接口观察到的失败状态与错误信息
