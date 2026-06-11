# 运行方式：pip install openai
# 将 your-api-key 替换为你的 DeepSeek API Key，保存为 reasoning_modes.py 后运行：python reasoning_modes.py

"""
推理模式演示
演示四种经典的 LLM 推理模式：CoT、ReAct、Plan-then-Execute、Reflection

运行方式：
    python reasoning_modes.py

运行后输入数字选择模式：
    1 - Chain of Thought（逐步推理）
    2 - ReAct（推理+行动交替）
    3 - Plan-then-Execute（先规划后执行）
    4 - Reflection（反思与自我纠正）
"""

import json
from openai import OpenAI

# ============================================================
# 基础配置
# ============================================================

client = OpenAI(
    api_key="sk-5ab3bca60f72427298ecde72e0f4d0b4",
    base_url="https://api.deepseek.com"
)

MODEL = "deepseek-chat"

# ============================================================
# 工具定义
# ============================================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息，返回温度、天气状况等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如'北京'、'上海'、'成都'"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_attractions",
            "description": "搜索指定城市的旅游景点，支持按类型筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如'北京'、'上海'、'成都'"
                    },
                    "type": {
                        "type": "string",
                        "description": "景点类型，如'户外'、'室内'、'文化'、'美食'"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# ============================================================
# 工具实现（模拟数据）
# ============================================================

def get_weather(city: str) -> str:
    """模拟天气查询，返回模拟数据"""
    weather_data = {
        "北京": "晴天，18~28°C，空气质量良好，紫外线中等，适合户外活动",
        "上海": "多云，22~30°C，午后可能有阵雨，建议携带雨具",
        "成都": "阴天，16~24°C，空气湿润，适合室内活动和品尝美食",
        "杭州": "小雨，20~26°C，西湖烟雨蒙蒙，适合游览但需带伞",
        "广州": "雷阵雨，25~33°C，天气闷热，建议安排室内景点"
    }
    return weather_data.get(city, f"暂无{city}的天气数据")

def search_attractions(city: str, type: str = None) -> str:
    """模拟景点搜索，返回模拟数据"""
    attractions_data = {
        "北京": {
            "户外": "长城（八达岭/慕田峪）、颐和园、天坛公园、北海公园、奥林匹克森林公园",
            "室内": "故宫博物院、国家博物馆、798艺术区、中国科技馆",
            "文化": "故宫、天坛、雍和宫、国子监、南锣鼓巷胡同游",
            "美食": "全聚德烤鸭、护国寺小吃街、簋街夜市、牛街清真美食"
        },
        "上海": {
            "户外": "外滩滨江步道、世纪公园、崇明岛湿地、滴水湖",
            "室内": "上海博物馆、上海科技馆、中华艺术宫、田子坊",
            "文化": "豫园、城隍庙、石库门建筑群、上海历史博物馆",
            "美食": "南翔小笼、生煎包、本帮菜、云南南路美食街"
        },
        "成都": {
            "户外": "青城山、都江堰、浣花溪公园、锦里古街",
            "室内": "成都博物馆、金沙遗址博物馆、四川科技馆、宽窄巷子",
            "文化": "武侯祠、杜甫草堂、金沙遗址、锦里古街",
            "美食": "火锅（蜀大侠/小龙坎）、串串香、担担面、龙抄手、兔头"
        }
    }
    city_data = attractions_data.get(city)
    if not city_data:
        return f"暂无{city}的景点数据"

    if type:
        result = city_data.get(type)
        if result:
            return result
        # 没有匹配的类型，返回所有类型
        all_types = "\n".join(f"  {k}: {v}" for k, v in city_data.items())
        return f"未找到'{type}'类型的景点，{city}可用的景点类型：\n{all_types}"

    # 没有指定类型，返回所有
    all_types = "\n".join(f"  {k}: {v}" for k, v in city_data.items())
    return f"{city}所有景点：\n{all_types}"

# 工具名称到函数的映射
tool_map = {
    "get_weather": get_weather,
    "search_attractions": search_attractions
}

# ============================================================
# 辅助函数
# ============================================================

def call_llm(messages: list, use_tools: bool = False) -> object:
    """
    调用 LLM 的辅助函数

    Args:
        messages: 对话消息列表
        use_tools: 是否启用工具调用

    Returns:
        ChatCompletionMessage 对象
    """
    kwargs = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3
    }
    if use_tools:
        kwargs["tools"] = tools
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message

