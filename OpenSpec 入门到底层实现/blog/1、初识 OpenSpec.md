> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## OpenSpec 是什么

假设你正在用 Claude Code 开发一个用户注册功能。没有 OpenSpec 时，流程是这样的：

```
你：帮我做用户注册
AI：好的，开始写代码...（直接动手）
你：等等，我要的是手机号注册，你怎么做了邮箱注册？
AI：抱歉，我重写...
你：验证码为什么是 4 位的？我要 6 位
AI：好的，再改...
你：为什么没有限频？一个号码 60 秒内只能发一次验证码
AI：...
```

反复几轮后终于凑出能用的代码。问题出在哪？**AI 和你对"用户注册"的理解从没对齐过**。你说"用户注册"，脑子里想的是手机号 + 验证码 + 限频，但 AI 不知道这些细节，它按自己的理解直接写代码了。

OpenSpec 的做法是：**在你和 AI 之间插入一个明确的中间步骤**。不是直接从"想法"跳到"代码"，而是先花一分钟把想法写成结构化的描述，让 AI 在写代码之前就知道你要什么：

```
你：帮我做用户注册，支持手机号验证码
    ↓
OpenSpec 生成一份行为描述：
    - 注册必须用手机号 + 6 位数字验证码
    - 验证码 5 分钟内有效
    - 同一手机号 60 秒内只能发一次
    - 手机号已注册时返回 409 错误
    ↓
AI 按这份描述写代码（不再是猜你要什么）
    ↓
完成后，这份描述保存下来，以后改注册功能时 AI 可以参考
```

这份行为描述就是 **Spec（规格）**。Spec 是人和 AI 共同确认的功能约束：你先看 Spec 确认"对，这就是我要的"，AI 再按 Spec 写代码。双方对着同一份结构化描述工作，不会各想各的。

一句话概括：**OpenSpec 让 AI 编码从"猜你要什么"变成"按规格写"**。

## 四条设计原则

OpenSpec 怎么用，取决于它的设计原则。理解这四条原则，后面的命令为什么这样设计就清楚了。

**原则一：规格可以改，不是写完就锁死（Fluid, not rigid）**

传统文档写完就定格了。但实际开发中，需求会变——今天定了 6 位验证码，明天产品说要改成 4 位。OpenSpec 允许你随时修改已有的规格，只需要描述"改了什么"（比如把验证码位数从 6 改成 4），OpenSpec 会自动更新原来的规格文件。规格跟着项目一起演化，不会变成过时的负担。

**原则二：不用提前想清楚所有细节（Iterative, not waterfall）**

你不需要一开始就把注册功能的每个细节都想好。可以先写一个大概的想法（"做手机号注册"），然后逐步细化（先定验证码规则，再定限频策略，再拆开发任务）。每一步都可以回头改前面的内容。不存在"必须按顺序规划完才能开始写代码"的限制。

**原则三：上手只需要 5 个命令（Easy, not complex）**

OpenSpec 的核心操作只有 5 个：创建提议、探索代码、执行实现、同步规格、归档收尾。

**原则四：随时可以加入已有项目（Brownfield-first）**

Brownfield（棕地项目）指的是已经有代码在跑的项目，跟 Greenfield（绿地项目，从零开始的新项目）相对。OpenSpec 优先支持棕地项目——你的项目已经写了一半？没问题。不需要从零开始，也不需要重构现有代码。一条 `openspec init` 命令就能接入，它会自动检测你正在用的 AI 工具（Claude Code、Cursor 等），无缝衔接。

需要注意：OpenSpec 并不会自动从你现有代码里推导出规格。接入后 `openspec/specs/` 目录一开始是空的。规格是逐步积累的——你每做一个新功能，通过 propose → archive 走完一轮，`openspec/specs/` 里就多了一份规格。以后再改相关功能时，AI 就有已有的规格可以参考了。所以"支持棕地项目"的意思是接入门槛低、不需要前置准备，不是说它能自动理解你现有的代码逻辑。

## 安装与初始化

安装只需要一条命令：

```bash
npm install -g @fission-ai/openspec
```

