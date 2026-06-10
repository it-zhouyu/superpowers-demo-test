> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## Core 工作流全景

前面我们执行了 `/opsx:propose`，创建了第一个 change。但那只是一小步。OPSX 的完整核心工作流是五个命令的组合：

```
/opsx:propose ──► /opsx:explore ──► /opsx:apply ──► /opsx:sync ──► /opsx:archive
```

注意：这不是固定单向流程。`explore` 可以在 `propose` 之前用（探索不清楚的需求），`sync` 可以在 `apply` 过程中随时执行（同步增量规格）。每个命令都是一个**动作**，不是一个必须按顺序经过的**阶段**。

不过，有一个隐含的依赖关系决定了命令的合理执行顺序：propose 生成四个 artifact（proposal → specs → design → tasks），apply 需要这些 artifact 存在才能工作，archive 需要任务完成才能归档。

## propose：从想法到提议

继续前面讲到的用户注册功能。在 Claude Code 中执行：

```
/opsx:propose "为现有 Express 项目添加用户注册功能，支持手机号验证码注册"
```

`propose` 是一条龙命令。它会在 `openspec/changes/add-user-registration/` 下一次性生成四个 artifact：

```
openspec/changes/add-user-registration/
├── proposal.md       # 为什么做、做什么
├── specs/            # Delta Spec（增量规格）
│   └── auth/
│       └── spec.md
├── design.md         # 技术方案
└── tasks.md          # 实现任务清单
```

### proposal.md — 意图与范围

AI 生成的 proposal.md 大致长这样：

```markdown
# Proposal: User Registration

## Intent
为现有 Express 项目添加手机号验证码注册功能，让新用户可以通过手机号创建账号。

## Scope
- POST /auth/send-code 发送验证码
- POST /auth/register 手机号验证码注册
- 验证码的生成、存储、校验逻辑
- 用户表的 phone_number 字段

## Approach
使用 Redis 存储验证码（5 分钟过期），bcrypt 哈希存储密码。
```

proposal 的作用是确认"我们到底要做什么"。它不是规格，而是 AI 和你之间的**意图对齐**文档。

### specs/auth/spec.md — 行为规格

这是 OpenSpec 生成的最核心的文件。它定义了"注册功能必须表现出什么行为"。AI 生成的 spec.md 大致长这样：

```markdown
# Delta for Auth

## ADDED Requirements

### Requirement: Phone Number Registration
The system SHALL allow new users to register with a phone number
and SMS verification code.

#### Scenario: Successful registration
- GIVEN a phone number not yet registered
- WHEN the user submits a valid verification code
- THEN a new user account is created
- AND the user is authenticated

#### Scenario: Duplicate phone number
- GIVEN a phone number already registered
- WHEN the user attempts to register
- THEN the system returns a 409 Conflict error

### Requirement: Verification Code Rate Limiting
The system SHALL limit verification code requests to one per 60 seconds per phone number.
```

这份文件有几个关键点：

1. **SHALL** 表示强制要求——AI 必须实现这个行为，不能跳过。后面还会介绍 MUST、SHOULD、MAY 等关键词，表示不同强度的要求。
2. **Scenario** 用 GIVEN/WHEN/THEN 描述可测试的场景——"在什么条件下、做了什么操作、应该得到什么结果"。
3. 文件开头写的是 `## ADDED Requirements`，表示这是**新增**的需求。如果项目里已经有 auth 的规格，还可能出现 `## MODIFIED Requirements`（修改已有需求）、`## REMOVED Requirements`（删除已有需求）。这种格式叫做 **Delta Spec（增量规格）**——只描述"这次改了什么"，不需要重复写已有的内容。

spec.md 是人先确认、AI 再执行的行为约束文件。你看了这份 spec，确认"对，注册就要有这些行为"，AI 才会按这个写代码。

### design.md — 技术方案

design.md 描述技术实现路径：

```markdown
# Design: User Registration

## Technical Approach
- 路由层：Express Router，两个端点
- 验证码服务：Redis SET + EXPIRE，6 位随机数字
- 数据层：Prisma User model，phone_number 唯一索引
- 安全：rate limiting（同号码 60 秒内限 1 次）
```

design 不是详细的代码设计，而是**架构层面的决策记录**。它告诉 AI "用什么技术、怎么组织"，避免 AI 每次都从零开始做技术选型。

### tasks.md — 实现清单

tasks.md 是可执行的检查列表：

