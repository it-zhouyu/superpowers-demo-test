> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 起点：SKILL.md 文件

当 Claude Code 执行 apply 技能时，底层做的事和 propose 一样：找到对应的 SKILL.md 文件，然后按照里面的指令一步步执行。

这个文件位于 `.claude/skills/openspec-apply-change/SKILL.md`，同样由 `openspec init` 生成。

frontmatter 中的 `description` 告诉 Claude Code 何时激活这个技能：

```yaml
name: openspec-apply-change
description: Implement tasks from an OpenSpec change. Use when the user wants
  to start implementing, continue implementation, or work through tasks.
metadata:
  author: openspec
  version: "1.0"
```

当你的描述匹配"开始实现"或"继续实现"时，Claude Code 自动加载这个技能的指令正文。

指令正文完整内容如下：

```
Implement tasks from an OpenSpec change.

Input: Optionally specify a change name. If omitted, check if it can be
inferred from conversation context. If vague or ambiguous you MUST prompt
for available changes.

Steps

1. Select the change
   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes
     and use the AskUserQuestion tool to let the user select
   Always announce: "Using change: <name>"

2. Check status to understand the schema
   > openspec status --change "<name>" --json
   Parse the JSON to understand:
   - schemaName: The workflow being used (e.g., "spec-driven")
   - planningHome, changeRoot, and actionContext: planning scope
   - Which artifact contains the tasks (typically "tasks" for spec-driven)

3. Get apply instructions
   > openspec instructions apply --change "<name>" --json
   This returns:
   - contextFiles: artifact ID -> array of concrete file paths
   - Progress (total, complete, remaining)
   - Task list with status
   - Dynamic instruction based on current state

   Handle states:
   - If state: "blocked" (missing artifacts): show message,
     suggest using openspec-continue-change
   - If state: "all_done": congratulate, suggest archive
   - Otherwise: proceed to implementation

   Workspace guard: If status JSON reports actionContext.mode:
   "workspace-planning" and allowedEditRoots is empty, explain that
   full workspace apply is not supported and STOP before editing files.

4. Read context files
   Read every file path listed under contextFiles from the apply
   instructions output. The files depend on the schema being used:
   - spec-driven: proposal, specs, design, tasks
   - Other schemas: follow the contextFiles from CLI output

5. Show current progress
   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview
   - Dynamic instruction from CLI

6. Implement tasks (loop until done or blocked)
   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Mark task complete in the tasks file: - [ ] → - [x]
   - Continue to next task

   Pause if:
   - Task is unclear → ask for clarification
   - Implementation reveals a design issue → suggest updating artifacts
   - Error or blocker encountered → report and wait for guidance
   - User interrupts

7. On completion or pause, show status
   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If all done: suggest archive
   - If paused: explain why and wait for guidance

Output During Implementation

  ## Implementing: <change-name> (schema: <schema-name>)
  Working on task 3/7: <task description>
  [...implementation happening...]
  ✓ Task complete

Output On Completion

  ## Implementation Complete
  **Change:** <change-name>
  **Schema:** <schema-name>
  **Progress:** 7/7 tasks complete ✓
  All tasks complete! Ready to archive this change.

Output On Pause (Issue Encountered)

  ## Implementation Paused
  **Change:** <change-name>
  **Progress:** 4/7 tasks complete
  ### Issue Encountered
  <description of the issue>
  What would you like to do?

Guardrails

- Keep going through tasks until done or blocked
- Always read context files before starting (from the apply instructions output)
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Update task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements - don't guess
- Use contextFiles from CLI output, don't assume specific file names

Fluid Workflow Integration

This skill supports the "actions on a change" model:
- Can be invoked anytime: Before all artifacts are done (if tasks exist),
  after partial implementation, interleaved with other actions
- Allows artifact updates: If implementation reveals design issues,
  suggest updating artifacts - not phase-locked, work fluidly
```

和 propose 的 SKILL.md 对比，apply 的核心区别在两点：