def execute_tool_calls(msg) -> list:
    """
    执行工具调用，返回工具结果消息列表

    Args:
        msg: 包含 tool_calls 的 assistant 消息对象

    Returns:
        工具结果消息列表
    """
    results = []
    for tool_call in msg.tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        print(f"  [调用工具: {func_name}({func_args})]")
        result = tool_map[func_name](**func_args)
        print(f"  [返回结果: {result[:50]}...]")
        results.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result
        })
    return results

# ============================================================
# 模式一：Chain of Thought（逐步推理）
# ============================================================

def demo_cot():
    """
    演示 CoT 模式
    通过 prompt 引导模型逐步推理，不使用工具，纯靠模型的推理能力解决问题
    """
    print("=" * 60)
    print("模式一：Chain of Thought（逐步推理）")
    print("=" * 60)

    question = "小明有 15 个苹果，给了小红 3 个，又从小华那里得到了 7 个，" \
               "然后吃掉了 5 个，最后把剩下的平均分给 4 个朋友。" \
               "请问每个朋友分到几个苹果？还剩几个？"
    print(f"\n问题：{question}\n")

    messages = [
        {
            "role": "user",
            "content": f"请一步步思考，然后回答：\n\n{question}"
        }
    ]

    # CoT 只需要一次 LLM 调用，不使用工具
    msg = call_llm(messages, use_tools=False)
    print(f"回答：\n{msg.content}\n")

# ============================================================
# 模式二：ReAct（推理+行动交替）
# ============================================================

