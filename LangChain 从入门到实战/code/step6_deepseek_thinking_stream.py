"""
Step 6: DeepSeek Thinking Mode Streaming
演示如何在 LangChain 中开启 DeepSeek 思考模式，并流式输出思考过程
"""

import asyncio

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


THINKING_MODEL = DEEPSEEK_MODEL or "deepseek-v4-flash"


@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。"""
    return f"{city}今天晴，气温 26 度。"


def create_thinking_llm() -> ChatDeepSeek:
    """创建开启 DeepSeek 思考模式的 ChatDeepSeek 实例"""
    return ChatDeepSeek(
        model=THINKING_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )


# ==================================================
# Demo 1: 非流式读取 reasoning_content
# ==================================================
def demo1_invoke_thinking():
    print("=" * 50)
    print("Demo 1: 非流式读取思考内容")
    print("=" * 50)

    llm = create_thinking_llm()
    response = llm.invoke("9.11 和 9.8 哪个更大？请给出简短结论。")

    reasoning = response.additional_kwargs.get("reasoning_content", "")
    answer = response.content

    print("\n[思考过程]")
    print(reasoning)

    print("\n[最终回答]")
    print(answer)


# ==================================================
# Demo 2: 同步流式输出思考过程
# ==================================================
def stream_deepseek_thinking(llm: ChatDeepSeek, question: str) -> tuple[str, str]:
    """流式输出 DeepSeek 思考过程和最终回答"""
    reasoning_text = ""
    answer_text = ""
    is_answer_started = False

    print("思考过程:\n", end="", flush=True)

    for chunk in llm.stream(question):
        reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
        answer_chunk = chunk.content

        if reasoning_chunk:
            reasoning_text += reasoning_chunk
            print(reasoning_chunk, end="", flush=True)

        if answer_chunk:
            if not is_answer_started:
                is_answer_started = True
                print("\n\n最终回答:\n", end="", flush=True)

            answer_text += answer_chunk
            print(answer_chunk, end="", flush=True)

    print("\n")
    return reasoning_text, answer_text


def demo2_stream_thinking():
    print("=" * 50)
    print("Demo 2: 同步流式输出思考过程")
    print("=" * 50)

    llm = create_thinking_llm()
    stream_deepseek_thinking(
        llm,
        "请判断：9.11 和 9.8 哪个更大？用一句话给出最终结论。",
    )


# ==================================================
# Demo 3: Chain 中流式输出思考过程
# ==================================================
def demo3_chain_stream_thinking():
    print("=" * 50)
    print("Demo 3: Chain 中流式输出思考过程")
    print("=" * 50)

    llm = create_thinking_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个严谨的数学老师，用中文回答。"),
        ("human", "{question}"),
    ])

    # 不接 StrOutputParser，保留 AIMessageChunk 中的 additional_kwargs
    chain = prompt | llm

    reasoning_text = ""
    answer_text = ""
    is_answer_started = False

    print("思考过程:\n", end="", flush=True)

    for chunk in chain.stream({"question": "为什么 9.8 大于 9.11？"}):
        reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
        answer_chunk = chunk.content

        if reasoning_chunk:
            reasoning_text += reasoning_chunk
            print(reasoning_chunk, end="", flush=True)

        if answer_chunk:
            if not is_answer_started:
                is_answer_started = True
                print("\n\n最终回答:\n", end="", flush=True)

            answer_text += answer_chunk
            print(answer_chunk, end="", flush=True)

    print("\n")


# ==================================================
# Demo 4: 异步流式输出思考过程
# ==================================================
async def astream_deepseek_thinking(llm: ChatDeepSeek, question: str) -> tuple[str, str]:
    """异步流式输出 DeepSeek 思考过程和最终回答"""
    reasoning_text = ""
    answer_text = ""
    is_answer_started = False

    print("思考过程:\n", end="", flush=True)

    async for chunk in llm.astream(question):
        reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
        answer_chunk = chunk.content

        if reasoning_chunk:
            reasoning_text += reasoning_chunk
            print(reasoning_chunk, end="", flush=True)

        if answer_chunk:
            if not is_answer_started:
                is_answer_started = True
                print("\n\n最终回答:\n", end="", flush=True)

            answer_text += answer_chunk
            print(answer_chunk, end="", flush=True)

    print("\n")
    return reasoning_text, answer_text


async def demo4_async_stream_thinking():
    print("=" * 50)
    print("Demo 4: 异步流式输出思考过程")
    print("=" * 50)

    llm = create_thinking_llm()
    await astream_deepseek_thinking(
        llm,
        "请用三步推理解释：为什么 9.8 大于 9.11？",
    )


# ==================================================
# Demo 5: 思考模式 + 工具调用 + 流式输出
# ==================================================
def demo5_stream_thinking_with_tools():
    print("=" * 50)
    print("Demo 5: 思考模式 + 工具调用 + 流式输出")
    print("=" * 50)

    llm = create_thinking_llm()
    llm_with_tools = llm.bind_tools([get_weather])

    messages = [
        HumanMessage(content="北京今天适合出门吗？请先查询天气工具再回答。")
    ]

    full_chunk = None
    reasoning_text = ""
    answer_text = ""
    tool_chunk_count = 0

    print("第一轮：模型思考并生成工具调用\n")
    print("思考过程:\n", end="", flush=True)

    for chunk in llm_with_tools.stream(messages):
        full_chunk = chunk if full_chunk is None else full_chunk + chunk

        reasoning_chunk = chunk.additional_kwargs.get("reasoning_content")
        answer_chunk = chunk.content

        if reasoning_chunk:
            reasoning_text += reasoning_chunk
            print(reasoning_chunk, end="", flush=True)

        if answer_chunk:
            answer_text += answer_chunk

        if chunk.tool_call_chunks:
            tool_chunk_count += len(chunk.tool_call_chunks)

    print("\n")
    print(f"工具调用流式片段数: {tool_chunk_count}")
    print(f"模型第一轮文本: {answer_text}")
    print(f"完整工具调用: {full_chunk.tool_calls}")

    # 关键点：把累积后的 AIMessageChunk 原样放回 messages。
    # 它里面包含 tool_calls，也保留了 reasoning_content。
    messages.append(full_chunk)

    for tool_call in full_chunk.tool_calls:
        tool_result = get_weather.invoke(tool_call["args"])
        messages.append(
            ToolMessage(
                content=tool_result,
                tool_call_id=tool_call["id"],
            )
        )
        print(f"\n执行工具: {tool_call['name']}({tool_call['args']})")
        print(f"工具结果: {tool_result}")

    print("\n第二轮：模型读取工具结果并生成最终回答\n")
    print("最终回答:\n", end="", flush=True)
    for chunk in llm_with_tools.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    demo1_invoke_thinking()
    demo2_stream_thinking()
    demo3_chain_stream_thinking()
    asyncio.run(demo4_async_stream_thinking())
    demo5_stream_thinking_with_tools()
