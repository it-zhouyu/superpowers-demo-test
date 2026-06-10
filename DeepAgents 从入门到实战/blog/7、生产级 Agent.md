> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前六篇我们分别学了：创建 Agent 和内置能力、自定义工具和 MCP 集成、文件系统后端和权限控制、子 Agent 和任务委派、Memory 记忆机制、Skills 技能系统和渐进式披露。每一篇聚焦一个特性，用独立的 Demo 演示。

这一部分做两件事：把所有特性组装成一个完整的生产级 Agent，再讲清楚生产环境必须面对的五个问题——流式输出、持久化记忆、上下文管理、可观测性、部署方案。

## 完整的生产级 Agent

把前面学过的所有组件拼到一起，就是一个生产级 Agent 的骨架：

```python
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

# 自定义工具
@tool
def search_info(query: str) -> str:
    """搜索信息。在实际项目中替换为真实的搜索 API（如 Tavily、Serper 等）。"""
    # 模拟搜索结果
    mock_data = {
        "LangChain": (
            "LangChain 最新版本更新:\n"
            "1. deepagents 0.6: 新增代码解释器、Harness Profiles、Streaming v3\n"
            "2. ContextHub: 自动上下文压缩和管理\n"
            "3. Delta Channels: 流式输出的增量更新\n"
            "4. langchain-deepseek: 官方 DeepSeek 集成包\n"
            "发布时间: 2026 年"
        ),
    }
    for key, value in mock_data.items():
        if key.lower() in query.lower():
            return value
    return f"搜索 '{query}': 找到了若干相关结果。"

@tool
def calculate(expression: str) -> str:
    """执行数学计算。输入一个数学表达式，返回计算结果。"""
    try:
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "错误: 表达式包含不允许的字符"
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"

# LLM 配置
llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

# 文件系统后端：真实磁盘读写
backend = FilesystemBackend(root_dir=work_dir)

# 检查点：内存持久化，支持多轮对话
checkpointer = MemorySaver()

# 创建 Agent
agent = create_deep_agent(
    model=llm,
    system_prompt=(
        "你是一个专业的研究助手。\n"
        "你的职责:\n"
        "  1. 根据用户的研究需求，使用 search_info 搜索信息\n"
        "  2. 使用 calculate 工具处理数值计算\n"
        "  3. 将研究结果整理成文档，保存到文件中\n"
        "  4. 输出结构清晰、引用准确的报告\n"
        "请用中文回复。保持专业和简洁。"
    ),
    tools=[search_info, calculate],
    backend=backend,
    checkpointer=checkpointer,
)
```

调用时传入 `thread_id` 来区分不同会话：

```python
result = agent.invoke(
    {"messages": "搜索一下 LangChain 的最新版本更新，然后告诉我主要的新特性。"},
    config={"configurable": {"thread_id": "user-123-session-1"}},
)
```

这个 Agent 拥有完整的配置：

| 组件 | 配置 | 作用 |
|------|------|------|
| model | ChatDeepSeek | LLM 后端，deepseek-v4-flash 对应 DeepSeek V4 Flash |
| system_prompt | 字符串 | Agent 的角色定义和行为指令 |
| tools | 列表 | 自定义工具（search_info、calculate）+ 内置工具（读写文件、搜索等） |
| backend | FilesystemBackend | 文件读写作用于真实磁盘 |
| checkpointer | MemorySaver | 对话状态持久化，支持多轮对话 |
| name | 字符串 | Agent 名称，用于流式输出时区分不同 Agent |

查看工具调用统计和执行结果：

```python
# 统计工具调用
tool_calls = {}
for msg in result["messages"]:
    if type(msg).__name__ == "AIMessage" and hasattr(msg, "tool_calls"):
        for tc in msg.tool_calls:
            name = tc["name"]
            tool_calls[name] = tool_calls.get(name, 0) + 1

for name, count in tool_calls.items():
    print(f"  - {name}: {count} 次")

# 打印最终回复
last_msg = result["messages"][-1]
print(last_msg.content)
```

