> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 起点：SKILL.md 文件

当 Claude Code 执行 propose 技能时，底层做的事很简单：找到对应的 SKILL.md 文件，然后按照里面的指令一步步执行。

这个文件位于 `.claude/skills/openspec-propose/SKILL.md`，由 `openspec init` 生成。

SKILL.md 分两部分：YAML frontmatter 和指令正文。frontmatter 中的 `description` 告诉 Claude Code 何时激活这个技能：

```yaml
name: openspec-propose
description: Propose a new change with all artifacts generated in one step.
  Use when the user wants to quickly describe what they want to build
  and get a complete proposal with design, specs, and tasks ready for implementation.
metadata:
  author: openspec
  version: "1.0"
```

当你的描述匹配"想构建一个新功能"时，Claude Code 自动加载这个技能的指令正文。

指令正文就是 Claude Code 的操作手册，完整内容如下（去掉了一些格式标记）：

```
Propose a new change - create the change and generate all artifacts in one step.

I'll create a change with artifacts:
- proposal.md (what & why)
- design.md (how)
- tasks.md (implementation steps)

When ready to implement, run /opsx:apply

Input: The user's request should include a change name (kebab-case) OR
a description of what they want to build.

Steps

1. If no clear input provided, ask what they want to build
   Use the AskUserQuestion tool (open-ended, no preset options) to ask:
   > "What change do you want to work on? Describe what you want to build or fix."
   From their description, derive a kebab-case name
   (e.g., "add user authentication" → add-user-auth).
   IMPORTANT: Do NOT proceed without understanding what the user wants to build.

2. Create the change directory
   > openspec new change "<name>"
   This creates a scaffolded change in the planning home with .openspec.yaml.

3. Get the artifact build order
   > openspec status --change "<name>" --json
   Parse the JSON to get:
   - applyRequires: array of artifact IDs needed before implementation (e.g., ["tasks"])
   - artifacts: list of all artifacts with their status and dependencies
   - planningHome, changeRoot, artifactPaths, and actionContext: path and scope context

4. Create artifacts in sequence until apply-ready
   Loop through artifacts in dependency order:

   a. For each artifact that is ready (dependencies satisfied):
      - Get instructions:
        > openspec instructions <artifact-id> --change "<name>" --json
      - The instructions JSON includes:
        - context: Project background (constraints for you - do NOT include in output)
        - rules: Artifact-specific rules (constraints for you - do NOT include in output)
        - template: The structure to use for your output file
        - instruction: Schema-specific guidance for this artifact type
        - resolvedOutputPath: Resolved path to write the artifact
        - dependencies: Completed artifacts to read for context
      - Read any completed dependency files for context
      - Create the artifact file using template as the structure
        and write it to resolvedOutputPath
      - Apply context and rules as constraints - but do NOT copy them into the file
      - Show brief progress: "Created <artifact-id>"

   b. Continue until all applyRequires artifacts are complete
      - After creating each artifact, re-run openspec status --change "<name>" --json
      - Check if every artifact ID in applyRequires has status: "done"
      - Stop when all applyRequires artifacts are done

   c. If an artifact requires user input (unclear context):
      - Use AskUserQuestion tool to clarify
      - Then continue with creation

5. Show final status
   > openspec status --change "<name>"

Output

After completing all artifacts, summarize:
- Change name and location
- List of artifacts created with brief descriptions
- What's ready: "All artifacts created! Ready for implementation."
- Prompt: "Run /opsx:apply or ask me to implement to start working on the tasks."

Artifact Creation Guidelines

- Follow the instruction field from openspec instructions for each artifact type
- The schema defines what each artifact should contain - follow it
- Read dependency artifacts for context before creating new ones
- Use template as the structure for your output file - fill in its sections
- IMPORTANT: context and rules are constraints for YOU, not content for the file
  - Do NOT copy context, rules, project_context blocks into the artifact
  - These guide what you write, but should never appear in the output

Guardrails

- Create ALL artifacts needed for implementation (as defined by schema's apply.requires)
- Always read dependency artifacts before creating a new one
- If context is critically unclear, ask the user - but prefer making reasonable
  decisions to keep momentum
- If a change with that name already exists, ask if user wants to continue it
  or create a new one
- Verify each artifact file exists after writing before proceeding to next
```