```markdown
# Tasks

## 1. 数据层
- [ ] 1.1 添加 Prisma User model 的 phone_number 字段
- [ ] 1.2 创建数据库迁移

## 2. 验证码服务
- [ ] 2.1 实现 Redis 验证码生成和存储
- [ ] 2.2 实现验证码校验逻辑
- [ ] 2.3 添加 rate limiting 中间件

## 3. API 端点
- [ ] 3.1 实现 POST /auth/send-code
- [ ] 3.2 实现 POST /auth/register
- [ ] 3.3 添加请求参数校验
```

每个 task 前面有 checkbox（`[ ]`），apply 时 AI 会逐个完成并标记为 `[x]`。

### 四个 artifact 的依赖关系

propose 虽然一次性生成了四个文件，但它们之间有依赖链：

```
proposal ──► specs ──► design ──► tasks
```

proposal 定义意图，specs 基于意图写规格，design 基于规格定方案，tasks 基于方案拆任务。

### 依赖规则的来源：Schema

上面的依赖链不是硬编码的，而是由 **Schema** 定义的。Schema 是一个 YAML 文件，描述了一个工作流包含哪些 artifact 以及它们的依赖。

默认的 **spec-driven** Schema（`OpenSpec/schemas/spec-driven/schema.yaml`）核心部分：

```yaml
artifacts:
  - id: proposal
    generates: proposal.md
    requires: []
  - id: specs
    generates: "specs/**/*.md"
    requires: [proposal]
  - id: design
    generates: design.md
    requires: [proposal]
  - id: tasks
    generates: tasks.md
    requires: [specs, design]
```

每个 artifact 的 `requires` 列出它依赖的其他 artifact。

OpenSpec 内部的 `ArtifactGraph` 类读取这个 YAML，用拓扑排序算出构建顺序——先处理没有依赖的（proposal），再处理依赖已满足的（specs、design），最后处理 tasks。排序是确定性的：相同的 Schema 永远产生相同的顺序。

Schema 也可以自定义。比如团队想在 tasks 之后加一个 review 步骤，可以用 `openspec schema fork spec-driven review-first` 复制内置 Schema，然后添加 review-plan artifact。自定义 Schema 的完整流程可以单独演示。

理解了 Schema 定义依赖规则，后面的 Artifact 状态机和 Delta Spec 都建立在这个基础上。

## Delta Spec 格式详解

propose 生成的 `specs/auth/spec.md` 不是一个普通的规格文档，它是一个 **Delta Spec**——描述的是"相对于当前 specs 的增量修改"。

假设项目中已有一个 `openspec/specs/auth/spec.md`（之前 archive 留下的），Delta Spec 格式如下：