安装完成后，在你的项目根目录执行：

```bash
openspec init
```

你会看到一个交互式界面，让你选择要配置哪些 AI 工具（Claude Code、Cursor、Windsurf 等）。选择完成后，OpenSpec 会在项目中创建必要的目录和配置文件。

如果你在 CI/CD 中使用，可以用非交互模式：

```bash
# 指定工具
openspec init --tools claude,cursor

# 配置所有支持的工具
openspec init --tools all

# 跳过工具配置
openspec init --tools none
```

初始化完成后，项目根目录会多出一个 `openspec/` 目录。下面来看看这个目录里有什么。

## 目录结构与文件职责

执行 `openspec init` 后，项目结构如下：

```
project/
├── openspec/
│   ├── specs/              # 规格文件（Source of Truth）
│   │   └── auth/
│   │       └── spec.md     # 某个能力域的完整规格
│   ├── changes/            # 提议中的修改
│   │   └── add-registration/
│   │       ├── proposal.md
│   │       ├── design.md
│   │       ├── tasks.md
│   │       └── specs/      # Delta Spec（增量规格）
│   │           └── auth/
│   │               └── spec.md
│   └── config.yaml         # 项目配置
├── .claude/
│   ├── skills/             # Claude Code Skills
│   │   ├── openspec-propose/
│   │   │   └── SKILL.md
│   │   └── ...
│   └── commands/
│       └── opsx/
│           └── propose.md  # /opsx:propose 命令
└── ...
```

三个核心目录的职责：

**`openspec/specs/`** — 项目的**规格来源（Source of Truth）**。每个子目录代表一个能力域（如 `auth`、`user`），里面的 `spec.md` 定义了该能力域的完整规格。这是 AI 写代码时必须参照的行为约束。新建项目时这个目录是空的，随着你 archive 完成的 change，Spec 会逐步积累。

**`openspec/changes/`** — 正在进行中的**修改提议**。每个子目录是一个 change，包含 proposal、design、tasks 等工作产物。change 完成后会通过 archive 合并到 specs 中，然后移入 `changes/archive/` 目录。

**`openspec/config.yaml`** — 项目级配置，记录 schema 选择、项目描述等元信息。通常你不需要手动编辑它。

另外，工具目录（如 `.claude/skills/` 和 `.claude/commands/`）是 OpenSpec 根据你选择的 AI 工具自动生成的，不要手动修改。运行 `openspec update` 可以在升级 CLI 后重新生成这些文件。

## Profile 与 Delivery 模式

`openspec init` 生成的 Skills 和 Commands 数量取决于两个全局配置：**Profile** 和 **Delivery**。

### Profile：决定"哪些工作流"

Profile 控制你使用的工作流集合。查看当前配置：

```bash
openspec config list
```

OpenSpec 提供两种 Profile：

| Profile | 工作流 | 适用场景 |
|---------|--------|----------|
| **core**（默认） | propose, explore, apply, sync, archive（5 个） | 大多数项目，简洁够用 |
| **custom** | 可选全部 11 个工作流 | 需要精细控制的高级用户 |

源码中这个逻辑非常直接（`OpenSpec/src/core/profiles.ts:42`）：

```typescript
export function getProfileWorkflows(
  profile: Profile,
  customWorkflows?: string[]
): readonly string[] {
  if (profile === 'custom') {
    return customWorkflows ?? [];
  }
  return CORE_WORKFLOWS; // ['propose', 'explore', 'apply', 'sync', 'archive']
}
```

切换 Profile：

```bash
# 交互式配置
openspec config profile

# 快速切换到 core
openspec config profile core
```

切换后需要运行 `openspec update` 来更新项目中的 Skills 和 Commands。

### Delivery：决定"怎么交付"

Delivery 控制工作流以什么形式安装到 AI 工具中：

| Delivery 模式 | 安装内容 | 适用场景 |
|---------------|---------|---------|
| **both**（默认） | Skills + Commands | 推荐，两种方式都可用 |
| **skills** | 只安装 Skills | AI 工具只支持 Skill 机制时 |
| **commands** | 只安装 Commands | 只需要斜杠命令，不需要 Skill |

