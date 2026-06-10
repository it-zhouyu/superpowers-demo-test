"""
Step 3: Tool Calling — 工具调用

本文件演示：
- 用 @tool 装饰器定义工具函数
- llm.bind_tools() 把工具绑定到模型
- 手动执行工具调用循环（解析 tool_calls -> 执行 -> ToolMessage -> 循环）
- with_structured_output() 获取结构化输出
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from pydantic import BaseModel, Field
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ============================================================
# 定义工具函数
# ============================================================

@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气信息。"""
    # 这里用模拟数据演示，实际项目中会调用天气 API
    mock_data = {
        "北京": "晴天，气温 18°C，空气质量良好",
        "上海": "多云，气温 22°C，有轻微雾霾",
        "深圳": "阴天，气温 26°C，可能有小雨",
    }
    weather = mock_data.get(city, f"暂无{city}的天气数据")
    return json.dumps({"city": city, "weather": weather}, ensure_ascii=False)


@tool
def get_time(city: str, timezone_str: str = "Asia/Shanghai") -> str:
    """查询指定城市的当前时间。"""
    # 根据 timezone_str 计算对应时区的当前时间
    tz_map = {
        "Asia/Shanghai": timedelta(hours=8),
        "America/New_York": timedelta(hours=-4),
        "Europe/London": timedelta(hours=1),
        "Asia/Tokyo": timedelta(hours=9),
    }
    offset = tz_map.get(timezone_str, timedelta(hours=8))
    tz = timezone(offset)
    now = datetime.now(tz)
    return json.dumps({
        "city": city,
        "timezone": timezone_str,
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)


def run_with_tools(llm_with_tools, messages: list) -> str:
    """
    执行完整的工具调用循环：
    1. 把消息发给模型
    2. 如果模型返回 tool_calls，逐个执行工具
    3. 把工具结果作为 ToolMessage 追加到消息列表
    4. 重复，直到模型不再调用工具，返回最终文本回复
    """
    tools_map = {t.name: t for t in [get_weather, get_time]}

    while True:
        # 调用模型
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        # 检查是否有工具调用
        if not ai_message.tool_calls:
            return ai_message.content

        # 逐个执行工具
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            print(f"  [调用工具] {tool_name}({tool_args})")

            # 执行工具函数
            tool_fn = tools_map[tool_name]
            tool_result = tool_fn.invoke(tool_args)

            print(f"  [工具返回] {tool_result}")

            # 创建 ToolMessage，tool_call_id 必须和 AIMessage 中的 id 对应
            tool_message = ToolMessage(
                content=tool_result,
                tool_call_id=tool_call["id"],
            )
            messages.append(tool_message)


def main():
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0,
    )

    # ============================================================
    # Demo 1: bind_tools — 绑定工具后观察模型响应
    # ============================================================
    print("=" * 50)
    print("Demo 1: llm.bind_tools() 观察工具调用响应")
    print("=" * 50)

    # bind_tools 把工具的函数签名和描述发送给模型
    # 模型会根据用户问题决定是否调用工具
    llm_with_tools = llm.bind_tools([get_weather, get_time])

    messages = [HumanMessage(content="北京今天天气怎么样？")]
    ai_message = llm_with_tools.invoke(messages)

    print(f"\n[模型回复类型] {type(ai_message).__name__}")
    print(f"[回复内容] {ai_message.content}")
    print(f"[工具调用] {ai_message.tool_calls}")

    if ai_message.tool_calls:
        tc = ai_message.tool_calls[0]
        print(f"\n[tool_call 详情]")
        print(f"  name: {tc['name']}")
        print(f"  args: {tc['args']}")
        print(f"  id:   {tc['id']}")

    # ============================================================
    # Demo 2: 手动工具执行循环
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 2: 手动工具执行循环")
    print("=" * 50)

    messages = [HumanMessage(content="北京现在几点了？天气怎么样？")]
    print(f"\n[用户问题] 北京现在几点了？天气怎么样？")

    final_answer = run_with_tools(llm_with_tools, messages)
    print(f"\n[最终回复] {final_answer}")

    # ============================================================
    # Demo 3: with_structured_output — 结构化输出
    # ============================================================
    print("\n" + "=" * 50)
    print("Demo 3: with_structured_output() 结构化输出")
    print("=" * 50)

    # 定义期望的输出结构
    class BookRecommendation(BaseModel):
        title: str = Field(description="书名")
        author: str = Field(description="作者")
        genre: str = Field(description="类型/分类")
        reason: str = Field(description="推荐理由，一句话")

    # with_structured_output 内部使用 tool calling 机制
    # 模型会被约束为按照 Pydantic 模型的结构输出
    # DeepSeek V4 Flash 的思考模式不支持 tool_choice，需要使用 json_mode
    # 注意: DeepSeek 的 json_mode 要求 prompt 中包含 "json" 关键词
    structured_llm = llm.with_structured_output(BookRecommendation, method="json_mode")

    result = structured_llm.invoke(
        "请以 json 格式推荐一本适合程序员看的科幻小说，"
        "包含 title、author、genre、reason 四个字段"
    )
    print(f"\n[结构化结果] 类型: {type(result).__name__}")
    print(f"  书名: {result.title}")
    print(f"  作者: {result.author}")
    print(f"  类型: {result.genre}")
    print(f"  理由: {result.reason}")


if __name__ == "__main__":
    main()
