> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 起点：SKILL.md 文件

当 Claude Code 执行 archive 技能时，底层做的事和 propose、apply 一样：找到对应的 SKILL.md 文件，然后按照里面的指令一步步执行。

这个文件位于 `.claude/skills/openspec-archive-change/SKILL.md`，由 `openspec init` 生成。

frontmatter 中的 `description` 告诉 Claude Code 何时激活这个技能：

```yaml
name: openspec-archive-change
description: Archive a completed change. Use when the user wants to finalize
  and archive a change after implementation is complete.
metadata:
  author: openspec
  version: "1.0"
```

当你的描述匹配"归档"或"收尾"时，Claude Code 自动加载这个技能的指令正文。

指令正文完整内容如下：

```
Archive a completed change.

Input: Optionally specify a change name. If omitted, check if it can be
inferred from conversation context. If vague or ambiguous you MUST prompt
for available changes.

Steps

1. If no change name provided, prompt for selection
   Run `openspec list --json` to get available changes. Use the
   AskUserQuestion tool to let the user select.
   Show only active changes (not already archived).
   Include the schema used for each change if available.
   IMPORTANT: Do NOT guess or auto-select a change. Always let the
   user choose.

2. Check artifact completion status
   Run `openspec status --change "<name>" --json` to check completion.
   Parse the JSON to understand:
   - schemaName: The workflow being used
   - planningHome, changeRoot, artifactPaths, actionContext: path context
   - artifacts: List of artifacts with their status (done or other)

   If actionContext.mode is "workspace-planning", explain that workspace
   archive is not supported and STOP.

   If any artifacts are not done:
   - Display warning listing incomplete artifacts
   - Use AskUserQuestion tool to confirm user wants to proceed
   - Proceed if user confirms

3. Check task completion status
   Read the tasks file (typically tasks.md) to check for incomplete tasks.
   Count tasks marked with - [ ] (incomplete) vs - [x] (complete).

   If incomplete tasks found:
   - Display warning showing count of incomplete tasks
   - Use AskUserQuestion tool to confirm user wants to proceed
   - Proceed if user confirms

   If no tasks file exists: Proceed without task-related warning.

4. Assess delta spec sync state
   Use artifactPaths.specs.existingOutputPaths from status JSON to check
   for delta specs. If none exist, proceed without sync prompt.

   If delta specs exist:
   - Compare each delta spec with its corresponding main spec at
     openspec/specs/<capability>/spec.md
   - Determine what changes would be applied (adds, modifications,
     removals, renames)
   - Show a combined summary before prompting

   Prompt options:
   - If changes needed: "Sync now (recommended)", "Archive without syncing"
   - If already synced: "Archive now", "Sync anyway", "Cancel"

   If user chooses sync, use Task tool (subagent_type: "general-purpose",
   prompt: "Use Skill tool to invoke openspec-sync-specs for change '<name>'.
   Delta spec analysis: <include the analyzed delta spec summary>").
   Proceed to archive regardless of choice.

5. Perform the archive
   Create an archive directory if it doesn't exist:
   > mkdir -p "<planningHome.changesDir>/archive"

   Generate target name using current date: YYYY-MM-DD-<change-name>

   Check if target already exists:
   - If yes: Fail with error, suggest renaming existing archive
   - If no: Move changeRoot to the archive directory
   > mv "<changeRoot>" "<planningHome.changesDir>/archive/YYYY-MM-DD-<name>"

6. Display summary
   Show archive completion summary including:
   - Change name
   - Schema that was used
   - Archive location
   - Whether specs were synced (if applicable)
   - Note about any warnings (incomplete artifacts/tasks)

Output On Success

  ## Archive Complete
  **Change:** <change-name>
  **Schema:** <schema-name>
  **Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
  **Specs:** ✓ Synced to main specs (or "No delta specs" or "Sync skipped")
  All artifacts complete. All tasks complete.

Output On Success With Warnings

  ## Archive Complete (with warnings)
  **Change:** <change-name>
  **Archived to:** openspec/changes/archive/YYYY-MM-DD-<name>/
  **Warnings:**
  - Archived with 2 incomplete artifacts
  - Archived with 3 incomplete tasks
  - Delta spec sync was skipped
  Review the archive if this was not intentional.

Guardrails

- Always prompt for change selection if not provided
- Use artifact graph (openspec status --json) for completion checking
- Don't block archive on warnings - just inform and confirm
- Preserve .openspec.yaml when moving to archive (it moves with directory)
- Show clear summary of what happened
- If sync is requested, use openspec-sync-specs approach (agent-driven)
- If delta specs exist, always run the sync assessment and show summary
  before prompting
```

和 propose、apply 的 SKILL.md 对比，archive 有一个关键区别：**它没有调用 `openspec instructions`**。propose 和 apply 都通过 CLI 动态获取指令，而 archive 的 SKILL.md 直接包含了所有逻辑。原因后面会分析。

