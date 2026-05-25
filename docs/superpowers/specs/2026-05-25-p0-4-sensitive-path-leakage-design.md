# SkillHub P0-4 敏感路径与内部错误暴露修复设计

## 背景

当前任务与 Skill 链路里，后端会把部分服务端内部实现细节直接返回给前端，包括：

- Skill 详情接口返回 `skill_dir`
- 任务进度 WebSocket 在 `probe` 阶段透出 PDF 绝对路径
- 任务失败进度消息透出 Python traceback

这些字段会暴露服务器文件系统结构、运行目录和源码路径，属于不必要的实现泄露。即使当前调用方已经过认证，这类信息也不应出现在前端可见响应里。

这属于 P0 级问题，因为它直接扩大了服务端内部实现面的暴露范围，也会让后续错误信息和日志脱敏变得更困难。

## 目标

- 移除前端可见响应中的服务端绝对路径
- 移除前端可见进度消息中的内部 traceback
- 保持任务页、Skill 页和进度页的现有核心功能可用
- 保持数据库结构不变，以最小改动完成收口

## 非目标

- 不在本次重构 `Skill` / `BenchmarkResult` 的 ORM 关系
- 不在本次引入 migration 或表结构调整
- 不改写任务状态机
- 不重做前端页面结构
- 不清理数据库中已落库的历史绝对路径字段，只收口对外暴露

## 已确认事实

- `apps/api/app/api/v1/skills.py` 的 `GET /api/v1/skills/{skill_id}` 当前会返回 `skill_dir`
- `apps/api/app/tasks/pipeline_task.py` 在 `probe` 完成后会把 `probe_pdf(...)` 的结果原样放进 WebSocket `extra`
- `skeleton/pdf_utils.py` 的 `probe_pdf(...)` 当前包含 `path = str(pdf_path.absolute())`
- `apps/api/app/tasks/pipeline_task.py` 在失败路径会把 `traceback.format_exc(limit=5)` 放进 WebSocket `extra`
- 前端代理层当前不会过滤这些字段，因此它们会直接到浏览器

## 设计原则

- 只暴露前端真正需要的业务信息
- 不向浏览器返回服务端文件系统结构
- 失败信息保持“可见失败”，但不附带内部实现细节
- 优先在后端收口，避免依赖前端自行过滤

## 方案选择

本次采用以下方案：

- 收紧 Skill 详情接口响应，移除 `skill_dir`
- 对任务进度事件做安全裁剪，移除绝对路径和 traceback
- 保留任务状态、阶段、进度百分比、用户可理解的错误摘要

不采用以下方案：

- 不仅靠前端隐藏字段，因为 API 和 WebSocket 仍然会继续泄露
- 不扩大到数据库字段删除，因为这会把问题升级成数据迁移项目
- 不把所有异常统一替换成固定文案，因为这样会损失必要的用户可观测性

## 架构设计

### Skill 详情接口收口

`apps/api/app/api/v1/skills.py` 只应返回页面需要的业务字段。

目标行为：

- 保留 `id`、`name`、`book_title`、`domain`、`visibility`、`chapter_count`、benchmark 摘要
- 删除 `skill_dir`
- 不影响章节读取和 benchmark 查询接口的现有行为

### 进度消息安全裁剪

`apps/api/app/tasks/pipeline_task.py` 需要在 `publish_progress(...)` 进入消息总线前，对 `extra` 做统一脱敏。

目标行为：

- `probe` 阶段不再向前端透出 PDF 绝对路径
- 失败阶段不再向前端透出 traceback
- 保留页数、文件大小、是否需要 OCR、是否降级等业务可观察字段

### 失败信息可见但不泄露内部实现

失败事件与任务详情仍需要能让用户知道任务失败了，但信息粒度应收敛。

目标行为：

- 保留 `error_message` 这一现有机制
- WebSocket 失败事件仅返回用户可理解的失败摘要
- 不把源码路径、工作目录、Python 栈帧发给浏览器

## 组件改动

### `apps/api/app/api/v1/skills.py`

需要完成以下改造：

- 移除 `get_skill()` 响应里的 `skill_dir`
- 保持返回体对现有页面兼容

### `apps/api/app/tasks/pipeline_task.py`

需要完成以下改造：

- 引入统一的进度消息脱敏辅助逻辑
- 在 `publish_progress(...)` 发送前裁剪 `extra`
- 删除失败事件里的 `traceback` 对外暴露

### `skeleton/pdf_utils.py`

需要完成以下改造：

- 调整 `probe_pdf(...)` 的输出，不再包含前端不需要的绝对路径
- 保留探测页数、大小、是否需要 OCR 等业务字段

## 对外行为变化

本次改动后，前端不再能看到以下字段或内容：

- Skill 目录绝对路径
- 上传 PDF 的绝对路径
- Python traceback 中的源码路径和栈帧

前端仍能看到：

- 任务状态与阶段
- 进度百分比
- OCR / 切章 / benchmark 的业务状态
- 可展示给用户的失败摘要

## 错误处理

- 技术细节进入后端日志即可，不进入浏览器响应
- 对用户的失败反馈继续沿用现有 `error_message` / 状态字段
- 如果未来某些异常文本本身包含绝对路径，本次优先保证不在 WebSocket `extra` 中继续扩散；任务详情接口中的错误文本脱敏属于后续可扩展项，不纳入本次范围

## 前端影响

本次不要求前端改结构，但需要满足：

- Skill 详情页不依赖 `skill_dir`
- 进度页能在没有 `probe.path` 和 `traceback` 的情况下继续工作

如果前端存在对这些字段的隐式依赖，应改为依赖已有业务字段，而不是服务端内部路径。

## 验收标准

- `GET /api/v1/skills/{skill_id}` 响应中不再包含 `skill_dir`
- WebSocket 进度消息中不再出现本机绝对路径
- WebSocket 失败消息中不再出现 traceback
- 任务进度页仍能正常显示阶段、进度和失败结果
- Skill 详情页与 benchmark 页不回归

## 测试与验证

实现完成后至少验证以下内容：

- 创建任务并订阅进度流，检查消息中不存在绝对路径
- 制造任务失败，检查失败事件中不存在 traceback
- 请求 Skill 详情，检查响应中不存在 `skill_dir`
- 前端相关页面仍能正常加载并展示核心数据

## 风险与缓解

风险：

- 前端若隐式依赖 `skill_dir`，删除后可能导致详情页回归
- 进度消息裁剪过度可能导致前端失去必要展示信息
- 若仅删除 `traceback`，仍可能存在个别异常文案自带路径

缓解：

- 保持接口主字段稳定，只移除明确不该暴露的字段
- 优先保留业务指标字段，避免把整个 `extra` 置空
- 验证 Skill 详情页与进度页的关键展示链路

## 产出

本次设计对应的实现产出应包括：

- 一个不再返回 `skill_dir` 的 Skill 详情接口
- 一个会在发送前自动裁剪敏感字段的任务进度消息层
- 一组不再向前端暴露绝对路径和 traceback 的任务执行反馈