这份操作手册的核心设计：它不告诉 Claude Code "proposal 应该怎么写"，而是告诉 Claude Code "去调用 CLI 拿指令，按指令写"。实际的写作规则来自 `openspec instructions` 返回的 `instruction` 字段。

下面用一个具体的例子来走完这 5 步。假设你说：

> "帮我添加用户注册功能，支持手机号验证码注册"

## Step 1：确认输入，推导 change 名称

Claude Code 从你的描述中推导出一个 kebab-case 的 change 名称。"添加用户注册功能" → `add-user-registration`。

kebab-case 是一种命名风格：所有单词小写，用短横线连接。比如 `add-user-registration`、`send-code`。目录名不能有空格，kebab-case 在文件路径中最易读。

如果你没有给出明确描述（比如只说"帮我搞一下"），Claude Code 会用 `AskUserQuestion` 工具追问："What change do you want to work on?"，拿到描述后再推导名称。

**这一步的产出**：change 名称 `add-user-registration`。

## Step 2：创建 change 目录

Claude Code 执行 CLI 命令：

```bash
openspec new change "add-user-registration"
```

这个命令在 `openspec/changes/` 下创建一个目录，并生成一个 `.openspec.yaml` 元数据文件：

```
openspec/changes/add-user-registration/
└── .openspec.yaml
```

`.openspec.yaml` 记录了 change 的元信息（创建时间、使用的 Schema 名称等），后续步骤会读取它。

**这一步的产出**：`openspec/changes/add-user-registration/` 目录 + `.openspec.yaml` 元数据文件。

## Step 3：获取 artifact 构建顺序

Claude Code 执行 CLI 命令：

```bash
openspec status --change "add-user-registration" --json
```

这个命令会解析 Schema（默认是 spec-driven），构建依赖图，检查当前哪些 artifact 文件已存在，然后返回一份 JSON。此时目录里只有 `.openspec.yaml`，所有 artifact 都还没创建：

```json
{
  "changeName": "add-user-registration",
  "schemaName": "spec-driven",
  "isComplete": false,
  "applyRequires": ["tasks"],
  "artifacts": [
    { "id": "proposal", "status": "ready", "missingDeps": [] },
    { "id": "specs",    "status": "blocked", "missingDeps": ["proposal"] },
    { "id": "design",   "status": "blocked", "missingDeps": ["proposal"] },
    { "id": "tasks",    "status": "blocked", "missingDeps": ["specs", "design"] }
  ],
  "changeRoot": "openspec/changes/add-user-registration"
}
```

关键字段：

- `applyRequires: ["tasks"]` — Schema 声明 apply 阶段需要 tasks 这个 artifact 完成才行。所以 propose 的目标是把 tasks 创建出来，而 tasks 依赖 specs 和 design，所以需要先把 proposal → specs → design → tasks 全部创建完
- `artifacts` — 每个 artifact 的状态：`ready`（可以创建）或 `blocked`（还有依赖未完成）
- `changeRoot` — change 目录的路径，后续创建文件都在这个目录下

**这一步的产出**：artifact 列表 + 依赖关系 + 状态。Claude Code 知道了"需要创建 proposal、specs、design、tasks 四个 artifact，按依赖顺序来"。

## Step 4：按依赖顺序逐个创建 artifact

这是最核心的步骤。Claude Code 按依赖顺序处理每个 `ready` 状态的 artifact：

1. 先创建 proposal（无依赖，ready）
2. 创建 specs 和 design（都依赖 proposal，proposal 完成后变为 ready）
3. 最后创建 tasks（依赖 specs 和 design，两者都完成后才 ready）

每创建一个 artifact 之前，Claude Code 先调用 `openspec instructions` 获取创建指令。这个指令告诉 Claude Code "这个 artifact 怎么写、用什么模板、有什么规则约束"。下面逐个分析。

### 4.1 创建 proposal

Claude Code 执行：

```bash
openspec instructions proposal --change "add-user-registration" --json
```

这条命令背后做了什么？

1. 解析 Schema（从 `.openspec.yaml` 或项目配置中拿到 schema 名称 `spec-driven`）
2. 从 schema.yaml 中找到 `id: proposal` 的 artifact 定义
3. 读取模板文件 `templates/proposal.md`
4. 检查依赖（proposal 没有依赖，`dependencies` 为空）
5. 检查完成后会解锁哪些 artifact（proposal 完成后解锁 specs 和 design）
6. 读取项目配置 `openspec/config.yaml` 中的 `context` 和 `rules`
7. 把以上信息组装成一份 JSON 返回