def demo_react():
    """
    演示 ReAct 模式
    推理和行动交替进行，通过 while 循环实现"推理→调用工具→观察→继续推理"的过程
    """
    print("=" * 60)
    print("模式二：ReAct（推理+行动交替）")
    print("=" * 60)

    user_input = "我想去北京旅游，天气怎么样？有什么户外景点推荐？"
    print(f"\n用户：{user_input}\n")

    messages = [
        {
            "role": "system",
            "content": "你是一个旅游助手。根据用户需求，主动调用工具查询天气和景点信息，然后给出综合建议。"
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    # ReAct 循环：推理→行动→观察→推理→...→最终回答
    while True:
        msg = call_llm(messages, use_tools=True)

        # 如果模型返回了最终文本回答（没有工具调用），循环结束
        if msg.content and not msg.tool_calls:
            print(f"AI：{msg.content}\n")
            break

        # 如果模型发起了工具调用，执行工具并将结果追加到消息历史
        if msg.tool_calls:
            # 必须用 model_dump() 将 ChatCompletionMessage 对象转为 dict
            # 因为 messages 列表中的 assistant 消息必须是 dict 格式才能传给 API
            messages.append(msg.model_dump())
            tool_results = execute_tool_calls(msg)
            messages.extend(tool_results)

# ============================================================
# 模式三：Plan-then-Execute（先规划后执行）
# ============================================================

def demo_plan_then_execute():
    """
    演示 Plan-then-Execute 模式
    分两个阶段：第一阶段让模型制定计划，第二阶段让模型根据计划调用工具执行
    """
    print("=" * 60)
    print("模式三：Plan-then-Execute（先规划后执行）")
    print("=" * 60)

    user_request = "帮我规划北京一日游，户外为主，避开高峰时段"
    print(f"\n用户需求：{user_request}\n")

    # ---- Phase 1: 规划阶段 ----
    print("[Phase 1: 规划阶段]")
    plan_messages = [
        {
            "role": "system",
            "content": "你是一个旅游规划师。用户会提出旅游需求，你需要制定一个详细的执行计划。\n"
                       "计划格式：每个步骤写明要做什么、需要什么信息。\n"
                       "只输出计划，不要执行。"
        },
        {
            "role": "user",
            "content": user_request
        }
    ]

    msg = call_llm(plan_messages, use_tools=False)
    plan = msg.content
    print(f"执行计划：\n{plan}\n")

    # ---- Phase 2: 执行阶段 ----
    print("[Phase 2: 执行阶段]")
    exec_messages = [
        {
            "role": "system",
            "content": "你是一个旅游助手，可以查询天气和景点。根据计划逐步执行，调用需要的工具。"
        },
        {
            "role": "user",
            "content": f"用户需求：{user_request}\n\n执行计划：\n{plan}\n\n请按计划逐步执行，调用需要的工具。"
        }
    ]

    # 执行阶段同样使用工具调用循环
    while True:
        msg = call_llm(exec_messages, use_tools=True)

        if msg.content and not msg.tool_calls:
            print(f"\nAI：{msg.content}\n")
            break

        if msg.tool_calls:
            # model_dump() 将消息对象转为 dict 再追加
            exec_messages.append(msg.model_dump())
            tool_results = execute_tool_calls(msg)
            exec_messages.extend(tool_results)

# ============================================================
# 模式四：Reflection（反思与自我纠正）
# ============================================================

def demo_reflection():
    """
    演示 Reflection 模式
    三轮对话：初次生成 → 审查问题 → 修正代码
    不使用工具，纯粹依靠模型的自我反思能力
    """
    print("=" * 60)
    print("模式四：Reflection（反思与自我纠正）")
    print("=" * 60)

    question = "写一个 Python 函数，判断一个字符串是否是回文字符串。" \
               "要求：忽略空格和标点符号，忽略大小写。例如 'A man, a plan, a canal: Panama' 应该返回 True。"
    print(f"\n问题：{question}\n")

    # ---- Round 1: 初次生成 ----
    print("[Round 1: 初次生成]")
    initial_msg = call_llm([
        {"role": "user", "content": question}
    ], use_tools=False)
    initial = initial_msg.content
    print(f"初次回答：\n{initial}\n")

    # ---- Round 2: 审查 ----
    print("[Round 2: 审查]")
    review_msg = call_llm([
        {
            "role": "system",
            "content": "你是代码审查专家。审查下面的代码，检查是否有 bug、边界情况遗漏、或可改进的地方。"
                       "如果代码完美就说'没有问题'，否则列出所有问题。"
        },
        {
            "role": "user",
            "content": f"问题：{question}\n\n代码：\n{initial}"
        }
    ], use_tools=False)
    review = review_msg.content
    print(f"审查意见：\n{review}\n")

    # ---- Round 3: 修正 ----
    print("[Round 3: 修正]")
    revised_msg = call_llm([
        {"role": "user", "content": question},
        {"role": "assistant", "content": initial},
        {
            "role": "user",
            "content": f"审查发现以下问题，请修正并输出完整代码：\n{review}"
        }
    ], use_tools=False)
    revised = revised_msg.content
    print(f"修正后代码：\n{revised}\n")

# ============================================================
# 主函数
# ============================================================

def main():
    """
    主函数，让用户选择要运行的推理模式
    """
    print("\n推理模式演示")
    print("请选择要运行的模式：")
    print("  1 - Chain of Thought（逐步推理）")
    print("  2 - ReAct（推理+行动交替）")
    print("  3 - Plan-then-Execute（先规划后执行）")
    print("  4 - Reflection（反思与自我纠正）")
    print()

    choice = input("请输入数字 (1-4): ").strip()

    demos = {
        "1": demo_cot,
        "2": demo_react,
        "3": demo_plan_then_execute,
        "4": demo_reflection
    }

    demo_func = demos.get(choice)
    if demo_func:
        print()
        demo_func()
    else:
        print("无效选择，请输入 1-4 之间的数字")

if __name__ == "__main__":
    main()