实际运行结果：

```
工具调用统计:
  - search_info: 9 次

Agent 回复:
根据搜索结果，以下是关于 LangChain 最新版本更新的整理报告：

## LangChain 最新版本更新概要

### 发布时间：2026年

### 1. deepagents 0.6 — Agent 框架重大升级
- 代码解释器：Agent 可实时运行代码
- Harness Profiles：可配置的测试/评估框架
- Streaming v3：第三代流式传输机制

### 2. ContextHub — 上下文管理
- 自动上下文压缩：智能压缩对话历史，减少 Token 消耗
- 上下文管理：自动管理长对话中的上下文窗口

### 3. Delta Channels — 流式输出优化
- 增量更新：只传输变化的部分，显著降低延迟和带宽消耗

### 4. langchain-deepseek — 官方集成包
- 官方 DeepSeek 集成，支持 DeepSeek V4 Flash 等模型
```

Agent 反复调用 `search_info` 是因为模拟数据只有一条，Agent 为了获取更多详细信息，尝试了不同的搜索关键词。在实际项目中，接入真实搜索 API 后，一次或两次调用就能拿到足够的信息。

这就是一个功能完整的研究助手 Agent。接下来的内容在这个基础上逐个解决生产环境的问题。

## 流式输出

前面的示例都用 `agent.invoke()` 同步等待完整结果。实际使用中，Agent 可能需要调用多个工具、执行多步推理，等待时间从几秒到几十秒不等。用户盯着空白屏幕等这么久，体验不好。

`agent.stream()` 返回一个迭代器，可以实时追踪 Agent 的执行过程：

```python
agent = create_deep_agent(
    model=llm,
    system_prompt="你是一个简洁的助手。请用中文简短回复。",
    tools=[search_info],
    backend=backend,
    name="stream-demo-agent",
)

for event in agent.stream({"messages": "简单搜索一下 LangChain 的信息"}):
    for node_name, node_output in event.items():
        if node_name == "agent":
            messages = node_output.get("messages", [])
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"  agent -> 调用工具: {tc['name']}")
                elif msg.content:
                    print(f"  agent -> 回复: {msg.content[:100]}")
        elif node_name == "tools":
            messages = node_output.get("messages", [])
            for msg in messages:
                print(f"  tools -> 结果: {msg.content[:100]}")
```

实际运行结果：

```
流式事件:
  [事件 4] tools -> 结果: LangChain 最新版本更新:
1. deepagents 0.6: 新增代码解释器、Harness Profiles、Streaming v3
2. ContextHub: 自动上下文压缩和管理

共收到 6 个流式事件
```

6 个流式事件的分布大致是：事件 1-3 包含 Agent 的思考过程和工具调用决策，事件 4 是工具返回结果，事件 5-6 是 Agent 的最终回复。通过 `name="stream-demo-agent"` 参数，可以在多 Agent 场景中用 `metadata["lc_agent_name"]` 区分不同 Agent 的事件。

每次迭代返回一个字典，key 是节点名称（`"agent"` 或 `"tools"`），value 是该节点的输出。通过区分节点名称，你可以知道 Agent 当前在做什么：

- `"agent"` 节点：Agent 在思考或回复。检查是否有 `tool_calls` 可以判断它是在调用工具还是直接回复
- `"tools"` 节点：工具执行完毕，返回结果

### stream_mode 控制事件类型

`stream()` 还支持 `stream_mode` 参数，控制返回的事件粒度：

- `"values"`（默认）：返回完整的当前状态，每次迭代拿到的是最新状态的快照
- `"updates"`：返回增量更新，每次只拿到变化的 delta
- `"messages"`：只返回消息增量，适合做逐字输出

### 多 Agent 场景下的流式追踪