schema.yaml 和模板文件都不在你当前项目里，而是按三级查找：先查项目本地 `openspec/schemas/`，再查用户全局 `~/.local/share/openspec/schemas/`，最后查 OpenSpec npm 包内置的 `schemas/spec-driven/`。你当前项目没有自定义 Schema，所以走的是包内置路径

返回的 JSON：

```json
{
  "changeName": "add-user-registration",
  "artifactId": "proposal",
  "schemaName": "spec-driven",
  "resolvedOutputPath": "openspec/changes/add-user-registration/proposal.md",
  "instruction": "Create the proposal document that establishes WHY this change is needed.\n\nSections:\n- Why: 1-2 sentences on the problem or opportunity.\n- What Changes: Bullet list of changes.\n- Capabilities: Identify which specs will be created or modified.\n- Impact: Affected code, APIs, dependencies, or systems.",
  "context": "This is an Express + TypeScript project...",
  "rules": null,
  "template": "## Why\n<!-- Explain the motivation... -->\n\n## What Changes\n<!-- Describe what will change... -->\n\n## Capabilities\n### New Capabilities\n- `<name>`: <brief description>\n\n### Modified Capabilities\n- `<existing-name>`: <what requirement is changing>\n\n## Impact\n<!-- Affected code, APIs, dependencies, systems -->",
  "dependencies": [],
  "unlocks": ["design", "specs"]
}
```

各字段的作用：

| 字段 | 作用 |
|------|------|
| `instruction` | 来自 schema.yaml 中 proposal artifact 的 `instruction` 字段，告诉 Claude Code 这个 artifact 要写什么内容、注意什么 |
| `template` | 来自 `schemas/spec-driven/templates/proposal.md`，定义输出文件的骨架结构。Claude Code 按这个骨架填写 |
| `context` | 来自 `openspec/config.yaml` 的 `context` 字段，项目背景信息。约束 Claude Code 的行为，但不能写入文件 |
| `rules` | 来自 `openspec/config.yaml` 的 `rules.proposal`，artifact 级别的规则。约束 Claude Code 的行为，不能写入文件 |
| `dependencies` | 前置 artifact 的路径和状态。Claude Code 需要读取这些文件作为参考 |
| `unlocks` | 完成后会解锁哪些 artifact，帮助 Claude Code 理解后续流程 |
| `resolvedOutputPath` | 文件写入路径 |

Claude Code 拿到这份 JSON 后，按 `template` 骨架、遵循 `instruction` 的指导、参考 `context` 和 `rules` 的约束，生成 proposal.md 文件，写入 `resolvedOutputPath` 指定的路径。

这里有一个关键细节：这份 JSON 是通过 Bash 工具的返回结果回到大模型的对话上下文中的。也就是说，`openspec instructions` 的本质是**动态组装一份提示词，然后交给大模型去生成内容**。大模型不是凭空写 proposal，而是拿到一份完整的"写作指南"（instruction + template + context + rules）后再写。

生成的 `proposal.md` 大致内容：

```markdown
## Why

现有系统缺少用户注册功能，需要支持手机号验证码注册方式，
让新用户可以自助创建账号。

## What Changes

- 新增 POST /auth/send-code 端点，发送短信验证码
- 新增 POST /auth/register 端点，手机号验证码注册
- User 表新增 phone_number 字段
- 集成 Redis 存储验证码（5 分钟过期）

## Capabilities

### New Capabilities
- `auth`: 用户注册与验证码管理

### Modified Capabilities
（无）

## Impact

- 依赖新增：Redis 连接、短信服务商 SDK
- 数据库：User 表结构变更，需要迁移
- API：新增两个公开端点
```

注意：`context` 和 `rules` 不会出现在文件中——它们只是约束 Claude Code 的行为。只有 `template` 骨架中的内容才是最终输出。

**这一步的产出**：`openspec/changes/add-user-registration/proposal.md` 文件。

### 4.2 创建 specs

proposal 完成后，Claude Code 重新执行 `openspec status --change "add-user-registration" --json`，发现 proposal 已经是 `done`，specs 和 design 变为 `ready`，tasks 仍然是 `blocked`。

Claude Code 先处理 specs。执行：

