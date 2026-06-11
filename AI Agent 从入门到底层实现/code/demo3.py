# 运行方式：pip install openai pytz
# 将 your-api-key 替换为你的 DeepSeek API Key，保存为 agent_with_tools.py 后运行：python agent_with_tools.py

import json
from datetime import datetime
from openai import OpenAI

# ==================== 客户端初始化 ====================
# 使用 DeepSeek 的 API，兼容 OpenAI SDK
client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-5ab3bca60f72427298ecde72e0f4d0b4"
)

MODEL = "deepseek-v4-flash"

# ==================== 工具定义 ====================
# tools 是一个列表，每个元素描述一个工具
# LLM 通过 name 判断调哪个函数，通过 description 判断什么时候该调
# parameters 用 JSON Schema 格式定义参数结构
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息，包括温度、天气状况、空气质量等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 '北京'、'上海'、'深圳'"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取指定城市的当前时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 '北京'、'东京'、'纽约'"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "时区标识，如 'Asia/Shanghai'、'America/New_York'、'Asia/Tokyo'"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# ==================== 工具实现 ====================
# 实际项目中这些函数会调用真实的 API
# 这里用模拟数据演示

def get_weather(city: str) -> str:
    """模拟天气查询，实际项目中可接入和风天气、心知天气等 API"""
    weather_data = {
        "北京": "晴，气温 18-28°C，空气质量良好",
        "上海": "多云，气温 22-30°C，有轻微雾霾",
        "深圳": "阵雨，气温 25-32°C，注意带伞",
        "广州": "多云转晴，气温 24-33°C",
        "成都": "阴，气温 15-22°C，适合出行",
    }
    return weather_data.get(city, f"未找到{city}的天气数据")

def get_time(city: str, timezone: str = "Asia/Shanghai") -> str:
    """获取指定城市的当前时间"""
    import pytz
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return f"{city}当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"

# ==================== 工具映射 ====================
# tool_map 把工具名（字符串）映射到实际的 Python 函数
# LLM 返回的是函数名字符串，通过 tool_map 找到对应函数执行
tool_map = {
    "get_weather": get_weather,
    "get_time": get_time
}

# ==================== System Prompt ====================
# SYSTEM_PROMPT 告诉 LLM 它的角色和可用能力
SYSTEM_PROMPT = "你是一个智能助手，可以查询天气和时间。回答要简洁明了，使用中文。"

# ==================== Agent 执行循环 ====================
def run_agent(user_input: str, messages: list) -> str:
    """
    Agent 的核心执行循环：
    1. 把用户消息加入 messages
    2. 调用 LLM，判断 finish_reason
    3. 如果是 tool_calls，执行工具，把结果加入 messages，再次调用 LLM
    4. 如果是 stop，返回最终回复
    5. 循环直到 LLM 返回 stop
    """
    messages.append({"role": "user", "content": user_input})

    while True:
        # 调用 LLM，传入 messages 和 tools 定义
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools
        )

        choice = response.choices[0]

        # finish_reason == "stop"：LLM 直接给出文本回复，不需要调用工具
        if choice.finish_reason == "stop":
            messages.append({"role": "assistant", "content": choice.message.content})
            return choice.message.content

        # finish_reason == "tool_calls"：LLM 请求调用一个或多个工具
        if choice.finish_reason == "tool_calls":
            # 注意：这里必须用 model_dump() 把 message 对象转成字典
            # 如果直接 append choice.message，后续再次调用 API 时会报 AttributeError
            messages.append(choice.message.model_dump())

            # 逐个执行 LLM 请求的工具调用
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                print(f"  [调用工具: {func_name}({func_args})]")

                # 通过 tool_map 找到对应函数并执行
                result = tool_map[func_name](**func_args)

                print(f"  [工具结果: {result}]")

                # 把工具结果作为 tool 角色的消息加入 messages
                # tool_call_id 必须与 LLM 返回的 tool_call.id 对应
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        # 循环继续：带着工具结果再次调用 LLM
        # LLM 会基于工具结果决定是直接回复（stop）还是继续调用工具（tool_calls）

# ==================== 主循环 ====================
# 初始化 messages，放入 system prompt
messages = [{"role": "system", "content": SYSTEM_PROMPT}]

print("工具型 Agent 已启动，输入 exit 退出\n")

while True:
    user_input = input("你: ").strip()
    if not user_input or user_input.lower() in ("exit", "quit"):
        break

    reply = run_agent(user_input, messages)
    print(f"AI: {reply}\n")