在多 Agent 场景中（主 Agent + 子 Agent），每个流式事件都带有 `metadata`，其中包含 `lc_agent_name` 字段，标识这个事件来自哪个 Agent。通过给 Agent 设置 `name` 参数，就可以区分不同 Agent 的事件：

```python
agent = create_deep_agent(
    model=llm,
    ...,
    name="research-assistant",  # 通过 name 标识 Agent
)
```

## 持久化记忆

生产环境中的 Agent 需要处理两类记忆问题：**对话状态**（多轮对话中的上下文连续性）和**跨会话知识**（项目约定、用户偏好等持久信息）。

### 第一层：对话状态持久化（Checkpointer）

前面的示例用了 `MemorySaver`，它把对话状态保存在内存中，进程重启就丢失。生产环境需要持久化到数据库：

| Checkpointer | 存储位置 | 适用场景 |
|--------------|----------|----------|
| MemorySaver | 内存 | 开发调试、单次运行 |
| SqliteSaver | SQLite 文件 | 轻量持久化、单机部署 |
| PostgresSaver | PostgreSQL | 生产环境推荐 |

配置方式一样，只是传入不同的 checkpointer：

```python
from langgraph.checkpoint.memory import MemorySaver
# from langgraph.checkpoint.sqlite import SqliteSaver
# from langgraph.checkpoint.postgres import PostgresSaver

# 内存（开发）
checkpointer = MemorySaver()

# SQLite（轻量生产）
# checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# PostgreSQL（生产推荐）
# checkpointer = PostgresSaver.from_conn_string("postgresql://...")

agent = create_deep_agent(
    model=llm,
    ...,
    checkpointer=checkpointer,
)
```

通过 `thread_id` 区分不同用户或不同会话：

```python
# 用户 A 的第一次对话
result1 = agent.invoke(
    {"messages": "帮我搜索 LangChain 的最新版本"},
    config={"configurable": {"thread_id": "user-A-session-1"}},
)

# 用户 A 的第二次对话（同一个 thread_id，上下文连续）
result2 = agent.invoke(
    {"messages": "刚才搜索的结果中，哪个特性最值得关注？"},
    config={"configurable": {"thread_id": "user-A-session-1"}},
)
```

同一个 `thread_id` 的多次调用共享对话历史。换一个 `thread_id` 就是一个全新的对话。

### 第二层：跨会话记忆（AGENTS.md）

AGENTS.md 是项目级的持久记忆文件，类似 Claude Code 的 CLAUDE.md。Agent 每次启动时自动加载它的内容，在整个生命周期中都可以读写。

- 写入 AGENTS.md 的信息在下次启动时仍然存在
- 适合存储项目约定、技术选型、用户偏好等"需要始终记住"的信息
- 和 Skill 的区别：AGENTS.md 始终加载，Skill 按需加载

### 第三层：结构化数据存储（StoreBackend）

除了对话状态和文本记忆，有时还需要存取结构化的键值数据（用户配置、缓存结果等）。StoreBackend 提供这一层：

- InMemoryStore：内存存储，开发用
- 外部数据库：可接入 Redis、PostgreSQL 等

### 生产环境的推荐组合

| 组件 | 推荐方案 | 职责 |
|------|----------|------|
| Checkpointer | PostgresSaver | 对话状态持久化，支持断点续传 |
| Backend | FilesystemBackend | 文件读写操作 |
| Memory | AGENTS.md | 项目级知识，始终加载 |
| Skills | SKILL.md | 专业知识，按需加载 |
| Store | PostgreSQL / Redis | 结构化数据 |

## 上下文管理

Agent 每次调用 LLM 都要发送完整的对话历史。对话越长、工具输出越多，上下文就越大。LLM 的上下文窗口有上限（DeepSeek V4 Flash 是 128K tokens），一旦超过，要么截断丢失信息，要么报错。

Deep Agents 提供三种策略来管理上下文大小：

### 策略一：自动压缩

当对话历史超过阈值时，Deep Agents 自动压缩较早的消息。不是简单截断，而是用 LLM 生成摘要，保留关键信息的压缩版。