```bash
openspec instructions specs --change "add-user-registration" --json
```

返回的 JSON：

```json
{
  "artifactId": "specs",
  "resolvedOutputPath": "openspec/changes/add-user-registration/specs/**/*.md",
  "instruction": "Create specification files that define WHAT the system should do.\n\nCreate one spec file per capability listed in the proposal's Capabilities section.\n\nDelta operations:\n- ADDED Requirements: New capabilities\n- MODIFIED Requirements: Changed behavior\n- REMOVED Requirements: Deprecated features\n- RENAMED Requirements: Name changes\n\nFormat:\n- Each requirement: ### Requirement: <name>\n- Use SHALL/MUST for normative requirements\n- Each scenario: #### Scenario: <name> with WHEN/THEN format\n- Every requirement MUST have at least one scenario.",
  "template": "## ADDED Requirements\n\n### Requirement: <!-- requirement name -->\n\n#### Scenario: <!-- scenario name -->\n- **WHEN** <!-- condition -->\n- **THEN** <!-- expected outcome -->",
  "dependencies": [
    { "id": "proposal", "done": true, "path": "proposal.md" }
  ],
  "unlocks": ["tasks"]
}
```

和 proposal 的指令对比，有几个关键区别：

1. `instruction` 不同——proposal 的 instruction 说"write WHY"，specs 的 instruction 说"write WHAT"，并且详细说明了 Delta Spec 的四种操作格式（ADDED/MODIFIED/REMOVED/RENAMED）
2. `template` 不同——proposal 用的是 proposal.md 模板，specs 用的是 spec.md 模板
3. `dependencies` 不同——specs 依赖 proposal（已完成），Claude Code 会先读取 proposal.md 了解意图

Claude Code 读取 proposal.md，知道 capabilities 中列出了 `auth`（新增能力）。按 instruction 的指导，为 `auth` 创建一个 spec 文件：

```markdown
## ADDED Requirements

### Requirement: Phone Number Registration
The system SHALL allow new users to register with a phone number
and SMS verification code.

#### Scenario: Successful registration
- **WHEN** user submits a valid phone number and verification code
- **THEN** a new user account is created with the phone number

#### Scenario: Duplicate phone number
- **WHEN** user submits a phone number that is already registered
- **THEN** the system returns a 409 Conflict error

### Requirement: Verification Code Rate Limiting
The system SHALL limit verification code requests to one per 60 seconds
per phone number.

#### Scenario: Rate limit exceeded
- **WHEN** user requests a verification code within 60 seconds of the previous request
- **THEN** the system returns a 429 Too Many Requests error
```

写入 `openspec/changes/add-user-registration/specs/auth/spec.md`。

**这一步的产出**：`specs/auth/spec.md` — 定义了注册功能必须表现出什么行为。

### 4.3 创建 design

和 specs 一样，design 也依赖 proposal，此时 proposal 已经 done。Claude Code 执行：

```bash
openspec instructions design --change "add-user-registration" --json
```

返回的 JSON：

```json
{
  "artifactId": "design",
  "resolvedOutputPath": "openspec/changes/add-user-registration/design.md",
  "instruction": "Create the design document that explains HOW to implement the change.\n\nSections:\n- Context: Background, current state, constraints\n- Goals / Non-Goals: What this design achieves and excludes\n- Decisions: Key technical choices with rationale\n- Risks / Trade-offs: Known limitations\n\nFocus on architecture and approach, not line-by-line implementation.",
  "template": "## Context\n<!-- Background and current state -->\n\n## Goals / Non-Goals\n**Goals:**\n<!-- What this design aims to achieve -->\n**Non-Goals:**\n<!-- What is explicitly out of scope -->\n\n## Decisions\n<!-- Key design decisions and rationale -->\n\n## Risks / Trade-offs\n<!-- Known risks and trade-offs -->",
  "dependencies": [
    { "id": "proposal", "done": true, "path": "proposal.md" }
  ],
  "unlocks": ["tasks"]
}
```

design 的 instruction 告诉 Claude Code：写"怎么实现"，不是"为什么做"（那是 proposal）也不是"做到什么程度"（那是 specs），而是技术选型和架构决策。

Claude Code 读取 proposal.md，生成 design.md：

