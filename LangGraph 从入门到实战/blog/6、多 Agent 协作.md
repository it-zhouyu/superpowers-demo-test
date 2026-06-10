> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面我们给 Agent 加了人机交互——关键操作前暂停等人确认。但还有一个限制没突破：所有事情都由一个 Agent 做。让它查天气，行；让它算数学，行；让它同时搜索资料、整理分析、写技术报告，也行，但效果往往不理想。一个 Agent 的提示词里塞太多角色指令，它反而会顾此失彼。

更好的做法是让多个专家 Agent 各司其职：一个负责搜索，一个负责写作，一个负责统筹调度。这就是多 Agent（Multi-Agent）协作。

## Supervisor 模式

多 Agent 协作有很多编排方式，最常用的是 Supervisor（监督者）模式：

- **Supervisor Agent**：不干具体活，只做决策。它看一眼任务，决定该派给哪个专家
- **专家 Agent**：各有所长，接到任务后执行，完成后把结果交回给 Supervisor
- Supervisor 看到结果后，决定是继续派活还是结束

用图的拓扑来表示：

```
START -> supervisor -> researcher -> supervisor -> writer -> supervisor -> END
                      \-> writer    \-> END
                      \-> END
```

Supervisor 是中心节点，每次执行完一个专家任务后回到 Supervisor，由它决定下一步。

## 定义共享状态

多个 Agent 之间怎么传递信息？答案是共享状态。所有 Agent 读写同一个状态对象：

```python
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # 消息历史
    next_agent: str  # 下一个要调用的 agent
```

`messages` 用 `add_messages` reducer 累加——每个 Agent 的输出都是一条新消息，追加到列表里。`next_agent` 是 Supervisor 写入的字段，告诉路由函数下一步该走哪个节点。

## 定义专家 Agent

### Researcher：搜索信息的专家

```python
@tool
def search_web(query: str) -> str:
    """搜索互联网获取信息"""
    mock_results = {
        "Python GIL": (
            "Python GIL（Global Interpreter Lock，全局解释器锁）是 CPython 中的互斥锁，"
            "确保同一时刻只有一个线程执行 Python 字节码。\n"
            "- GIL 使得 CPU 密集型任务无法真正并行\n"
            "- I/O 密集型任务不受 GIL 影响\n"
            "- Python 3.13 引入了实验性的 free-threaded 模式"
        ),
    }
    for key, value in mock_results.items():
        if key.lower() in query.lower():
            return value
    return "未找到相关信息"
```

```python
def researcher_node(state: AgentState) -> dict:
    """研究智能体：根据任务搜索信息"""
    messages = state["messages"]

    system_msg = SystemMessage(content=(
        "你是一个研究助手。根据用户的任务，使用 search_web 工具搜索相关信息，"
        "然后整理成结构化的研究结果返回。"
    ))

    researcher_llm = llm.bind_tools([search_web])
    response = researcher_llm.invoke([system_msg] + messages)

    # 手动执行工具调用
    tool_calls = getattr(response, "tool_calls", None)
    research_results = []

    if tool_calls:
        for tc in tool_calls:
            if tc["name"] == "search_web":
                result = search_web.invoke(tc["args"])
                research_results.append(f"[搜索: {tc['args']['query']}]\n{result}")

    # 有结果就让 LLM 总结，没结果直接返回
    if research_results:
        combined = "\n\n".join(research_results)
        summary = llm.invoke([
            SystemMessage(content="将以下搜索结果整理成简洁的研究报告。"),
            HumanMessage(content=combined),
        ])
        content = summary.content
    else:
        content = response.content

    return {
        "messages": [HumanMessage(content=f"研究结果:\n{content}", name="researcher")],
        "next_agent": "supervisor",  # 完成后回到 supervisor
    }
```

Researcher 节点做了三件事：

1. 把当前消息列表和 system 指令一起发给绑定了搜索工具的 LLM
2. 如果 LLM 决定调用搜索工具，手动执行并汇总结果
3. 把研究结果作为新消息追加到状态中，同时把 `next_agent` 设为 `"supervisor"`

### Writer：写作的专家

```python
def writer_node(state: AgentState) -> dict:
    """写作智能体：根据研究结果撰写内容"""
    messages = state["messages"]

    system_msg = SystemMessage(content=(
        "你是一个技术写作助手。根据提供的研究结果，撰写一篇结构清晰的技术总结。"
        "要求使用中文撰写，包含标题和分段，语言简洁专业。"
    ))

    response = llm.invoke([system_msg] + messages)

    return {
        "messages": [HumanMessage(content=f"撰写内容:\n{response.content}", name="writer")],
        "next_agent": "supervisor",
    }
```