修改 Delivery：

```bash
openspec config profile
# 选择 "Change delivery only"
# 然后选择想要的模式
```

这两个维度组合起来决定了最终的安装结果。例如 core Profile + both Delivery = 5 个 Skill + 5 个 Command，而 custom Profile + skills Delivery = 最多 11 个 Skill，不安装 Command。

## OPSX 命令全景

OpenSpec 的核心工作流通过两种方式调用：Skill（如 `/openspec-propose`）和 Command（如 `/opsx:propose`）。两种方式效果相同，只是调用形式不同。

### Core 工作流（5 个命令）

| 命令 | 作用 | 产物 |
|------|------|------|
| `propose` | 从自然语言描述生成结构化 Proposal | `proposal.md` |
| `explore` | 需求不明确时先调查代码和已有 Spec | 分析结果 |
| `apply` | 按 Tasks 执行实现 | 代码文件 |
| `sync` | 将 Delta Spec 合并到主 Spec（不归档） | 更新后的 `specs/` |
| `archive` | 验证、合并 Spec、归档 Change | 归档到 `archive/` |

这是默认 core Profile 提供的完整流程：大多数情况下只需要 propose → apply → archive 三步。explore 是可选的，用在需求不明确、想先调查的时候；sync 也是可选的，archive 时会自动处理规格合并。

### 扩展工作流（6 个命令）

通过切换到 custom Profile 可以启用：

| 命令 | 作用 |
|------|------|
| `new` | 手动创建新 Change 目录 |
| `continue` | 继续一个已有的 Change |
| `ff` | 快速前进：跳过中间步骤直接到 Tasks |
| `bulk-archive` | 批量归档多个 Change |
| `verify` | 验证实现是否符合 Spec |
| `onboard` | 引导新成员了解项目 Spec |

大多数项目用 core 的 5 个命令就够了。扩展命令适合团队协作、复杂变更管理、快速迭代等场景。

## AI 工具集成矩阵

OpenSpec 不是某个 AI 工具的专属插件。它通过一套统一的 Skill/Command 生成机制，同时支持 25+ 种 AI 编码工具。

init 时的工具选择界面背后是 `getAvailableTools()`（`OpenSpec/src/core/available-tools.ts`），它会检测项目目录中已有的 AI 工具配置文件（如 `.claude/` 目录代表 Claude Code，`.cursor/` 代表 Cursor），自动推荐匹配的工具。

集成方式分两种：

**Skills**：安装到各工具的 skills 目录，如 `.claude/skills/openspec-propose/SKILL.md`。AI 工具自动加载这些 Skill 作为行为指令。

**Commands**：安装到各工具的 commands 目录，以斜杠命令形式提供，如 `.claude/commands/opsx/propose.md`，对应 `/opsx:propose` 命令。

部分工具的路径示例：

| 工具 | Skills 路径 | Commands 路径 |
|------|-----------|--------------|
| Claude Code | `.claude/skills/openspec-*/SKILL.md` | `.claude/commands/opsx/<id>.md` |
| Cursor | `.cursor/skills/openspec-*/SKILL.md` | `.cursor/commands/opsx-<id>.md` |
| Windsurf | `.windsurf/skills/openspec-*/SKILL.md` | `.windsurf/workflows/opsx-<id>.md` |
| GitHub Copilot | `.github/skills/openspec-*/SKILL.md` | `.github/prompts/opsx-<id>.prompt.md` |

完整的工具列表有 30 个：Amazon Q、Antigravity、Auggie、Cline、Codex、Continue、Crush、Gemini CLI、Kilo Code、Kiro、Lingma、RooCode、Trae 等。每个工具的 Skills 和 Commands 内容相同，只是安装路径和调用方式不同。

如果你同时使用 Claude Code 和 Cursor，运行一次 `openspec init --tools claude,cursor` 就能同时配置两个工具，Spec 内容完全一致。

## init 背后发生了什么