```markdown
## Context

现有 Express + TypeScript 项目，使用 Prisma ORM 和 PostgreSQL。
没有短信服务商集成，需要新增。

## Goals / Non-Goals

**Goals:**
- 手机号验证码注册流程
- 验证码的生成、存储、校验
- 60 秒内同号码限发一次

**Non-Goals:**
- 邮箱注册（后续迭代）
- 第三方 OAuth 登录

## Decisions

- **验证码存储**：Redis SET + EXPIRE（5 分钟），选 Redis 是因为天然支持 TTL
- **密码处理**：bcrypt 哈希，业界标准
- **短信服务商**：阿里云 SMS SDK，团队已有账号
- **数据库**：Prisma User model 新增 phone_number 字段，唯一索引

## Risks / Trade-offs

- Redis 不可用时验证码功能整体不可用 → 可考虑降级方案（内存缓存）
- 短信到达率依赖第三方 → 需要重试机制和错误提示
```

**这一步的产出**：`design.md` — 技术选型和架构决策。

### 4.4 创建 tasks

specs 和 design 都完成后，tasks 的依赖满足了。Claude Code 执行：

```bash
openspec instructions tasks --change "add-user-registration" --json
```

返回的 JSON：

```json
{
  "artifactId": "tasks",
  "resolvedOutputPath": "openspec/changes/add-user-registration/tasks.md",
  "instruction": "Create the task list that breaks down the implementation work.\n\nGuidelines:\n- Group related tasks under ## numbered headings\n- Each task MUST be a checkbox: - [ ] X.Y Task description\n- Tasks should be small enough to complete in one session\n- Order tasks by dependency\n\nReference specs for what needs to be built, design for how to build it.",
  "template": "## 1. <!-- Task Group Name -->\n\n- [ ] 1.1 <!-- Task description -->\n- [ ] 1.2 <!-- Task description -->",
  "dependencies": [
    { "id": "specs",  "done": true, "path": "specs/**/*.md" },
    { "id": "design", "done": true, "path": "design.md" }
  ],
  "unlocks": []
}
```

tasks 的特殊之处：

1. 它依赖两个 artifact（specs 和 design），Claude Code 需要同时读取两者
2. instruction 强调了 checkbox 格式（`- [ ]`）——这是 apply 阶段追踪进度的基础
3. `unlocks` 为空——tasks 是最后一个 artifact，完成后整个 propose 流程结束

Claude Code 读取 specs 和 design，生成 tasks.md：

```markdown
## 1. 数据层

- [ ] 1.1 添加 Prisma User model 的 phone_number 字段
- [ ] 1.2 创建数据库迁移

## 2. 验证码服务

- [ ] 2.1 实现 Redis 验证码生成和存储
- [ ] 2.2 实现验证码校验逻辑
- [ ] 2.3 添加 rate limiting 中间件（60 秒同号码限 1 次）

## 3. API 端点

- [ ] 3.1 实现 POST /auth/send-code
- [ ] 3.2 实现 POST /auth/register
- [ ] 3.3 添加请求参数校验
```

**这一步的产出**：`tasks.md` — 实现清单，每个 task 用 checkbox 标记。

### 4.5 检查是否全部完成

tasks 创建后，Claude Code 最后执行一次 `openspec status --change "add-user-registration" --json`：

```json
{
  "isComplete": true,
  "applyRequires": ["tasks"],
  "artifacts": [
    { "id": "proposal", "status": "done" },
    { "id": "specs",    "status": "done" },
    { "id": "design",   "status": "done" },
    { "id": "tasks",    "status": "done" }
  ]
}
```

`applyRequires` 中的 tasks 状态为 `done`，所有 artifact 都创建完毕。

## Step 5：展示最终状态

Claude Code 执行 `openspec status --change "add-user-registration"`（不带 `--json`），拿到人可读的输出：

```
Change: add-user-registration
Schema: spec-driven
Progress: 4/4 artifacts complete

[x] proposal
[x] specs
[x] design
[x] tasks
```

然后向用户展示摘要：

```
All artifacts created! Ready for implementation.

Created:
- proposal.md: 用户注册功能的意图和范围
- specs/auth/spec.md: 注册行为的规格定义
- design.md: 技术选型（Redis + 阿里云 SMS）
- tasks.md: 8 个实现任务

Run /opsx:apply to start implementing.
```

## 指令是怎么生成的：generateInstructions() 的内部逻辑