这个过程对调用者透明——你不需要手动触发或配置，Agent 在需要时自动执行。deepagents 0.6 版本的 ContextHub 统一管理上下文的生命周期。

### 策略二：工具输出卸载到磁盘

工具调用可能返回大量数据（比如搜索结果返回了几千字、文件内容有几百行）。把这些完整输出留在上下文中很浪费。

Deep Agents 可以把大型工具输出保存到文件，在上下文中只保留文件路径和简短摘要。后续需要时通过文件路径重新读取。

在 system_prompt 中指示 Agent 这么做：

```python
system_prompt = (
    "当你收集到大量数据时:\n"
    "1. 将原始数据保存到 /data/raw_results.txt\n"
    "2. 处理和分析数据\n"
    "3. 只返回分析摘要\n"
)
```

### 策略三：子 Agent 上下文隔离

这是控制上下文最有效的机制。每个子 Agent 有独立的上下文窗口，大量中间输出不会影响主 Agent。主 Agent 只接收子 Agent 的最终结果（一条 ToolMessage），上下文始终保持干净。

前面已经详细讲过子 Agent 的机制，这里从上下文管理的角度补充：任何会产生大量中间结果的场景（搜索、代码分析、数据处理），都应该委派给子 Agent，而不是主 Agent 自己做。

### 最佳实践

- 要求子 Agent 返回简洁摘要（300-500 字），不要返回原始数据
- 大文件内容写入磁盘，不在上下文中保留全文
- 复杂任务分解给子 Agent，保持主 Agent 上下文干净
- 使用 `response_format` 让子 Agent 返回结构化数据，方便主 Agent 解析
- 使用 checkpointer 支持长对话的断点续传——如果上下文真的管理不了，至少可以从检查点恢复

## 部署方案

从开发到生产，有不同的路径可选。先快速了解一下 LangGraph 生态中两个付费服务，然后重点讲 Docker 容器部署和开源监控方案。

### LangGraph Cloud 和 LangSmith 简介

LangChain 官方提供了两个商业服务：

**LangGraph Cloud** —— Agent 托管部署平台。把 Agent 部署到 LangChain 的云基础设施上，自动处理水平扩展、容错、API 网关等。按执行节点数和待机时间计费，适合不想管基础设施的团队。也可以选择 Self-Hosted Lite 模式（免费，最多 100 万个节点），在自己服务器上运行一个功能受限的版本。

**LangSmith** —— LLM 可观测性平台。追踪每次 Agent 调用的完整链路（哪个工具被调用了、花了多少 token、延迟多少），还支持自动评估输出质量。免费额度每月 5,000 条 trace，Plus 计划 $39/席位/月。也支持私有部署，但属于企业版功能，需要购买许可。

两个服务都不错，但对于个人开发者和中小团队来说，完全可以不花钱——用 Docker 自己部署 Agent，用 LangFuse（开源）做监控。接下来讲这两个方案。

### 本地开发

最简单的方式，直接运行 Python 脚本：

```bash
python agent.py
```

用 MemorySaver + StateBackend 就够了。适合快速迭代和调试，改完代码立刻运行验证。

### LangGraph 开发服务器

```bash
langgraph dev
```

这个命令启动一个本地服务器，提供：

- 热重载：修改代码后自动生效，不需要重启
- Web UI：浏览器中可视化查看 Agent 执行过程
- 自动 API 生成：自动生成 REST API 和 WebSocket 端点

适合在接近生产的环境中测试，验证流式输出、多轮对话等行为。

### Docker 容器部署

生产部署推荐用 Docker 容器。核心思路：用 FastAPI 把 Agent 包装成 HTTP 服务，再用 Docker 容器化部署。

**第一步：创建 FastAPI 服务**

创建 `server.py`，把 Agent 暴露为 REST API：