下面继续用"用户注册功能"的例子走完这 6 步。假设 apply 已完成，8 个 task 全部标记为 `[x]`。现在你说：

> "归档用户注册功能"

## Step 1：选择 change

和 propose、apply 不同，archive 不会自动推断 change 名称，而是强制让你确认。Claude Code 执行：

```bash
openspec list --json
```

列出所有活跃的 change，然后用 AskUserQuestion 工具让你选择。这是故意的设计——归档是不可逆操作，不能凭猜测选错 change。

如果你在命令中已经指定了名称（如 `/opsx:archive add-user-registration`），这步直接使用你指定的名称。

**这一步的产出**：确定要归档的 change 为 `add-user-registration`。

## Step 2：检查 artifact 完成状态

Claude Code 执行：

```bash
openspec status --change "add-user-registration" --json
```

返回的 JSON：

```json
{
  "changeName": "add-user-registration",
  "schemaName": "spec-driven",
  "isComplete": true,
  "artifacts": [
    { "id": "proposal", "status": "done" },
    { "id": "specs",    "status": "done" },
    { "id": "design",   "status": "done" },
    { "id": "tasks",    "status": "done" }
  ],
  "artifactPaths": {
    "specs": {
      "existingOutputPaths": ["openspec/changes/add-user-registration/specs/auth/spec.md"]
    }
  },
  "planningHome": {
    "changesDir": "openspec/changes"
  },
  "changeRoot": "openspec/changes/add-user-registration",
  "actionContext": { "mode": "repo-local" }
}
```

Claude Code 从中检查三件事：

1. **artifact 是否全部 done** — 这里全部 done，没有警告
2. **actionContext.mode 是否为 workspace-planning** — 如果是，直接报错停止（workspace change 不能归档到 repo-local 的 archive 目录）。这里是 `repo-local`，通过
3. **artifactPaths 中是否有 delta spec 文件** — 有 `specs/auth/spec.md`，Step 4 会用到

如果有 artifact 不是 `done`，Claude Code 会列出警告并让你确认是否继续——警告不阻断，你确认后可以继续。

**这一步的产出**：确认所有 artifact 已完成、不是 workspace 模式、存在 delta spec 文件。

## Step 3：检查 task 完成状态

这一步不通过 CLI，而是 Claude Code 直接读取 tasks.md 文件，统计 `- [ ]` 和 `- [x]` 的数量。

```markdown
## 1. 数据层
- [x] 1.1 添加 phone_number 字段
- [x] 1.2 创建数据库迁移

## 2. 验证码服务
- [x] 2.1 实现 Redis 验证码生成和存储
- [x] 2.2 实现验证码校验逻辑
- [x] 2.3 添加 rate limiting 中间件

## 3. API 端点
- [x] 3.1 实现 POST /auth/send-code
- [x] 3.2 实现 POST /auth/register
- [x] 3.3 添加请求参数校验
```

统计结果：8/8 tasks complete，全部完成。

和 Step 2 的区别：Step 2 检查的是 artifact 文件是否存在（粗粒度），Step 3 检查的是 task 是否全部完成（细粒度）。一个 change 可以所有 artifact 文件都存在（`done`），但 tasks.md 中还有未完成的 checkbox。

如果有未完成的 task，Claude Code 同样列出警告让你确认——不阻断。

**这一步的产出**：确认 8/8 task 已完成。

## Step 4：评估 Delta Spec 同步状态

这是 archive 中最复杂的一步。Claude Code 从 Step 2 的 `artifactPaths.specs.existingOutputPaths` 中发现有一个 delta spec 文件：`openspec/changes/add-user-registration/specs/auth/spec.md`。

然后 Claude Code 做两件事：

1. 读取 change 中的 delta spec（`openspec/changes/add-user-registration/specs/auth/spec.md`）
2. 读取对应的主 spec（`openspec/specs/auth/spec.md`，如果存在的话）

对比两者，分析差异。比如 delta spec 中有 `## ADDED Requirements`（2 个新需求）和 `## MODIFIED Requirements`（1 个修改需求），主 spec 中还没有这些内容。

Claude Code 展示差异摘要：

```
Delta Spec Analysis for specs/auth/spec.md:

ADDED Requirements:
- Phone Number Registration (2 scenarios)
- Verification Code Rate Limiting

MODIFIED Requirements:
- Session Timeout (60min → 30min)
```

然后让你选择：

- **Sync now (recommended)** — 先把 delta spec 合并到主 spec，再归档
- **Archive without syncing** — 直接归档，不合并 spec

如果你选择 sync，Claude Code 会派一个子 agent 执行同步。不管同步是否成功，归档都会继续——因为归档是移动目录，同步是合并文件，两个操作是独立的。

如果不存在 delta spec（比如这个 change 没有修改 spec），这步直接跳过。

**这一步的产出**：delta spec 已同步到主 spec（或跳过同步），准备归档。

## Step 5：执行归档

纯文件系统操作。Claude Code 执行：