Writer 比 Researcher 简单，因为不需要调用工具。它接收状态中的所有消息（包括 Researcher 的研究结果），写出一篇技术总结。

两个专家节点的返回格式一样：`messages` + `next_agent`。这是共享状态的关键——所有节点操作同一个状态结构。

## Supervisor 节点：任务调度

Supervisor 不做具体工作，它只看当前的消息历史，决定下一步该派给谁：

```python
def supervisor_node(state: AgentState) -> dict:
    """监督智能体：决定下一步调用哪个 agent"""
    messages = state["messages"]

    system_msg = SystemMessage(content=(
        "你是一个任务调度器。根据对话历史，决定下一步应该调用哪个智能体。\n"
        "可选的智能体:\n"
        "- researcher: 需要搜索和收集信息时调用\n"
        "- writer: 已经有足够的研究结果，需要撰写内容时调用\n"
        "- FINISH: 任务已完成，不需要继续\n\n"
        "只返回以下三个值之一: researcher, writer, FINISH"
    ))

    response = llm.invoke([system_msg] + messages)
    decision = response.content.strip().upper()

    if "RESEARCHER" in decision:
        next_agent = "researcher"
    elif "WRITER" in decision:
        next_agent = "writer"
    elif "FINISH" in decision:
        next_agent = "FINISH"
    else:
        next_agent = "FINISH"  # 兜底

    return {"next_agent": next_agent}
```

Supervisor 的提示词很关键：它必须清楚知道有哪些专家可用，以及什么情况下该选谁。这里给了三条规则——没搜索过就派 researcher，有研究结果了就派 writer，内容写好了就 FINISH。

注意 Supervisor 只更新 `next_agent` 字段，不往 `messages` 里添加消息。它的角色是"决策者"而非"执行者"。

## 路由函数：根据决策选择节点

Supervisor 做出决策后，需要一个路由函数来决定图走哪条边：

```python
from langgraph.graph import END

def route_agent(state: AgentState) -> str:
    """根据 next_agent 字段路由到对应节点"""
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "researcher":
        return "researcher"
    elif next_agent == "writer":
        return "writer"
    else:
        return END
```

这个函数读 `next_agent` 字段，返回对应的节点名称。返回 `END` 表示图执行结束。跟之前 ReAct Agent 里的 `should_continue` 函数是同一个模式——读状态、做判断、返回节点名。

## 构建多 Agent 图

把所有节点和边组合起来：

```python
from langgraph.graph import StateGraph, START

def build_multi_agent_graph():
    graph = StateGraph(AgentState)

    # 添加三个节点
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)

    # 入口：先到 supervisor
    graph.add_edge(START, "supervisor")

    # supervisor 通过条件边路由到不同 agent
    graph.add_conditional_edges("supervisor", route_agent)

    # agent 执行完毕后回到 supervisor
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("writer", "supervisor")

    return graph.compile()
```

图的结构用文字描述就是：

```
START -> supervisor --(条件边)--> researcher -> supervisor (循环)
                            |---> writer     -> supervisor (循环)
                            |---> END
```

关键设计：

1. `START` 直接连 `supervisor`，任何任务先进调度器
2. `supervisor` 用条件边（`add_conditional_edges`），根据 `route_agent` 的返回值决定走哪条路
3. `researcher` 和 `writer` 执行完后都回到 `supervisor`，形成循环
4. 当 `route_agent` 返回 `END` 时，图执行结束

这个循环模式跟 ReAct Agent 的 agent -> tools -> agent 循环类似，只不过循环的粒度更大——这里是整个专家 Agent 作为循环单位。

## 执行示例：研究 GIL 并写总结

```python
app = build_multi_agent_graph()

task = "研究 Python GIL 机制，并写一篇技术总结"
result = app.invoke({
    "messages": [HumanMessage(content=task)],
    "next_agent": "",
})
```

执行过程：

```
[Supervisor] 决策: next_agent = researcher
  -> researcher 调用 search_web("Python GIL")
  -> 搜索结果: Python GIL 是 CPython 中的互斥锁...
  -> researcher 整理成研究报告

[Supervisor] 决策: next_agent = writer
  -> writer 看到研究报告，撰写技术总结

[Supervisor] 决策: next_agent = FINISH
  -> 图执行结束
```

查看最终的消息历史：