```python
# server.py
import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_deepseek import ChatDeepSeek
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

app = FastAPI(title="Deep Agent API")

# 初始化 Agent（启动时执行一次）
llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

work_dir = os.environ.get("AGENT_WORK_DIR", "/tmp/agent-work")
backend = FilesystemBackend(root_dir=work_dir)
checkpointer = MemorySaver()

agent = create_deep_agent(
    model=llm,
    system_prompt="你是一个专业的研究助手。请用中文回复。",
    backend=backend,
    checkpointer=checkpointer,
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """调用 Agent 并返回回复。"""
    result = agent.invoke(
        {"messages": req.message},
        config={"configurable": {"thread_id": req.thread_id}},
    )
    return ChatResponse(reply=result["messages"][-1].content)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

关键设计：

- Agent 在服务启动时初始化一次，不是每次请求都创建
- `thread_id` 从请求参数传入，区分不同用户的会话
- `/health` 端点用于 Docker 健康检查和负载均衡器探活
- API Key 从环境变量读取，不硬编码

**第二步：创建 Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动服务
CMD ["python", "server.py"]
```

**第三步：创建 requirements.txt**

```
fastapi>=0.115.0
uvicorn>=0.30.0
langchain-deepseek>=0.1.0
deepagents>=0.6.4
langgraph>=1.2.2
```

**第四步：构建和运行**

```bash
# 构建镜像
docker build -t deep-agent .

# 运行容器
docker run -d \
    --name deep-agent \
    -p 8000:8000 \
    -e DEEPSEEK_API_KEY=your-api-key \
    -e AGENT_WORK_DIR=/app/workspace \
    deep-agent
```

`-e` 传入环境变量，API Key 不写进镜像里。

**第五步：测试**

```bash
# 健康检查
curl http://localhost:8000/health

# 调用 Agent
curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "搜索 LangChain 的最新版本", "thread_id": "user-1"}'
```

生产环境通常还会加一层 Nginx 做反向代理和 HTTPS 终结，用 Docker Compose 或 Kubernetes 管理多容器编排。

### LangFuse 可观测性

生产环境的 Agent 必须有可观测性——你需要知道它每次调用了什么工具、花了多长时间、出了什么错。LangFuse 是 LangSmith 的开源替代品，功能对等（Tracing、Evaluation、Prompt 管理），MIT 协议，可以免费私有部署。

**部署 LangFuse**

Docker 一行启动：

```bash
docker run -d \
    --name langfuse \
    -p 3000:3000 \
    -e DATABASE_URL=postgresql://user:pass@db:5432/langfuse \
    -e NEXTAUTH_SECRET=your-secret \
    -e SALT=your-salt \
    langfuse/langfuse
```

启动后访问 `http://localhost:3000` 注册账号，在项目设置中获取 API Key。

**集成到 Agent 代码**

安装 LangFuse：

```bash
pip install langfuse
```

设置环境变量（和 LangSmith 的方式类似）：

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=http://localhost:3000
```

在 Agent 调用时传入 LangFuse 的回调处理器：

```python
from langfuse.langchain import CallbackHandler

# 初始化 LangFuse 回调处理器
langfuse_handler = CallbackHandler()

# 调用 Agent 时传入 callbacks 参数
result = agent.invoke(
    {"messages": "搜索 LangChain 的最新版本"},
    config={
        "configurable": {"thread_id": "user-1"},
        "callbacks": [langfuse_handler],  # 追踪数据自动上报到 LangFuse
    },
)
```

加了这一行，Agent 每次调用的完整链路——包括工具调用、子 Agent 执行、LLM 推理过程——都会自动上报到 LangFuse。不需要改 Agent 的业务逻辑，只在 `config` 中加一个 `callbacks` 参数。

如果想让编译后的图自动带上回调（不需要每次调用时手动传入），可以用 `with_config`：

```python
agent = create_deep_agent(
    model=llm,
    system_prompt="你是一个助手。",
    backend=backend,
).with_config({"callbacks": [langfuse_handler]})
```

**在 LangFuse 中查看追踪数据**

打开 LangFuse UI（`http://localhost:3000`），可以看到：

