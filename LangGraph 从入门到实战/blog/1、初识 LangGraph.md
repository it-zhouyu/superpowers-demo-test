> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前面，我们用 LangChain 搭出了完整的链路：LCEL 组合、工具调用、对话记忆、流式输出、RAG。所有链路都有一个共同特征——直线执行。数据从 prompt 流向 llm，再流向 parser，一去不回。

但真实的 AI Agent 不是直线运行的。想想你让一个助手"帮我查一下北京的天气，如果下雨就推荐室内活动，否则推荐户外运动"。它需要：查天气（行动）、看结果（观察）、根据结果做判断（思考）、再采取行动。这是一个循环：思考 → 行动 → 观察 → 再思考。

LangChain 的 LCEL 链做不到循环和条件分支。LangGraph 就是来补这个缺的——它是一个基于图（Graph）的编排框架，专门处理带分支、带循环的复杂执行流程。

本文从零搭建第一个 LangGraph 图：定义状态、创建节点、连接边、编译执行。

## 安装依赖

```bash
pip install langgraph langchain-deepseek python-dotenv
```

| 包名 | 作用 |
|------|------|
| langgraph | 图编排框架，提供 StateGraph、节点、边等核心组件 |
| langchain-deepseek | DeepSeek 模型适配器，前面已经用过 |
| python-dotenv | 从 .env 文件加载环境变量 |

`.env` 文件和 LangChain 系列保持一致：

```
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## 第一个图：单节点聊天机器人

直接看代码，用注释说明每一步在做什么：

```python
from typing import Annotated
from typing_extensions import TypedDict