前面每创建一个 artifact 时都调用了 `openspec instructions <artifact-id> --json`。这一节分析这条命令背后的 `generateInstructions()` 函数是怎么组装出那份 JSON 的。

```
openspec instructions proposal --change "add-user-registration" --json
│
├─ 1. loadChangeContext()
│     ├─ 解析 Schema：从 .openspec.yaml 中读到 schema 名称 "spec-driven"
│     ├─ 加载 schema.yaml：解析出 artifact 列表和依赖关系
│     ├─ 构建 ArtifactGraph：内存中的依赖图
│     └─ detectCompleted()：扫描文件系统，检查哪些文件已存在
│
├─ 2. 从 ArtifactGraph 中找到 id="proposal" 的 artifact 定义
│     └─ 拿到 generates、template、instruction、requires 等字段
│
├─ 3. loadTemplate("spec-driven", "proposal.md", projectRoot)
│     └─ 读取 schemas/spec-driven/templates/proposal.md 的内容
│
├─ 4. getDependencyInfo()
│     └─ proposal 的 requires=[]，所以 dependencies 为空
│
├─ 5. getUnlockedArtifacts()
│     └─ 查找哪些 artifact 依赖 proposal → specs 和 design
│
├─ 6. readProjectConfig()
│     ├─ 读取 openspec/config.yaml
│     ├─ 提取 context 字段（项目背景）
│     └─ 提取 rules.proposal 字段（artifact 级规则）
│
└─ 7. 组装返回 JSON
      ├─ template: 第 3 步读到的模板内容
      ├─ instruction: 第 2 步拿到的 schema.yaml 中的 instruction 字段
      ├─ context: 第 6 步拿到的项目背景
      ├─ rules: 第 6 步拿到的规则
      ├─ dependencies: 第 4 步计算的依赖信息
      └─ unlocks: 第 5 步计算的解锁信息
```

核心思路：`instruction` 和 `template` 来自 Schema 定义（告诉 Claude Code "写什么、怎么写"），`context` 和 `rules` 来自项目配置（告诉 Claude Code "受什么约束"），`dependencies` 和 `unlocks` 来自依赖图计算（告诉 Claude Code "参考什么、影响什么"）。这些信息来自不同的数据源，在这一步合并成一份完整的指令。

"动态"的含义也在这里——每次调用时根据当前状态（哪些 artifact 已完成、项目配置是什么）实时组装。比如创建 specs 时 `dependencies` 会显示 proposal 已完成（`done: true`），而创建 tasks 时会显示 specs 和 design 都已完成。

## 每个 artifact 的指令差异

四个 artifact 的 instruction 来自 schema.yaml 中各自的 `instruction` 字段，内容完全不同：

| Artifact | instruction 的核心内容 | template 骨架 |
|----------|----------------------|--------------|
| **proposal** | 写"为什么做"——Why、What Changes、Capabilities、Impact | proposal.md |
| **specs** | 写"做到什么程度"——Delta Spec 四种操作、RFC 2119 关键词、WHEN/THEN 场景 | spec.md |
| **design** | 写"怎么实现"——Context、Goals、Decisions、Risks | design.md |
| **tasks** | 写"做什么步骤"——checkbox 格式、按依赖排序、参照 specs 和 design | tasks.md |

这也解释了为什么 SKILL.md 不直接告诉 Claude Code "proposal 应该怎么写"——因为不同 Schema 的 instruction 可能完全不同。SKILL.md 只说"去调 CLI 拿指令"，实际的写作规则来自 `openspec instructions` 返回的 `instruction` 字段。

## 小结

propose 技能的执行流程：

1. Claude Code 加载 `.claude/skills/openspec-propose/SKILL.md`，拿到 5 步操作手册
2. 从用户描述推导 change 名称（如 `add-user-registration`）
3. 用 `openspec new change` 创建 change 目录
4. 用 `openspec status` 获取 artifact 列表和依赖关系
5. 按依赖顺序逐个创建 artifact，每个先调 `openspec instructions` 拿指令再写文件
6. 每个 artifact 的指令来自 `generateInstructions()` 的实时组装——模板来自 Schema、约束来自项目配置、依赖来自 ArtifactGraph 计算

Claude Code 的工作模式：读操作手册 → 调 CLI → 拿指令 → 按模板写文件 → 检查状态 → 下一个。不是自由创作，而是按指令逐步执行。
