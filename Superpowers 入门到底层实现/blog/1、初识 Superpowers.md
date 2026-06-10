> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 什么是 Superpowers

Superpowers 是一个 Claude Code 插件，但它不是普通的工具插件。它把**一整套软件开发的最佳实践**打包成了 14 个自动触发的 Skill，让 Claude Code 在你开发时自动遵循：先设计再编码、测试驱动开发、系统化调试、代码审查、分支管理。

一句话概括：**Superpowers 让 Claude Code 从"能写代码"变成"会做工程"**。

它的核心理念是：当 AI 要帮你开发一个功能时，它不应该直接动手写代码，而应该先问你"你到底想做什么"，确认需求后做设计，设计通过后再拆计划，然后按计划用 TDD 方式实现，每步都有审查，最后再合并。

这些步骤不是建议，是**强制执行**的。Superpowers 用了大量的 DOT 流程图和"反辩解表"来防止 AI 跳过流程——这背后是大量测试验证过的设计。

## 安装

在 Claude Code 中执行一条命令：

```
/plugin install superpowers@claude-plugins-official
```

也可以从 Superpowers 自己的 Marketplace 安装：

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

安装完成后，**重启 Claude Code**，Superpowers 就会自动激活。

怎么验证是否生效？在空目录中启动 Claude Code，输入：

```
我想开发一个手机号验证码登录注册 API
```

如果 Superpowers 正常工作，Claude Code **不会直接开始写代码**，而是先问你一系列问题来澄清需求——这就是 `brainstorming` Skill 自动触发了。如果没有安装 Superpowers，Claude Code 通常会直接开始写代码。

## 安装后发生了什么

我们来深入看看安装 Superpowers 后，Claude Code 的行为为什么发生了变化。答案在一个 **SessionStart Hook** 里。

### Hook 配置

Superpowers 的 `hooks/hooks.json` 定义了一个 SessionStart 钩子：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "async": false
          }
        ]
      }
    ]
  }
}
```

这个配置的意思是：在 Claude Code **启动、清空会话、压缩上下文**时，执行 `session-start` 脚本。`async: false` 表示必须等脚本执行完才能继续。

### session-start 脚本

脚本的核心逻辑很简单——把 `using-superpowers` Skill 的完整内容读取出来，注入到会话上下文中。简化版逻辑如下：

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 读取 using-superpowers Skill 内容
content=$(cat "${PLUGIN_ROOT}/skills/using-superpowers/SKILL.md")

# 转义为 JSON 字符串
escaped_content=$(escape_for_json "$content")

# 输出为 Hook 上下文注入格式
printf '{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "%s"
  }
}\n' "$escaped_content"
```

这就是为什么安装后 Claude Code 的行为立刻不同了——`using-superpowers` Skill 的内容被自动注入到了每一次对话的上下文中。

实际脚本比上面简化版多了一些处理：检查旧版自定义 Skill 目录并发出迁移警告；根据不同平台（Claude Code、Copilot CLI、Cursor）输出不同格式的 JSON。

### 多平台适配

不同平台对 Hook 输出的 JSON 格式要求不同。脚本做了适配：

| 平台 | 识别方式 | 输出格式 |
|------|---------|---------|
| Claude Code | `CLAUDE_PLUGIN_ROOT` 环境变量 | `hookSpecificOutput.additionalContext`（嵌套） |
| Cursor | `CURSOR_PLUGIN_ROOT` 环境变量 | `additional_context`（下划线） |
| Copilot CLI | `COPILOT_CLI=1` | `additionalContext`（顶层） |

这个适配逻辑解释了为什么 Superpowers 能同时支持 Claude Code、Codex CLI、Gemini CLI、Cursor、GitHub Copilot CLI 等多个平台——Hook 脚本根据环境变量判断当前平台，输出对应格式。

## using-superpowers 引导流程

`using-superpowers` 是 Superpowers 的"引导 Skill"，它的内容在每次会话启动时自动注入。它的作用是教会 Claude Code 如何使用其他 13 个 Skill。核心规则如下：

### 1% 规则

原版规则：

> If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.
>
> IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.
>
> This is not negotiable. This is not optional. You cannot rationalize your way out of this.