1. **Step 3 调用的是 `openspec instructions apply`**，不是 `openspec instructions <artifact-id>`。这是一个特殊的 CLI 入口，不走 artifact 的指令组装逻辑，而是返回任务级别的执行上下文
2. **Step 6 是一个循环**——逐个实现 task，完成后标记 `[x]`，直到全部完成或遇到阻塞

下面继续用前面讲到的"用户注册功能"例子，走完这 7 步。假设 propose 已经完成，所有 artifact 都已创建好。现在你说：

> "开始实现用户注册功能"

## Step 1：选择 change

Claude Code 从对话上下文推断你要 apply 的 change 是 `add-user-registration`（因为你刚才在讨论这个功能）。如果同时有多个活跃 change，Claude Code 会执行 `openspec list --json` 列出所有 change，用 AskUserQuestion 让你选择。

**这一步的产出**：确定 change 名称为 `add-user-registration`。

## Step 2：检查状态

Claude Code 执行 CLI 命令：

```bash
openspec status --change "add-user-registration" --json
```

propose 阶段已经创建了所有 artifact，所以返回的 JSON 中所有 artifact 状态都是 `done`：

```json
{
  "changeName": "add-user-registration",
  "schemaName": "spec-driven",
  "isComplete": true,
  "applyRequires": ["tasks"],
  "artifacts": [
    { "id": "proposal", "status": "done" },
    { "id": "specs",    "status": "done" },
    { "id": "design",   "status": "done" },
    { "id": "tasks",    "status": "done" }
  ],
  "changeRoot": "openspec/changes/add-user-registration"
}
```

Claude Code 从中拿到 `schemaName: "spec-driven"`，知道用的是什么 Schema，以及 change 目录的路径。

**这一步的产出**：确认 Schema 为 spec-driven，所有 artifact 都已创建，change 目录路径确认。

## Step 3：获取 apply 指令

这是 apply 和 propose 的关键区别。Claude Code 执行的不是 `openspec instructions <artifact-id>`，而是一个特殊命令：

```bash
openspec instructions apply --change "add-user-registration" --json
```

这条命令背后做了什么？

1. 加载 change 的 Schema（spec-driven），读取其中的 `apply` 配置段：

```yaml
apply:
  requires: [tasks]
  tracks: tasks.md
  instruction: |
    Read context files, work through pending tasks, mark complete as you go.
    Pause if you hit blockers or need clarification.
```

2. 检查 `requires` 中声明的 artifact（tasks）是否存在 → tasks.md 存在，满足
3. 解析 `tracks` 指向的 tasks.md，用正则匹配 `- [ ]` 和 `- [x]`，统计任务进度
4. 遍历 Schema 中所有 artifact，检查对应文件是否存在，把存在的文件路径组装成 `contextFiles`
5. 根据以上结果判断当前状态，返回对应的指令

返回的 JSON：

```json
{
  "changeName": "add-user-registration",
  "schemaName": "spec-driven",
  "state": "ready",
  "contextFiles": {
    "proposal": ["openspec/changes/add-user-registration/proposal.md"],
    "specs": ["openspec/changes/add-user-registration/specs/auth/spec.md"],
    "design": ["openspec/changes/add-user-registration/design.md"],
    "tasks": ["openspec/changes/add-user-registration/tasks.md"]
  },
  "progress": { "total": 8, "complete": 0, "remaining": 8 },
  "tasks": [
    { "id": "1", "description": "添加 phone_number 字段", "done": false },
    { "id": "2", "description": "创建数据库迁移", "done": false },
    { "id": "3", "description": "实现 Redis 验证码生成和存储", "done": false },
    { "id": "4", "description": "实现验证码校验逻辑", "done": false },
    { "id": "5", "description": "添加 rate limiting 中间件", "done": false },
    { "id": "6", "description": "实现 POST /auth/send-code", "done": false },
    { "id": "7", "description": "实现 POST /auth/register", "done": false },
    { "id": "8", "description": "添加请求参数校验", "done": false }
  ],
  "instruction": "Read context files, work through pending tasks, mark complete as you go. Pause if you hit blockers or need clarification."
}
```