输入 `openspec init` 后，`InitCommand`（`OpenSpec/src/core/init.ts:105`）执行了以下步骤：

```
validate → handleLegacyCleanup → detectTools → migrateIfNeeded →
getSelectedTools → validateTools → createDirectoryStructure →
generateSkillsAndCommands → createConfig → displaySuccessMessage
```

逐步拆解：

**1. 验证与检测**

`validate()`（第 161 行）检查目标目录是否已有 `openspec/` 目录。如果有，进入 extend 模式（更新而非新建）；同时检查写入权限。

`handleLegacyCleanup()`（第 196 行）检测项目中是否有旧版 OpenSpec 的遗留文件（比如旧格式的命令文件），自动清理。

`getAvailableTools()` 检测项目目录中已有的 AI 工具配置——扫描 `.claude/`、`.cursor/` 等目录，判断你安装了哪些工具。

**2. 工具选择**

`getSelectedTools()`（第 255 行）的逻辑分支：

- 如果有 `--tools` 参数，直接使用参数指定的工具列表
- 如果是非交互模式（CI/CD），使用检测到的工具作为 fallback
- 如果是交互模式，显示可搜索的多选界面，已配置的工具排在前面

**3. 目录与配置创建**

`createDirectoryStructure()` 创建 `openspec/specs/` 和 `openspec/changes/` 目录。如果是 extend 模式，只创建缺失的目录。

`createConfig()` 生成 `openspec/config.yaml`，内容包含项目描述和默认 schema（`spec-driven`）。

**4. Skills 和 Commands 生成**

`generateSkillsAndCommands()`（`OpenSpec/src/core/init.ts:148`）是核心步骤。它读取全局配置中的 Profile 和 Delivery，通过 `getProfileWorkflows()` 确定要安装哪些工作流，然后为每个选中的工具生成对应的 Skill 和 Command 文件。

生成的 Skill 内容不是静态的。OpenSpec 内置了 Skill 模板（`SKILL_NAMES` 到模板的映射），每个 Skill 的内容会根据当前版本、Profile 配置动态生成。这就是为什么升级 CLI 后需要运行 `openspec update`——它重新生成这些文件以匹配最新版本。

整个流程的设计原则是：**用户只需要选工具，Profile/Delivery/工作流的组合全部自动处理**。

## 第一个 Change

现在让我们实际操作一下。假设你有一个 TypeScript + Express 项目，需要添加用户注册功能。

在 Claude Code 中，输入：

```
/opsx:propose "为现有 Express 项目添加用户注册功能，支持手机号验证码注册"
```

`propose` 命令会在 `openspec/changes/` 下创建一个新的 change 目录：

```
openspec/changes/add-user-registration/
├── proposal.md       # 提议文档
└── (后续步骤会添加更多文件)
```

`proposal.md` 的内容由 AI 根据你的描述生成，通常包含：

- 功能概述
- 影响范围
- 涉及的能力域（如 auth、user）

这只是第一步。proposal 创建后，后续的 explore、apply、sync、archive 命令会逐步把它细化成可执行的规格和任务。

## 小结

本文覆盖了 OpenSpec 的核心概念：

1. **OpenSpec 的定位**：在人类意图和代码生成之间插入规格层，让 AI 按规格写代码
2. **四条设计哲学**：流动而非僵化、迭代而非瀑布、简单而非复杂、棕地优先
3. **安装与初始化**：`npm install -g` + `openspec init`，支持交互和非交互模式
4. **目录结构**：`specs/`（真相源）、`changes/`（修改提议）、`config.yaml`（项目配置）
5. **Profile**：core（5 个命令）vs custom（最多 11 个），通过 `openspec config profile` 切换
6. **Delivery**：both/skills/commands 三种交付模式，决定安装 Skill 还是 Command
7. **OPSX 命令**：核心 5 个（propose、explore、apply、sync、archive）+ 扩展 6 个
8. **AI 工具集成**：30 种工具统一支持，一次 init 配置全部
9. **init 内部流程**：验证 → 检测 → 选择工具 → 创建目录 → 生成 Skills/Commands → 写入配置
