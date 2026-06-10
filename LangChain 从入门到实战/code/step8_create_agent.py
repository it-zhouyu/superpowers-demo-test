"""
Step 8: create_agent Tool Agent
演示 create_agent 自动工具调用，并验证 DeepSeek 思考模式下的版本兼容
"""

import importlib.metadata

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


THINKING_MODEL = DEEPSEEK_MODEL or "deepseek-v4-flash"


@tool(description="查询天气")
def get_weather(city: str) -> str:
    return f"{city}今天晴，气温 26 度。"


def create_thinking_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        model=THINKING_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )


def main():
    version = importlib.metadata.version("langchain-deepseek")
    print("=" * 50)
    print("create_agent + DeepSeek 思考模式 + 工具调用")
    print("=" * 50)
    print(f"模型: {THINKING_MODEL}")
    print(f"langchain-deepseek: {version}")
    print("建议版本: >= 1.1.0\n")

    llm = create_thinking_llm()
    agent = create_agent(
        model=llm,
        tools=[get_weather],
        system_prompt="你是一个有帮助的助手。需要天气信息时必须调用工具。",
    )

    result = agent.invoke({
        "messages": [
            {"role": "user", "content": "北京今天适合出门吗？请先查天气再回答。"},
        ]
    })

    for msg in result["messages"]:
        reasoning = msg.additional_kwargs.get("reasoning_content", "")
        print(f"[{type(msg).__name__}]")
        print(f"content: {msg.content}")
        if reasoning:
            print(f"reasoning_content 长度: {len(reasoning)}")
        if getattr(msg, "tool_calls", None):
            print(f"tool_calls: {msg.tool_calls}")
        print()


if __name__ == "__main__":
    main()