- **Traces**：每次 Agent 调用的完整链路，包括所有工具调用和子 Agent 执行
- **Latency**：每个步骤的耗时分布，定位慢在哪
- **Token Usage**：每次调用的 token 消耗，用于成本监控
- **Scores**：支持手动或自动给 Trace 打分，评估 Agent 输出质量

这些信息帮你回答：Agent 调了哪些工具？哪一步最慢？花了多少 token？输出质量怎么样？

### 生产环境关键考量

| 关注点 | 建议 |
|--------|------|
| 安全 | 在工具和沙箱层面限制 Agent 权限，不要期望模型自我约束 |
| 成本 | 监控 token 使用量，合理使用上下文管理和子 Agent |
| 可靠性 | 使用 Checkpointer 支持断点续传和重试 |
| 可观测 | 集成 LangFuse 追踪每次调用，监控延迟和 token 消耗 |
| 扩展性 | 无状态设计 + 持久化存储，Docker 容器支持水平扩展 |
| 模型选择 | 不同子 Agent 可以用不同模型（推理用强模型，写作用快模型） |

推荐的项目目录结构：

```
project/
  server.py             # FastAPI 服务入口
  agent.py              # Agent 定义和工具注册
  tools/                # 自定义工具
  skills/               # 技能文件
  Dockerfile            # Docker 构建文件
  requirements.txt      # 依赖
  .env                  # 环境变量（API keys 等）
```

## 系列总结

前面从零到一构建了一个生产级 Agent。回顾一下核心内容：

**创建 Agent 与内置能力**

`create_deep_agent()` 一行代码创建 Agent。内置了文件读写、代码搜索、任务规划等工具，开箱即用。

**自定义工具与 MCP 集成**

用 `@tool` 装饰器把 Python 函数变成 Agent 工具。MCP（Model Context Protocol）让 Agent 直接使用外部工具服务器的能力。

**文件系统后端与权限控制**

FilesystemBackend 让 Agent 在真实磁盘上读写文件。FilesystemPermission 精细控制 Agent 的文件操作权限——哪些目录可读、哪些可写、哪些禁止访问。

**子 Agent 与任务委派**

通过 `subagents` 参数给 Agent 配备专家团队。主 Agent 负责协调，子 Agent 负责执行。核心价值是上下文隔离——子 Agent 的大量中间输出不会撑爆主 Agent 的上下文窗口。

**Memory 记忆机制**

AGENTS.md 存储始终加载的项目上下文。Agent 可以自主更新记忆。跨会话记忆用 CompositeBackend + StoreBackend 实现持久化。

**Skills 技能系统**

SKILL.md 定义可复用的专业知识。渐进式披露机制让 Agent 只在匹配到相关任务时才加载完整指令，节省上下文空间。

**生产级 Agent**

组装所有特性，加上流式输出、持久化记忆、上下文管理、Docker 容器部署、LangFuse 可观测性，把 Agent 从 Demo 变成可上线的系统。

### 三条学习路径

如果你是按顺序学的这三个系列，你的学习路径是：

1. **LangChain**：掌握 LLM 应用的基础组件——模型调用、提示词模板、对话记忆、RAG、工具调用
2. **LangGraph**：掌握 Agent 的编排能力——状态图、条件路由、循环、人机交互、检查点、多 Agent 协作
3. **DeepAgents**：掌握完整 Agent 的构建——文件系统、子 Agent、记忆机制、技能系统、生产部署

LangChain 提供原子组件，LangGraph 提供编排框架，DeepAgents 提供开箱即用的 Agent 方案。三层递进，每层建立在前一层的基础上。

完整代码见 `deepagents-demo/step7_production.py`，包含六个 Demo：生产级 Agent 配置、流式输出、持久化记忆概念、上下文管理策略、完整的研究助手 Agent、Docker 部署与 LangFuse 监控概述。