from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatDeepSeek(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

# 第一步：定义状态
# State 是一个 TypedDict，描述图在运行过程中维护的数据结构
# messages 字段用 Annotated[list, add_messages] 声明
# add_messages 是一个 reducer：新消息追加到列表，而不是覆盖
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 第二步：定义节点函数
# 每个节点函数接收当前 state，返回需要更新的字段
def chatbot(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# 第三步：构建图
# StateGraph(State) 创建一个图，状态类型由 State 决定
graph = StateGraph(State)
graph.add_node("chatbot", chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

# 第四步：编译并执行
app = graph.compile()
result = app.invoke({"messages": [("user", "你好，请用一句话介绍你自己")]})

print(f"消息数量: {len(result['messages'])}")
print(f"AI 回复: {result['messages'][1].content}")
```

四步搭完一个图：定义状态 → 定义节点 → 连接边 → 编译执行。下面逐个解释关键概念。

## State、Node、Edge 分别是什么

刚才的代码用了三个核心概念，用一张执行流程来理解：

```
START → chatbot → END
```

**State（状态）** 是图在运行过程中维护的数据。你把它理解成一个字典，所有节点共享同一份 State，每个节点读它、改它。刚才的 State 只有一个 `messages` 字段。

**Node（节点）** 是图中的处理单元。每个节点是一个 Python 函数，接收当前 State，返回需要更新的字段。刚才只有一个节点 `chatbot`，它调用 LLM 并把回复加到 messages 里。节点函数还可以接收第二个参数 `config`（运行时配置），后面讲到检查点时会用到，现在先知道有这回事就行。

**Edge（边）** 定义节点之间的执行顺序。`add_edge(START, "chatbot")` 表示从图的入口进入 chatbot 节点；`add_edge("chatbot", END)` 表示 chatbot 执行完后图结束。START 和 END 是 LangGraph 预定义的特殊标记，分别代表图的起点和终点。

**add_messages reducer** 是 `Annotated[list, add_messages]` 中声明的合并策略。没有 reducer 的字段，节点返回的新值会直接覆盖旧值。有了 reducer，新值会按 reducer 的逻辑合并到旧值上。`add_messages` 的合并逻辑是：新消息追加到已有消息列表末尾。这意味着每个节点往 messages 里追加消息时，之前的消息不会丢失。

## 执行图：invoke 和返回值

`app.invoke()` 接收一个字典，作为图的初始 State。这个字典的 key 必须和 State 的字段对应。返回值是最终 State 的完整快照：

```python
result = app.invoke({"messages": [("user", "你好")]})
# result 是整个 State：
# {
#     "messages": [
#         HumanMessage(content="你好"),
#         AIMessage(content="你好！有什么我能帮助你的吗？"),
#     ]
# }
```

`("user", "你好")` 是 LangChain 的简写格式，等价于 `HumanMessage(content="你好")`。

## 查看图结构

编译后的图可以用 `get_graph()` 查看内部结构：

```python
graph_data = app.get_graph()

print("节点列表:")
for node in graph_data.nodes:
    print(f"  {node}")

print("边列表:")
for edge in graph_data.edges:
    print(f"  {edge}")
```

输出：

```
节点列表:
  __start__
  chatbot
  __end__
边列表:
  __start__ -> chatbot
  chatbot -> __end__
```

`__start__` 和 `__end__` 就是 START 和 END 的内部表示。

还可以生成 Mermaid 格式的流程图描述：

```python
print(app.get_graph().draw_mermaid())
```

输出：

```mermaid
title: StateGraph
stateDiagram-v2
    [*] --> chatbot
    chatbot --> [*]
```

这段文本可以粘贴到支持 Mermaid 的工具（如 GitHub Markdown、Notion）中渲染成流程图。后面文章的图会越来越复杂，用 Mermaid 看图比看文字直观得多。

## 多轮对话：手动管理消息历史

LangGraph 的图本身不持久化状态。每次 `invoke` 是独立的，不会记住上一次的 messages。做多轮对话需要手动管理：

```python
# 第一轮
result1 = app.invoke({"messages": [("user", "我叫小明")]})
print(f"第 1 轮回复: {result1['messages'][1].content}")

# 第二轮：把第一轮的完整消息历史带上
messages = result1["messages"]
messages.append(("user", "我叫什么名字？"))
result2 = app.invoke({"messages": messages})
print(f"第 2 轮回复: {result2['messages'][-1].content}")
```

这里的关键是 `result1["messages"]`——因为 State 的 messages 字段用了 `add_messages` reducer，执行完第一轮后 messages 里已经包含了用户消息和 AI 回复。把整个列表传给第二次 invoke，模型就能看到之前的对话内容。

这种手动管理看起来麻烦，但好处是完全可控。后面学到 Checkpointer（检查点）时会看到自动持久化的做法。

## StateGraph 核心方法

本文用到了 StateGraph 的几个方法，后续文章会陆续用到更多。先把常用的列出来：## 小结

- **LangGraph** 是基于图的编排框架，解决 LangChain 链无法处理循环和条件分支的问题
- **State** 用 TypedDict 定义，所有节点共享；字段可以声明 reducer 控制合并行为
- **Node** 是普通 Python 函数，接收 State 返回需要更新的字段
- **Edge** 用 `add_edge` 连接节点，START 和 END 标记图的入口和出口
- **add_messages reducer** 让消息自动追加，不会覆盖之前的内容
- **compile()** 把图定义编译为可执行对象，之后用 `invoke()` 运行

## 完整代码

把下面代码保存为 `step1_stategraph_basics.py`，并和前面的 `config.py` 放在同一个目录下运行：

```python
from typing import Annotated
from typing_extensions import TypedDict

from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

class State(TypedDict):
    messages: Annotated[list, add_messages]

llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

def chatbot(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

graph = StateGraph(State)
graph.add_node("chatbot", chatbot)
graph.add_edge(START, "chatbot")
graph.add_edge("chatbot", END)

app = graph.compile()

def demo_simple_invoke():
    print("=" * 50)
    print("Demo 1: 单轮对话")
    print("=" * 50)

    result = app.invoke({"messages": [("user", "你好，请用一句话介绍你自己")]})

    print(f"消息数量: {len(result['messages'])}")
    print(f"用户消息: {result['messages'][0].content}")
    print(f"AI 回复: {result['messages'][1].content}")
    print()

def demo_multi_turn():
    print("=" * 50)
    print("Demo 2: 多轮对话")
    print("=" * 50)

    result1 = app.invoke({"messages": [("user", "我叫小明")]})
    print(f"第 1 轮 - AI 回复: {result1['messages'][1].content}")

    messages = result1["messages"]
    messages.append(("user", "我叫什么名字？"))
    result2 = app.invoke({"messages": messages})

    print(f"第 2 轮 - AI 回复: {result2['messages'][-1].content}")
    print()

def demo_graph_structure():
    print("=" * 50)
    print("Demo 3: 图结构")
    print("=" * 50)

    print("Mermaid 图描述:")
    print(app.get_graph().draw_mermaid())

    graph_data = app.get_graph()
    print("节点列表:")
    for node in graph_data.nodes:
        print(f"  - {node}")
    print("边列表:")
    for edge in graph_data.edges:
        print(f"  - {edge}")
    print()

if __name__ == "__main__":
    demo_simple_invoke()
    demo_multi_turn()
    demo_graph_structure()
```
