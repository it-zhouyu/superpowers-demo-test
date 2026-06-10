"""
Step 5: Streaming Output
演示 stream()、astream()、astream_events() 以及工具调用流式输出
"""

import asyncio

from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ==================================================
# Demo 1: 基本流式输出 - llm.stream()
# ==================================================
def demo1_basic_stream():
    print("=" * 50)
    print("Demo 1: 基本流式输出 - llm.stream()")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    print("AI 回答: ", end="", flush=True)
    # stream() 返回一个迭代器，每次 yield 一个 chunk（一小段文本）
    for chunk in llm.stream("用100字介绍Python"):
        # chunk.content 是当前片段的文本内容
        print(chunk.content, end="", flush=True)
    print("\n")


# ==================================================
# Demo 2: Chain 流式输出 - chain.stream()
# ==================================================
def demo2_chain_stream():
    print("=" * 50)
    print("Demo 2: Chain 流式输出 - chain.stream()")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个 Python 专家，用中文回答，简洁明了。"),
        ("human", "{input}"),
    ])

    # chain: prompt -> llm -> StrOutputParser
    # StrOutputParser() 把 AIMessage 提取为纯字符串
    chain = prompt | llm | StrOutputParser()

    print("AI 回答: ", end="", flush=True)
    # chain.stream() 会把整个 chain 的每一步都流式处理
    # 最终输出的是 StrOutputParser 解析后的纯文本片段
    for chunk in chain.stream({"input": "用3句话解释什么是装饰器"}):
        print(chunk, end="", flush=True)
    print("\n")


# ==================================================
# Demo 3: 异步流式输出 - chain.astream()
# ==================================================
async def demo3_async_stream():
    print("=" * 50)
    print("Demo 3: 异步流式输出 - chain.astream()")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个编程助手，用中文简洁回答。"),
        ("human", "{input}"),
    ])

    chain = prompt | llm | StrOutputParser()

    print("AI 回答: ", end="", flush=True)
    # astream() 是 stream() 的异步版本，用法完全一样
    async for chunk in chain.astream({"input": "列举3个Python的Web框架"}):
        print(chunk, end="", flush=True)
    print("\n")


# ==================================================
# Demo 4: 流式事件 - chain.astream_events()
# ==================================================
async def demo4_stream_events():
    print("=" * 50)
    print("Demo 4: 流式事件 - chain.astream_events()")
    print("=" * 50)

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个编程助手，用中文简洁回答。"),
        ("human", "{input}"),
    ])

    chain = prompt | llm | StrOutputParser()

    # astream_events() 可以监听 chain 执行过程中的各种事件
    # version="v2" 使用新版事件格式（推荐）
    # 事件类型包括:
    #   on_chain_start / on_chain_end  - chain 开始/结束
    #   on_llm_start / on_llm_end      - LLM 调用开始/结束
    #   on_llm_stream                  - LLM 流式输出片段
    #   on_parser_start / on_parser_end - 解析器开始/结束
    #   on_parser_stream               - 解析器输出片段
    event_count = 0
    async for event in chain.astream_events(
        {"input": "Python 的 GIL 是什么？一句话回答"},
        version="v2",
    ):
        event_count += 1
        kind = event["event"]

        # 只打印关键事件类型，避免输出过多
        if kind in ("on_chain_start", "on_chain_end"):
            name = event.get("name", "")
            print(f"  事件 [{kind}] name={name}")
        elif kind == "on_llm_stream":
            # LLM 流式片段
            data = event["data"]
            chunk = data["chunk"]
            content = chunk.content
            if content:
                print(f"  事件 [on_llm_stream] content={repr(content)}")
        elif kind == "on_llm_end":
            print(f"  事件 [on_llm_end] LLM 调用完成")
        elif kind == "on_parser_stream":
            # 解析器输出片段
            data = event["data"]
            chunk = data["chunk"]
            if chunk:
                print(f"  事件 [on_parser_stream] chunk={repr(chunk)}")

    print(f"\n总共收到 {event_count} 个事件")


# ==================================================
# Demo 5: 工具调用流式输出
# ==================================================
async def demo5_tool_call_stream():
    print("\n" + "=" * 50)
    print("Demo 5: 工具调用流式输出")
    print("=" * 50)

    # 定义两个简单的工具函数
    @tool
    def add(a: int, b: int) -> int:
        """计算两个数的和"""
        return a + b

    @tool
    def multiply(a: int, b: int) -> int:
        """计算两个数的乘积"""
        return a * b

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
    )

    # bind_tools() 让 LLM 知道有哪些工具可用
    llm_with_tools = llm.bind_tools([add, multiply])

    # 流式输出工具调用
    # LLM 会在流式过程中逐步生成 tool_call 的参数
    print("问题: 3加5等于多少？再乘以4\n")

    accumulated_tool_calls = {}  # 累积工具调用结果

    async for chunk in llm_with_tools.astream("3加5等于多少？然后结果再乘以4"):
        # chunk 可能包含 content（文本）或 tool_call_chunks（工具调用片段）
        if chunk.content:
            print(f"  文本片段: {chunk.content}")

        # tool_call_chunks 是工具调用的流式片段
        if chunk.tool_call_chunks:
            for tc_chunk in chunk.tool_call_chunks:
                idx = tc_chunk.get("index", 0)
                if idx not in accumulated_tool_calls:
                    accumulated_tool_calls[idx] = {
                        "name": "",
                        "args": "",
                        "id": "",
                    }
                # 逐步拼接工具调用的 name、args、id
                if tc_chunk.get("name"):
                    accumulated_tool_calls[idx]["name"] += tc_chunk["name"]
                if tc_chunk.get("args"):
                    accumulated_tool_calls[idx]["args"] += tc_chunk["args"]
                if tc_chunk.get("id"):
                    accumulated_tool_calls[idx]["id"] += tc_chunk["id"]

    # 打印累积的工具调用结果
    print(f"\n累积的工具调用:")
    for idx, tc in accumulated_tool_calls.items():
        print(f"  工具 [{idx}]: name={tc['name']}, args={tc['args']}, id={tc['id']}")


# ==================================================
# Main
# ==================================================
def run_sync_demos():
    """运行同步 Demo"""
    demo1_basic_stream()
    demo2_chain_stream()


async def run_async_demos():
    """运行异步 Demo"""
    await demo3_async_stream()
    await demo4_stream_events()
    await demo5_tool_call_stream()


if __name__ == "__main__":
    # 先运行同步 Demo
    run_sync_demos()

    # 再运行异步 Demo
    asyncio.run(run_async_demos())