```markdown
# Delta for Auth

## ADDED Requirements

### Requirement: Phone Number Registration
The system SHALL allow new users to register with a phone number
and SMS verification code.

#### Scenario: Successful registration
- GIVEN a phone number not yet registered
- WHEN the user submits a valid verification code
- THEN a new user account is created
- AND the user is authenticated

#### Scenario: Duplicate phone number
- GIVEN a phone number already registered
- WHEN the user attempts to register
- THEN the system returns a 409 Conflict error

## MODIFIED Requirements

### Requirement: Session Timeout
The system SHALL expire sessions after 30 minutes of inactivity.
(Previously: 60 minutes)

## REMOVED Requirements

### Requirement: Remember Me Cookie
(Replaced by JWT-based token management)

## RENAMED Requirements

- FROM: `### Requirement: Password Hash`
- TO: `### Requirement: Credential Storage`
```

### 四种操作的含义

| 操作 | 含义 | 内容要求 |
|------|------|---------|
| **ADDED** | 新增需求 | 完整的 Requirement Block（含场景） |
| **MODIFIED** | 修改已有需求 | 完整的替换内容（整个 Block 替换） |
| **REMOVED** | 删除需求 | 只需要标题名称 |
| **RENAMED** | 重命名需求 | FROM/TO 配对 |

### 为什么用 Delta 而不是全量

如果每次修改都写完整 Spec，你的 change 里会出现大量和本次修改无关的已有内容。Delta 的好处是：

1. **聚焦变更**：只关注"这次改了什么"，不被已有内容干扰
2. **合并安全**：archive 时 OpenSpec 只修改 Delta 中提到的 Block，不动其他内容
3. **冲突可见**：多个 change 修改同一个 Spec 时，Delta 让冲突更容易发现
4. **历史可追溯**：每个 change 的 Delta 都保留在 archive 中，形成变更历史

如果是全新的能力域（项目里还没有 `openspec/specs/user/`），Delta 中只能用 ADDED，不能有 MODIFIED 或 RENAMED——因为没有已存在的东西可以修改。

## RFC 2119 与 WHEN/THEN

Delta Spec 中的需求描述不是随意写的，它使用了两种规范化表达。

### RFC 2119 关键词

OpenSpec 的 Spec 使用 RFC 2119 定义的四个关键词来标明需求强度：

| 关键词 | 含义 | 适用场景 |
|--------|------|---------|
| **SHALL** | 强制要求 | 核心功能行为，必须实现 |
| **MUST** | 无条件强制 | 安全、数据完整性相关，无例外 |
| **SHOULD** | 推荐但允许例外 | 最佳实践，可以有合理理由偏离 |
| **MAY** | 完全可选 | 非核心功能，实现不实现都行 |

上文的示例中已经用到了：

```
The system SHALL allow new users to register with a phone number...
```

"SHALL"表示这是一个强制需求——AI 在实现时必须支持手机号注册，不能跳过。

对比：

```
The system MAY support email registration as an alternative.
```

"MAY"意味着可选——AI 知道这不是必须的，可以根据实际情况决定是否实现。

这些关键词对 AI 的价值在于：它们给了 AI **判断优先级的依据**。SHALL/MUST 的需求必须完整实现，SHOULD 的需求尽量实现但可以协商，MAY 的需求可以暂缓。

### WHEN/THEN 场景

Spec 中的 Scenario 使用 GIVEN/WHEN/THEN 格式描述可测试的行为：

```markdown
#### Scenario: Successful registration
- GIVEN a phone number not yet registered
- WHEN the user submits a valid verification code
- THEN a new user account is created
- AND the user is authenticated
```

- **GIVEN**：前置条件（测试 setup）
- **WHEN**：触发动作（测试 input）
- **THEN**：预期结果（测试 assertion）
- **AND**：追加条件或结果

这不是测试代码，但它是**测试用例的自然语言表达**。AI 在 apply 实现代码时，可以参考这些场景来写测试用例。verify 命令也会用这些场景来检查实现是否覆盖了所有行为。

## Artifact 状态机

Artifact 就是 propose 生成的那些文件——proposal.md、spec.md、design.md、tasks.md。每个 artifact 有三种状态：**BLOCKED**（还不能创建）、**READY**（可以创建了）、**DONE**（已经创建好了）。

### 状态判定逻辑

逻辑很简单：检查 artifact 对应的文件是否存在。`proposal.md` 存在 → proposal 是 DONE，不存在 → 看依赖是否满足。

三个状态的判定规则：

| 状态 | 条件 | 含义 |
|------|------|------|
| **DONE** | 文件已存在 | artifact 已创建完成 |
| **READY** | 文件不存在，但所有依赖 artifact 已 DONE | 可以创建 |
| **BLOCKED** | 文件不存在，且有依赖 artifact 未 DONE | 不能创建 |

以 spec-driven schema（proposal → specs → design → tasks）为例：

**初始状态**（刚创建 change 目录，什么文件都没有）：
```
proposal: READY（无依赖）
specs:    BLOCKED（依赖 proposal）
design:   BLOCKED（依赖 specs）
tasks:    BLOCKED（依赖 design）
```

**proposal 完成后**：
```
proposal: DONE
specs:    READY（proposal 已完成）
design:   READY（proposal 已完成）
tasks:    BLOCKED（依赖 design）
```

### 用 CLI 查看状态

```bash
openspec status --change add-user-registration
```

输出：

```
Change: add-user-registration
Schema: spec-driven
Progress: 4/4 artifacts complete

[x] proposal
[x] specs
[x] design
[x] tasks
```

如果只有 proposal 和 specs 完成：

```
Change: add-user-registration
Schema: spec-driven
Progress: 2/4 artifacts complete