这份 JSON 通过 Bash 工具的返回值进入 Claude Code 的上下文，Claude Code 就知道了"当前有哪些上下文文件、总共有多少 task、完成了几个、下一步该做什么"。

关键字段：

- **`state`**：当前状态。三种取值：
  - `blocked`：必需的 artifact 缺失（比如 tasks.md 不存在），不能开始执行
  - `ready`：所有条件满足，可以开始实现 task
  - `all_done`：所有 task 都已完成，建议 archive
- **`contextFiles`**：每个 artifact 对应的实际文件路径。Claude Code 接下来会读取这些文件来理解上下文
- **`progress`**：任务进度统计，来自 tasks.md 的 checkbox 计数
- **`tasks`**：从 tasks.md 中解析出的任务列表，每个任务有描述和完成状态
- **`instruction`**：来自 schema.yaml 中 `apply.instruction` 字段的指导文本

**这一步的产出**：Claude Code 知道了 state=ready，有 8 个 task 待完成，以及需要读取哪些上下文文件。

## Step 4：读取上下文文件

Claude Code 读取 `contextFiles` 中列出的所有文件：proposal.md、specs/auth/spec.md、design.md、tasks.md。

这些文件就是 propose 阶段生成的四个 artifact。Claude Code 需要它们来理解"要实现什么功能、规格是什么、用什么技术方案、具体做哪些任务"。

**这一步的产出**：Claude Code 的上下文中加载了完整的规划信息。

## Step 5：展示当前进度

Claude Code 向你展示：

```
## Implementing: add-user-registration (schema: spec-driven)

Progress: 0/8 tasks complete

Remaining tasks:
- 1.1 添加 phone_number 字段
- 1.2 创建数据库迁移
- 2.1 实现 Redis 验证码生成和存储
- 2.2 实现验证码校验逻辑
- 2.3 添加 rate limiting 中间件
- 3.1 实现 POST /auth/send-code
- 3.2 实现 POST /auth/register
- 3.3 添加请求参数校验
```

**这一步的产出**：你和 Claude Code 都确认了当前状态和待做事项。

## Step 6：实现任务循环

这是 apply 的核心——Claude Code 逐个实现每个 task：

**Task 1：添加 phone_number 字段**

```
Working on task 1/8: 添加 phone_number 字段
[修改 prisma/schema.prisma，添加 phone_number 字段]
✓ Task complete
```

每完成一个 task，Claude Code 在 tasks.md 中把 `- [ ]` 改为 `- [x]`：

```markdown
- [x] 1.1 添加 phone_number 字段    ← 刚改的
- [ ] 1.2 创建数据库迁移
```

**Task 2：创建数据库迁移**

```
Working on task 2/8: 创建数据库迁移
[运行 npx prisma migrate dev]
✓ Task complete
```

以此类推，逐个完成。如果中间遇到问题（比如 Redis 连接不上），Claude Code 会暂停并告诉你：

```
## Implementation Paused

**Change:** add-user-registration
**Progress:** 3/8 tasks complete

### Issue Encountered
Task 2.1 实现 Redis 验证码生成时，Redis 连接超时。
可能原因：Redis 配置缺少密码。

What would you like to do?
```

**这一步的产出**：所有 task 逐一实现并标记完成，或者遇到问题时暂停等待你的指示。

## Step 7：展示结果

所有 task 完成后，Claude Code 展示最终状态：

```
## Implementation Complete

**Change:** add-user-registration
**Schema:** spec-driven
**Progress:** 8/8 tasks complete ✓

### Completed This Session
- [x] 1.1 添加 phone_number 字段
- [x] 1.2 创建数据库迁移
- [x] 2.1 实现 Redis 验证码生成和存储
- [x] 2.2 实现验证码校验逻辑
- [x] 2.3 添加 rate limiting 中间件
- [x] 3.1 实现 POST /auth/send-code
- [x] 3.2 实现 POST /auth/register
- [x] 3.3 添加请求参数校验

All tasks complete! Ready to archive this change.
```

## 中断恢复