```bash
# 确保 archive 目录存在
mkdir -p "openspec/changes/archive"

# 检查目标是否已存在
# 如果 2025-01-24-add-user-registration 已存在 → 报错
# 如果不存在 → 移动目录
mv "openspec/changes/add-user-registration" "openspec/changes/archive/2025-01-24-add-user-registration"
```

归档命名用日期前缀（`YYYY-MM-DD-change-name`），保证唯一性和可排序性。如果当天已有同名归档，直接报错——不覆盖。

`.openspec.yaml` 元数据文件跟着目录一起移动，不需要额外处理。

归档后目录结构：

```
openspec/changes/archive/
└── 2025-01-24-add-user-registration/
    ├── .openspec.yaml
    ├── proposal.md
    ├── specs/
    │   └── auth/
    │       └── spec.md
    ├── design.md
    └── tasks.md
```

**这一步的产出**：change 目录已移到 archive 下。

## Step 6：展示摘要

```
## Archive Complete

**Change:** add-user-registration
**Schema:** spec-driven
**Archived to:** openspec/changes/archive/2025-01-24-add-user-registration/
**Specs:** ✓ Synced to main specs

All artifacts complete. All tasks complete.
```

如果有警告（比如有未完成的 artifact 或 task），摘要中会标注 `(with warnings)` 并列出具体警告。

归档后，`openspec/specs/auth/spec.md` 中包含了更新后的需求。下一个 change 如果要修改 auth 相关内容，会基于这个最新的 Spec 来写 Delta。

## archive 为什么不用 `openspec instructions`

propose 和 apply 都通过 `openspec instructions` 动态获取指令。archive 没有。原因：

propose 需要动态指令，因为每个 artifact 的写作规则不同（proposal 的规则和 specs 的规则不一样），规则来自 Schema 和项目配置，需要实时组装。

apply 需要动态指令，因为任务状态在变化（每次 apply 进度不同），需要实时检查 blocked/ready/all_done。

archive 不需要动态指令，因为它的操作是确定性的：

- 检查完成状态 → 读 JSON 或读文件
- 同步 Delta Spec → 对比文件差异
- 归档 → 移动目录

每一步的输入和输出都是确定的，不需要根据 Schema 的 `instruction` 字段来调整行为。所以 archive 的 SKILL.md 直接包含了所有逻辑，没有"去 CLI 拿指令"这一步。

## 安全检查的双层设计

Step 2 和 Step 3 构成双层安全检查：

| 检查层 | 检查内容 | 数据来源 | 阻断级别 |
|--------|---------|---------|---------|
| Step 2 | artifact 文件是否存在 | `openspec status --json` | 警告 + 确认 |
| Step 3 | task 是否全部完成 | 直接读 tasks.md | 警告 + 确认 |

两层都不阻断归档——它们只是警告，你确认后可以继续。这是因为"未完成"的定义可能因场景不同而不同：有些 task 可能不需要做，有些 artifact 可能故意没生成。

但有一个硬阻断：**workspace-planning 模式的 change 不能归档**。这种 change 跨多个仓库，归档到单个 repo 的 archive 目录没有意义。

## 三个技能的对比

| | propose | apply | archive |
|---|---|---|---|
| SKILL.md 步骤数 | 5 | 7 | 6 |
| 调用 `openspec instructions` | 是（每个 artifact） | 是（apply 状态） | 否 |
| 指令返回内容 | artifact 写作指南 + 模板 | 任务列表 + 进度 + 状态 | 不适用 |
| 核心动作 | 创建 Markdown 文件 | 写代码 + 更新 checkbox | 检查 + 同步 + 移动目录 |
| 循环机制 | 按依赖顺序创建 artifact | 逐个实现 task | 无循环 |
| 进度追踪 | artifact 文件是否存在 | checkbox 计数 | artifact + task 检查 |
| 可逆性 | 可重新生成 | 可改回 checkbox | 不可逆（目录移动） |
| 交互需求 | 低 | 中（遇问题暂停） | 高（多处确认） |

共同点：三个技能的 SKILL.md 都是 `openspec init` 生成的，都遵循"先查状态再执行"的模式。区别在于 propose 和 apply 用动态指令，archive 用静态指令；propose 创建文件，apply 写代码，archive 移动目录。

## 小结

archive 的底层实现围绕"安全归档"：

1. **SKILL.md**：6 步手册，重点是多层安全检查和交互式确认
2. **不使用动态指令**：操作是确定性的，SKILL.md 直接包含所有逻辑
3. **双层安全检查**：artifact 文件存在性（Step 2）+ task 完成度（Step 3），两者都是警告不阻断
4. **Delta Spec 同步**：Step 4 评估是否需要同步，用户决定是否执行
5. **归档操作**：日期前缀命名 + 目录移动，不可逆

三篇文章覆盖了 OpenSpec 三个核心技能的完整底层实现：propose 用三层提示词生成规划文件，apply 用状态感知的指令系统执行任务，archive 用安全检查和交互确认确保归档质量。