```python
for i, msg in enumerate(result["messages"]):
    name = getattr(msg, "name", "user") or "user"
    role = type(msg).__name__
    print(f"[{i}] {role} (name={name}):")
    for line in msg.content.split("\n"):
        print(f"    {line}")
```

输出（节选）：

```
[0] HumanMessage (name=user):
    研究 Python GIL 机制，并写一篇技术总结

[1] HumanMessage (name=researcher):
    研究结果:
    Python GIL（全局解释器锁）是 CPython 中的互斥锁...

[2] HumanMessage (name=writer):
    撰写内容:
    ## Python GIL 机制技术总结
    ### 什么是 GIL
    GIL 是 CPython 实现中的一把全局锁...
```

整个过程完全自动：Supervisor 先派 Researcher 搜索，看到研究结果后派 Writer 撰写，写完后 Supervisor 判断任务完成，结束执行。

## 多 Agent 编排模式对比

Supervisor 不是唯一的多 Agent 编排方式。LangGraph 支持多种模式：

| 模式 | 结构 | 适用场景 | 复杂度 |
|------|------|----------|--------|
| Supervisor | 中心调度，一个 Supervisor 控制多个专家 | 任务有明确的分解步骤，需要统筹 | 中等 |
| Swarm（群智） | Agent 之间直接交接控制权，无中心节点 | Agent 之间是对等协作关系 | 较高 |
| Hierarchical（层级） | 多层 Supervisor，每层管理一组 Agent | 大型项目，任务层级分明 | 高 |
| Map-Reduce | 同一任务分发给多个 Agent 并行执行，汇总结果 | 大量独立子任务需要并行处理 | 中等 |

Supervisor 模式适合大多数场景，也是这里重点讲解的。其他模式在 LangGraph 的官方文档中有详细说明，核心思想都是一样的——通过共享状态和条件边控制 Agent 之间的信息流转。

## 子图：每个专家可以是完整的图

前面的示例中，researcher 和 writer 各自是一个普通节点函数。但如果一个专家 Agent 本身就需要复杂的逻辑（比如多步推理、工具循环），可以把每个专家做成一个完整的 StateGraph——也就是子图（Subgraph）。

```python
# Researcher 可以是一个完整的 ReAct Agent
researcher_graph = create_react_agent(
    model=llm,
    tools=[search_web],
)

# Writer 可以是一个多步骤的写作处理链
writer_graph = StateGraph(WriterState)
writer_graph.add_node("outline", outline_node)
writer_graph.add_node("draft", draft_node)
writer_graph.add_node("polish", polish_node)
# ... 内部有多个节点和边
```

子图的好处是每个专家内部可以有自己的状态和逻辑，不影响外层的多 Agent 编排。主图只关心每个专家的输入和输出，不关心它内部怎么实现。

## 消息传递：Agent 之间怎么共享数据

多 Agent 系统中，所有 Agent 通过共享的 `messages` 列表传递信息。每个 Agent 执行时，能看到之前所有 Agent 的输出。

关键在 `add_messages` reducer。当 Researcher 返回：

```python
{"messages": [HumanMessage(content="研究结果: ...", name="researcher")]}
```

这条消息被 `add_messages` 追加到状态中的 `messages` 列表。Writer 执行时，`state["messages"]` 已经包含了用户的原始任务和 Researcher 的研究结果。

`name` 参数是消息的来源标识。在多 Agent 场景中，用它区分消息是哪个 Agent 产生的：

```python
HumanMessage(content="研究结果: ...", name="researcher")
HumanMessage(content="撰写内容: ...", name="writer")
```

`next_agent` 字段是 Supervisor 和路由函数之间的通信方式。Supervisor 写入，路由函数读取。这种"通过状态字段传递控制信息"的模式在 LangGraph 中很常见。

## 总结

- **Supervisor 模式**是最常用的多 Agent 编排方式：一个调度 Agent + 多个专家 Agent
- **共享状态**（AgentState）是 Agent 之间传递信息的桥梁，所有节点读写同一个状态对象
- **条件边**实现 Supervisor 到专家的路由，`next_agent` 字段控制流转方向
- **循环结构**让 Supervisor 能反复调度：researcher -> supervisor -> writer -> supervisor -> END
- 每个专家可以是简单的节点函数，也可以是完整的子图（StateGraph）
- `add_messages` reducer 自动累加消息，`name` 参数标识消息来源

## 完整代码

把下面代码保存为 `step6_multi_agent.py`，并和前面的 `config.py` 放在同一个目录下运行：