翻译：如果一个 Skill 有哪怕 1% 的可能性适用于当前任务，你就必须调用它。这不是建议，是强制要求——你没有选择，不能用自我辩解来逃避。

这条规则的存在是因为 AI 有一个很强的倾向：跳过流程直接干活。比如用户说"帮我加个按钮"，AI 想的是"直接写代码"，但 Superpowers 要求先检查是否有 `brainstorming` Skill 适用——显然适用，因为"加按钮"是在创建功能。

### 技能检查流程

Superpowers 用 DOT/GraphViz 流程图来定义这个检查流程。原版如下：

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

解读一下这个流程图：

- **上半部分**：当 AI 想进入 Plan Mode 时，先拦截检查"有没有做过 brainstorming"——没做过就先触发 brainstorming
- **下半部分**：每条用户消息进来后，检查是否有 Skill 可能适用（哪怕 1%）——有就调用，没有就直接回复
- 调用 Skill 后还要检查 Skill 里有没有 Checklist——有的话为每项创建 Todo

这就是为什么你在空目录输入"开发一个 API"时，Claude Code 不会直接规划，而是先问你要什么功能。

### Red Flags 表

为了防止 AI 找借口跳过 Skill，Superpowers 列了一张"Red Flags"表。原版如下：

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

简单来说：当 AI 脑子里出现这些想法时，意味着它在自我辩解，必须停下。

这张表的存在本身就说明了一个问题：**AI 天然倾向于跳过结构化流程**。Superpowers 通过大量测试发现了 AI 最常用的 12 种"借口"，逐一列出并给出反驳。

### Skill 优先级

当多个 Skill 可能同时适用时，原版规则：

> 1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
> 2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

即：流程类 Skill 先执行（brainstorming、systematic-debugging），它们决定"怎么做"；实现类 Skill 后执行，它们指导具体实现。比如"帮我开发一个 API"，brainstorming 先触发（流程类），确定设计后再调用实现类 Skill。

## Skill 的两种类型

Superpowers 把 Skill 分成两类，原版描述：

> **Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.
>
> **Flexible** (patterns): Adapt principles to context.

**Rigid（严格型）**：必须严格遵守，不能灵活变通。比如 TDD、systematic-debugging、verification-before-completion。**Flexible（灵活型）**：按原则指导，可以适应上下文。Skill 本身会告诉你它是哪种类型。

## 指令优先级

当用户的指令和 Superpowers 的规则冲突时，谁说了算？原版规则：

> 1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
> 2. **Superpowers skills** — override default system behavior where they conflict
> 3. **Default system prompt** — lowest priority

即：用户指令最高、Superpowers 居中、默认行为最低。比如 CLAUDE.md 里写了"不要用 TDD"，而 Superpowers 的 TDD Skill 说"必须 TDD"——听用户的。

## Superpowers 的 14 个 Skill 全景

最后，我们用一个表格总览 Superpowers 提供的全部 14 个 Skill，按开发流程排列：

| 阶段 | Skill 名称 | 触发时机 |
|------|-----------|---------|
| 引导 | using-superpowers | 每次会话启动时自动注入 |
| 设计 | brainstorming | 创建功能、修改行为前自动触发 |
| 规划 | writing-plans | 设计批准后，写实现计划 |
| 执行 | subagent-driven-development | 有计划后，派发子代理逐任务实现 |
| 执行 | executing-plans | 子代理不可用时的备选执行方式 |
| 执行 | dispatching-parallel-agents | 2+ 个独立问题需要并行处理 |
| 测试 | test-driven-development | 实现任何功能或修复前 |
| 调试 | systematic-debugging | 遇到 bug、测试失败时 |
| 验证 | verification-before-completion | 声称"完成"之前 |
| 审查 | requesting-code-review | 完成任务、合并前 |
| 审查 | receiving-code-review | 收到审查反馈时 |
| 分支 | using-git-worktrees | 开始功能开发，创建隔离工作区 |
| 分支 | finishing-a-development-branch | 实现完成，决定合并/PR/丢弃 |
| 自定义 | writing-skills | 创建或修改 Skill 时 |

接下来，我们将用一个 **Spring Boot + Java 的统一登录注册 API** 项目，逐一体验这些 Skill 在实际开发中的工作方式。