apply 如果执行到一半被中断（手动停止、网络问题），再次执行 `/opsx:apply` 时：

1. Step 3 调用 `openspec instructions apply --json`，解析 tasks.md 中的 checkbox
2. `progress` 返回 "5/8 complete"
3. `state` 仍然是 `ready`（还有未完成的 task）
4. Claude Code 从第一个 `- [ ]` 开始继续执行

状态保存在 tasks.md 的 checkbox 中，不需要额外的 checkpoint 文件。tasks.md 既是计划文档，也是进度存储。

## `openspec instructions apply` 的三种状态详解

Step 3 中的 `state` 字段决定了 Claude Code 接下来做什么。完整的三种状态：

### blocked — 不能执行

触发条件：`apply.requires` 中声明的 artifact 有缺失（比如 tasks.md 还不存在），或者 `apply.tracks` 指向的文件中没有可解析的 task。

```json
{
  "state": "blocked",
  "missingArtifacts": ["tasks"],
  "instruction": "Cannot apply this change yet. Missing artifacts: tasks. Use openspec-continue-change to create the missing artifacts first."
}
```

Claude Code 看到这个状态后会告诉你"还缺少 tasks，需要先创建"，然后建议你运行 `/opsx:continue`。

### ready — 可以执行

触发条件：所有必需 artifact 都存在，tracks 文件中有未完成的 task。

```json
{
  "state": "ready",
  "contextFiles": { ... },
  "progress": { "total": 8, "complete": 2, "remaining": 6 },
  "instruction": "Read context files, work through pending tasks, mark complete as you go."
}
```

Claude Code 看到这个状态后进入 Step 6 的任务循环。

### all_done — 全部完成

触发条件：tracks 文件中所有 task 都已标记为 `[x]`。

```json
{
  "state": "all_done",
  "progress": { "total": 8, "complete": 8, "remaining": 0 },
  "instruction": "All tasks are complete! This change is ready to be archived."
}
```

Claude Code 看到这个状态后不会进入任务循环，而是直接告诉你"所有任务已完成，建议归档"。

### 状态判断的逻辑

三种状态的判断顺序：

1. 先检查 `apply.requires` 中的 artifact 是否都存在 → 不存在 → `blocked`
2. 再检查 tracks 文件是否存在、是否有可解析的 task → 不存在或没有 → `blocked`
3. 再检查所有 task 是否都已完成 → 全部完成 → `all_done`
4. 以上都不满足 → `ready`

这个顺序保证了 `blocked` 优先级最高——连任务文件都没有，谈不上执行。

## apply 和 propose 的对比

| | propose | apply |
|---|---|---|
| SKILL.md 步骤数 | 5 | 7 |
| 核心动作 | 创建 artifact（Markdown 文件） | 实现 task（写代码） |
| `openspec instructions` | 对每个 artifact 调用一次 | 对 apply 整体调用一次 |
| 指令返回内容 | 单个 artifact 的写作指南 + 模板 | 任务列表 + 上下文文件 + 进度 + 状态 |
| 状态感知 | 无（一次性创建） | 有（blocked/ready/all_done） |
| 循环机制 | 按依赖顺序逐个创建 | 逐个实现 task 直到完成或阻塞 |
| 进度追踪 | artifact 文件是否存在 | tasks.md 中的 checkbox |

共同点是：都不把"怎么写"硬编码在 SKILL.md 里，而是通过 `openspec instructions` 动态获取指令。区别在于 propose 为每个 artifact 获取写作指南，apply 为整体获取执行上下文。

## 小结

apply 的底层实现围绕"状态感知的任务执行循环"：

1. **SKILL.md**：7 步执行手册，核心是 Step 6 的任务循环
2. **`openspec instructions apply`**：特殊的 CLI 入口，返回三种状态（blocked/ready/all_done）、上下文文件列表、任务进度
3. **任务解析**：通过正则匹配 tasks.md 中的 checkbox 语法，统计进度
4. **中断恢复**：基于 tasks.md 的 checkbox 状态，无需额外机制