```python
"""
LangGraph 教程 - Step 6: Multi-Agent（多智能体）

演示 Supervisor 模式：
1. Supervisor 节点决定任务分配
2. Researcher 子图负责信息搜索
3. Writer 子图负责内容撰写
4. Supervisor 循环调度直到任务完成
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_deepseek import ChatDeepSeek
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

# ============================================================
# 定义共享状态
# ============================================================

class AgentState(TypedDict):
    """多智能体共享状态"""
    messages: Annotated[list[BaseMessage], add_messages]  # 消息历史
    next_agent: str  # 下一个要调用的 agent: "researcher" / "writer" / "FINISH"

# ============================================================
# 创建 LLM 实例
# ============================================================

llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    api_base=DEEPSEEK_BASE_URL,
)

# ============================================================
# 定义工具
# ============================================================

@tool
def search_web(query: str) -> str:
    """搜索互联网获取信息（模拟）"""
    # 模拟搜索结果
    mock_results = {
        "Python GIL": (
            "Python GIL（Global Interpreter Lock，全局解释器锁）是 CPython 中的互斥锁，"
            "确保同一时刻只有一个线程执行 Python 字节码。\n"
            "关键要点:\n"
            "- GIL 使得 CPU 密集型任务无法真正并行\n"
            "- I/O 密集型任务不受 GIL 影响\n"
            "- Python 3.13 引入了实验性的 free-threaded 模式，可禁用 GIL\n"
            "- 多进程（multiprocessing）是绕过 GIL 的常用方案\n"
            "- C 扩展可以在执行计算时释放 GIL"
        ),
        "default": "搜索结果: 未找到相关信息，请尝试其他关键词。",
    }
    for key, value in mock_results.items():
        if key.lower() in query.lower():
            return value
    return mock_results["default"]

# ============================================================
# Researcher Agent（研究智能体）
# ============================================================

def researcher_node(state: AgentState) -> dict:
    """研究智能体：根据任务搜索信息"""
    messages = state["messages"]

    # 构造研究指令
    system_msg = SystemMessage(content=(
        "你是一个研究助手。根据用户的任务，使用 search_web 工具搜索相关信息，"
        "然后整理成结构化的研究结果返回。"
        "只返回研究结果，不要添加多余的解释。"
    ))

    # 调用带工具的 LLM
    researcher_llm = llm.bind_tools([search_web])
    response = researcher_llm.invoke([system_msg] + messages)

    # 手动执行工具调用（简化版，避免嵌套子图的复杂性）
    tool_calls = getattr(response, "tool_calls", None)
    research_results = []

    if tool_calls:
        for tc in tool_calls:
            if tc["name"] == "search_web":
                result = search_web.invoke(tc["args"])
                research_results.append(f"[搜索查询: {tc['args']['query']}]\n{result}")

    # 如果有工具调用结果，再让 LLM 总结
    if research_results:
        combined = "\n\n".join(research_results)
        summary_response = llm.invoke([
            SystemMessage(content="将以下搜索结果整理成简洁的研究报告。"),
            HumanMessage(content=combined),
        ])
        return {
            "messages": [HumanMessage(content=f"研究结果:\n{summary_response.content}", name="researcher")],
            "next_agent": "supervisor",
        }

    # 没有工具调用，直接返回 LLM 响应
    return {
        "messages": [HumanMessage(content=f"研究结果:\n{response.content}", name="researcher")],
        "next_agent": "supervisor",
    }

# ============================================================
# Writer Agent（写作智能体）
# ============================================================

def writer_node(state: AgentState) -> dict:
    """写作智能体：根据研究结果撰写内容"""
    messages = state["messages"]

    system_msg = SystemMessage(content=(
        "你是一个技术写作助手。根据提供的研究结果，撰写一篇结构清晰、内容准确的技术总结。"
        "要求:\n"
        "- 使用中文撰写\n"
        "- 包含标题和分段\n"
        "- 语言简洁专业\n"
        "- 只返回撰写的内容，不要添加多余说明"
    ))

    response = llm.invoke([system_msg] + messages)

    return {
        "messages": [HumanMessage(content=f"撰写内容:\n{response.content}", name="writer")],
        "next_agent": "supervisor",
    }

# ============================================================
# Supervisor Node（监督智能体）
# ============================================================

def supervisor_node(state: AgentState) -> dict:
    """监督智能体：决定下一步调用哪个 agent"""
    messages = state["messages"]

    system_msg = SystemMessage(content=(
        "你是一个任务调度器。根据对话历史，决定下一步应该调用哪个智能体。\n"
        "可选的智能体:\n"
        "- researcher: 需要搜索和收集信息时调用\n"
        "- writer: 已经有足够的研究结果，需要撰写内容时调用\n"
        "- FINISH: 任务已完成，不需要继续\n\n"
        "判断规则:\n"
        "1. 如果还没有搜索过信息，分配给 researcher\n"
        "2. 如果已有研究结果但还没有撰写内容，分配给 writer\n"
        "3. 如果已经有撰写好的内容，返回 FINISH\n\n"
        "只返回以下三个值之一: researcher, writer, FINISH\n"
        "不要返回任何其他内容。"
    ))

    response = llm.invoke([system_msg] + messages)
    decision = response.content.strip().upper()

    # 标准化输出
    if "RESEARCHER" in decision:
        next_agent = "researcher"
    elif "WRITER" in decision:
        next_agent = "writer"
    elif "FINISH" in decision:
        next_agent = "FINISH"
    else:
        # 默认兜底
        next_agent = "FINISH"

    print(f"  [Supervisor] 决策: next_agent = {next_agent}")

    return {"next_agent": next_agent}

# ============================================================
# 路由函数：根据 supervisor 决策选择下一个节点
# ============================================================

def route_agent(state: AgentState) -> str:
    """根据 next_agent 字段路由到对应节点"""
    next_agent = state.get("next_agent", "FINISH")
    if next_agent == "researcher":
        return "researcher"
    elif next_agent == "writer":
        return "writer"
    else:
        return END

# ============================================================
# 构建多智能体图
# ============================================================

def build_multi_agent_graph():
    """构建 Supervisor 模式的多智能体图"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)

    # 设置入口
    graph.add_edge(START, "supervisor")

    # supervisor 根据决策路由到不同 agent
    graph.add_conditional_edges("supervisor", route_agent)

    # agent 执行完毕后回到 supervisor 继续调度
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("writer", "supervisor")

    return graph.compile()

# ============================================================
# Demo: 多智能体协作
# ============================================================

def demo_multi_agent():
    """演示 Supervisor 模式的多智能体协作"""
    print("=" * 50)
    print("Demo: Multi-Agent Supervisor 模式")
    print("=" * 50)

    app = build_multi_agent_graph()

    # 打印图结构
    print("\n--- 图结构 ---")
    print("START -> supervisor -> (researcher | writer | END)")
    print("researcher -> supervisor (循环)")
    print("writer -> supervisor (循环)")

    # 执行任务
    task = "研究 Python GIL 机制，并写一篇技术总结"
    print(f"\n--- 用户任务: {task} ---")

    result = app.invoke({
        "messages": [HumanMessage(content=task)],
        "next_agent": "",
    })

    # 展示执行过程
    print(f"\n--- 执行结果（共 {len(result['messages'])} 条消息）---")
    for i, msg in enumerate(result["messages"]):
        name = getattr(msg, "name", "user") or "user"
        role = type(msg).__name__
        content = msg.content
        print(f"\n  [{i}] {role} (name={name}):")
        # 缩进输出
        for line in content.split("\n"):
            print(f"      {line}")

    print(f"\n--- 最终决策: {result.get('next_agent', 'unknown')} ---")

# ============================================================
# Demo 2: 简单任务直接完成
# ============================================================

def demo_simple_task():
    """演示简单任务：不需要多个 agent"""
    print("\n" + "=" * 50)
    print("Demo 2: 简单任务（supervisor 直接完成）")
    print("=" * 50)

    app = build_multi_agent_graph()

    # 一个已经包含足够信息的任务
    task = "请根据以下信息直接写总结: Python 的 GIL 是全局解释器锁，影响多线程并行。"
    print(f"\n--- 用户任务: {task} ---")

    result = app.invoke({
        "messages": [HumanMessage(content=task)],
        "next_agent": "",
    })

    print(f"\n--- 执行结果 ---")
    for i, msg in enumerate(result["messages"]):
        name = getattr(msg, "name", "user") or "user"
        role = type(msg).__name__
        content = msg.content[:200] if len(msg.content) > 200 else msg.content
        print(f"  [{i}] {role} (name={name}): {content}")

# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("LangGraph Step 6: Multi-Agent（多智能体）")
    print("Supervisor 模式演示\n")

    # Demo 1: 完整的研究 + 写作任务
    demo_multi_agent()

    # Demo 2: 简单任务
    demo_simple_task()

    print("\n" + "=" * 50)
    print("所有 Demo 执行完毕")
    print("=" * 50)
```