[x] proposal
[x] specs
[ ] design
[-] tasks (blocked by: design)
```

`[-]` 表示 blocked，括号里告诉你哪些依赖没满足。

### --json：Claude Code 的自动查询机制

上面的 `openspec status` 输出是人读的格式。实际上，当你在 Claude Code 中执行 `/opsx:apply` 或 `/opsx:archive` 时，Claude Code 会在后台自动执行 OpenSpec 的 CLI 命令，并在命令后面加上 `--json`，拿到结构化的 JSON 结果来判断下一步该做什么。

比如 Claude Code 想知道当前 change 的状态，它会自动执行：

```bash
openspec status --change add-user-registration --json
```

拿到的结果是一份 JSON：

```json
{
  "changeName": "add-user-registration",
  "schemaName": "spec-driven",
  "isComplete": false,
  "applyRequires": ["tasks"],
  "artifacts": [
    {"id": "proposal", "outputPath": "proposal.md", "status": "done"},
    {"id": "specs", "outputPath": "specs/**/*.md", "status": "done"},
    {"id": "design", "outputPath": "design.md", "status": "ready"},
    {"id": "tasks", "outputPath": "tasks.md", "status": "blocked", "missingDeps": ["design"]}
  ]
}
```

Claude Code 读取这份 JSON 后，看到 `design` 的 status 是 `ready`、`tasks` 的 status 是 `blocked`（缺少 design），就知道"design 还没创建，tasks 还不能做"，从而决定下一步该做什么。

你不需要手动加 `--json`——这是 Claude Code 和 OpenSpec 之间的自动协作机制。多个 CLI 命令都支持 `--json`：`openspec list --json`、`openspec show --json`、`openspec validate --all --json`、`openspec instructions --json`，Claude Code 会根据需要自动调用。

## apply：从规格到实现

所有 artifact 就绪后，执行：

```
/opsx:apply add-user-registration
```

apply 的工作方式：

1. 读取 `tasks.md`，识别所有未完成的 task（`[ ]` 标记）
2. 按顺序逐个实现：写代码、创建文件、运行测试
3. 每完成一个 task，将 `[ ]` 改为 `[x]`
4. 所有 task 完成后报告结果

实际对话可能像这样：

```
AI:  Implementing add-user-registration...

     Reading tasks.md:
     - [ ] 1.1 添加 Prisma User model 的 phone_number 字段
     - [ ] 1.2 创建数据库迁移
     - [ ] 2.1 实现 Redis 验证码生成和存储
     ...

     Working on 1.1: 添加 phone_number 字段...
     [Updates prisma/schema.prisma]

     ✓ 1.1 Complete

     Working on 1.2: 创建数据库迁移...
     [Runs npx prisma migrate dev]

     ✓ 1.2 Complete
     ...
     All tasks complete!
```

apply 过程中，AI 会参考 proposal.md 确认意图、参考 design.md 了解技术选型、参考 specs 确认行为规格。这就是为什么这些 artifact 需要在 apply 之前准备好。

如果 apply 中断了（比如网络问题、手动停止），再次执行 `/opsx:apply` 会从第一个未完成的 task 继续。状态保存在 `tasks.md` 的 checkbox 中。

## archive：合并规格并归档

apply 完成后，执行 `/opsx:archive` 做收尾。archive 会做两件事：**把 Delta Spec 合并到主 Spec**，然后把 change 目录移到归档目录。

```
/opsx:archive add-user-registration
```

archive 的完整流程：

```
1. 检查 artifact 完成状态
2. 检查 task 完成进度（警告未完成的 task）
3. 如果 Delta Spec 未同步，提示是否 sync
4. 执行 Delta 合并（ADDED → 追加，MODIFIED → 替换，REMOVED → 删除）
5. 将 change 目录移到 openspec/changes/archive/YYYY-MM-DD-add-user-registration/
```

第 3 步中的"同步 Delta Spec"就是 `/opsx:sync` 做的事情——把 change 中的 Delta Spec 合并到主 Spec。大多数情况下不需要单独执行 sync，archive 时会自动处理。

实际对话：

```
AI:  Archiving add-user-registration...

     Artifact status:
     ✓ proposal.md exists
     ✓ specs/ exists
     ✓ design.md exists
     ✓ tasks.md exists (8/8 tasks complete)

     Delta specs: Not yet synced
     → Sync now? (recommended)

You: Yes

AI:  ✓ Synced specs to openspec/specs/auth/spec.md
     ✓ Moved to openspec/changes/archive/2025-01-24-add-user-registration/

     Change archived successfully.
```

归档后，`openspec/specs/auth/spec.md` 中包含了新的需求。下一个 change 如果要修改 auth 相关内容，会基于这个更新后的 Spec 来写 Delta。

## 小结

本文走完了 OPSX 核心工作流的完整路径：

1. **propose**：一条龙生成 proposal、specs、design、tasks 四个 artifact
2. **Delta Spec 格式**：ADDED/MODIFIED/REMOVED/RENAMED 四种操作，描述增量修改
3. **RFC 2119**：SHALL/MUST/SHOULD/MAY 标明需求强度
4. **WHEN/THEN**：GIVEN/WHEN/THEN 描述可测试的行为场景
5. **Artifact 状态机**：BLOCKED/READY/DONE 三态，通过文件存在性判定
6. **Schema**：YAML 定义的 artifact 依赖规则，ArtifactGraph 通过拓扑排序确定构建顺序
7. **apply**：按 tasks.md 逐个实现，checkbox 跟踪进度
8. **archive**：合并 Delta Spec 到主 Spec，归档 change 目录；sync 是 archive 中的可选步骤
9. **--json**：Claude Code 自动查询 OpenSpec 状态的机制
