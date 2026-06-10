> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="100" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 模式一：Chain of Thought

**核心思路**：在 prompt 中要求 LLM"请一步步思考"，让推理过程显式展开。

直接看效果。一道水池注水题：

```python
messages = [
    {"role": "user", "content": """请一步步思考，然后回答：

一个水池有两个进水管和一个排水管。
A管单独注满需要 4 小时，B管单独注满需要 6 小时，排水管单独排空需要 12 小时。
如果三管同时打开，多少小时能注满水池？"""}
]

reply = call_llm(messages)
print(reply)
```

输出：

```
三管同时打开时，净注水速率为：
1/4 + 1/6 - 1/12 = 3/12 + 2/12 - 1/12 = 4/12 = 1/3（池/小时）。
注满水池所需时间为：1 ÷ 1/3 = 3（小时）。

答案：3小时。
```

关键在 prompt 里的"请一步步思考"六个字，没有这句话，LLM 可能直接跳到答案"3小时"，中间过程要么省略要么出错，加上之后，LLM 会逐步骤展示推理过程。

### 为什么有效

LLM 生成文本的方式是"预测下一个 Token"。如果直接生成答案，它只基于问题做一次预测；如果先生成推理步骤，每一步的输出都成为下一步的输入——相当于把一次复杂预测拆成了多次简单预测，准确率自然更高。

### 适用场景

数学计算、逻辑推理、多步骤分析——任何需要"中间过程"才能得出正确答案的任务。

### 局限

CoT 是"纯想不动手"——LLM 只在脑子里推理，不调用任何工具，如果推理过程中需要查数据（比如"北京今天的气温是多少"），CoT 无法处理。

## 模式二：ReAct（推理+行动交替）

**核心思路**：思考（Reasoning）和行动（Acting）交替进行，每一步先推理"我需要做什么"，然后调用工具获取信息，观察结果后继续推理。

ReAct 把 CoT 的"纯脑力推理"扩展成了"脑力+行动力"的循环：

```
推理 → 行动（调用工具） → 观察（获取结果） → 推理 → 行动 → ... → 最终答案
```

用旅游助手来演示：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_attractions",
            "description": "搜索城市的旅游景点",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "type": {"type": "string", "description": "景点类型，如'户外'、'室内'、'文化'"}
                },
                "required": ["city"]
            }
        }
    }
]

def react_loop(messages: list) -> str:
    while True:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=tools,
            temperature=0.3
        )

        choice = response.choices[0]
        msg = choice.message

        if choice.finish_reason == "stop":
            return msg.content

        if choice.finish_reason == "tool_calls":
            messages.append(msg)
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                result = tool_map[func_name](**func_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
```

运行：

```
你: 我想去北京旅游，天气怎么样？有什么户外景点推荐？

  [推理后行动: 调用 get_weather({'city': '北京'})]
  [观察结果: 晴，18-28°C]

  [推理后行动: 调用 search_attractions({'city': '北京', 'type': '户外'})]
  [观察结果: 长城、颐和园、天坛公园]

AI:
北京天气：晴天，18~28°C，非常适合户外活动。
推荐户外景点：
1. 长城 — 世界文化遗产，推荐八达岭或慕田峪段
2. 颐和园 — 皇家园林，昆明湖+万寿山
3. 天坛公园 — 明清祭天之地，古树参天
```

LLM 先推理出"需要查天气和景点"，然后**分两步**调用工具——先查天气，再查景点。每拿到一个结果，就基于新信息决定下一步，这就是 ReAct 的"推理→行动→观察"循环。

### 适用场景

信息检索、数据分析、多步骤任务——需要"边查边想"的场景。

## 模式三：Plan-then-Execute（先规划后执行）

**核心思路**：把任务拆成两个阶段。第一阶段让 LLM 制定计划，第二阶段按计划逐步执行。

ReAct 是"边想边做"，Plan-then-Execute 是"想清楚再做"。

ReAct 每一步都是临时决策——拿到天气后才知道下一步要查景点。
Plan-then-Execute 先花一轮对话把所有步骤规划好，再按计划执行，好处是计划可以提前审查和调整，坏处是计划可能不准确，执行时发现遗漏还要回头改。

代码分两个阶段：

```python
def plan_then_execute(user_request: str) -> str:
    # Phase 1: Planning
    plan_messages = [
        {"role": "system", "content": """你是一个旅游规划师。用户会提出旅游需求，你需要制定一个执行计划。
计划格式：每个步骤写明要做什么、需要什么信息。
只输出计划，不要执行。"""},
        {"role": "user", "content": user_request}
    ]
    plan = call_llm(plan_messages)

    # Phase 2: Execution
    exec_messages = [
        {"role": "system", "content": "你是一个旅游助手，可以查询天气和景点。根据计划逐步执行，调用需要的工具。"},
        {"role": "user", "content": f"用户需求：{user_request}\n\n执行计划：\n{plan}\n\n请按计划逐步执行，调用需要的工具。"}
    ]

    # Agent 执行循环（带工具调用）...
```

运行（用户请求"帮我规划北京一日游，户外为主，避开高峰时段"）：

```
[Phase 1: 规划阶段]
执行计划:
步骤 1：确认游客基本信息（出发地点、体力水平）
步骤 2：查询北京天气，判断是否适合户外活动
步骤 3：搜索北京的户外景点
步骤 4：设计时间线，避开早晚高峰
步骤 5：细化交通与排队策略
步骤 6：输出最终行程清单

[Phase 2: 执行阶段]
  [执行步骤: 调用 get_weather({'city': '北京'})]
  [获取数据: 晴，18-28°C]
  [执行步骤: 调用 search_attractions({'city': '北京', 'type': '户外'})]
  [获取数据: 长城、颐和园、天坛公园]
  [执行步骤: 调用 search_attractions({'city': '北京', 'type': '文化'})]
  [获取数据: 故宫、天坛、胡同游]

AI:
推荐路线：天坛公园 → 北海公园 → 什刹海/后海
时间线：09:30出发 → 10:00-12:00天坛 → 12:30-13:30午餐
        → 13:30-15:30北海 → 15:45-16:30什刹海 → 16:30返程
避峰技巧：南进北出（天坛）、16:30结束避开晚高峰
```

注意 Phase 2 的执行不是盲目的——它参考了 Phase 1 制定的计划，按步骤调用了天气和景点工具。模型还主动查了"文化"类景点（计划中没写但执行时判断需要补充）。

### 适用场景

复杂任务、多步骤流程——需要全局视野、步骤之间有依赖关系的场景。

### 与 ReAct 的对比

| 维度 | ReAct | Plan-then-Execute |
|------|-------|-------------------|
| 决策时机 | 每步临时决策 | 先规划再执行 |
| 适应性 | 强——每步根据最新信息调整 | 弱——按计划走，发现遗漏才能改 |
| 全局观 | 弱——看不到后续步骤 | 强——整体规划后再动手 |
| 成本 | 可能走弯路（多轮试错） | 规划 + 执行两次 LLM 调用 |

简单任务用 ReAct，复杂任务用 Plan-then-Execute，也可以组合：先用 Plan-then-Execute 制定大纲，每个步骤内部用 ReAct 执行。

## 模式四：Reflection（反思与自我纠正）

**核心思路**：生成结果后，让 LLM 自己审查一遍，发现问题就修正。做 → 检查 → 改。

用一个代码题来演示：

```python
def reflection_loop(question: str) -> str:
    # Round 1: 初次回答
    initial = call_llm([
        {"role": "user", "content": question}
    ])

    # Round 2: 自我审查
    review = call_llm([
        {"role": "system", "content": "你是代码审查专家。审查下面的代码，检查是否有bug、边界情况遗漏、或可改进的地方。如果完美就说'没有问题'。"},
        {"role": "user", "content": f"问题：{question}\n\n代码：\n{initial}"}
    ])

    # Round 3: 根据审查意见修正
    revised = call_llm([
        {"role": "user", "content": question},
        {"role": "assistant", "content": initial},
        {"role": "user", "content": f"审查发现以下问题，请修正：\n{review}"}
    ])

    return revised
```

用户问"写一个 Python 函数，找出列表中第二大的数。要求只遍历一次列表。"

**Round 1 — 初次回答**（节选）：

```python
def second_largest(nums):
    if len(nums) < 2:
        return None

    max1 = max2 = float('-inf')  # 初始化为负无穷

    for x in nums:
        if x > max1:
            max2 = max1
            max1 = x
        elif x > max2 and x < max1:
            max2 = x

    if max2 == float('-inf'):
        return None
    return max2
```

**Round 2 — 审查意见**（节选）：

```
代码逻辑基本正确，但存在一个边界情况的缺陷：

列表中含有 float('-inf') 时，第二大数的检测可能失败。
原因：max1 和 max2 均初始化为 float('-inf')，
当列表中确实包含 -inf 时，函数无法区分"哨兵值"和"真实数据"。

示例：second_largest([float('-inf'), 1])
期望返回 -inf，实际返回 None。

建议修复：使用 None 作为初始哨兵，避免与任何数值冲突。
```

**Round 3 — 修正后的代码**：

```python
def second_largest(nums):
    if len(nums) < 2:
        return None

    max1 = max2 = None  # 用 None 替代 float('-inf')

    for x in nums:
        if max1 is None or x > max1:
            max2 = max1
            max1 = x
        elif max2 is None or (x > max2 and x < max1):
            max2 = x

    return max2
```

审查发现了一个真实的边界 bug：当列表中包含 `float('-inf')` 时，初始哨兵值 `-inf` 会和真实数据冲突。修正版用 `None` 替代，彻底避免了这个问题。

### 为什么有效

LLM 生成文本时是"单向的"——从左到右、从前到后，没有回头检查的机会。
Reflection 给了 LLM 一个"回头看"的机会，第一次生成可能因为注意力分配不均而遗漏边界情况，第二次以审查者的视角重新审视，往往能发现之前忽略的问题。

### 适用场景

代码生成、文档写作、数据分析——质量要求高、出错代价大的任务。

### 成本

Reflection 至少要 3 次 LLM 调用（生成 + 审查 + 修正），成本是普通方式的三倍。而且审查可能说"没有问题"（Round 2 的输出就可能是"没有问题"），这时 Round 3 的修正调用就白花了。所以 Reflection 不适合所有请求，只在质量要求高的场景启用。

## 四种模式对比

| 模式 | 核心机制 | 工具调用 | LLM 调用次数 | 适用场景 |
|------|----------|----------|-------------|----------|
| CoT | prompt 加"请一步步思考" | 无 | 1 次 | 数学、逻辑推理 |
| ReAct | 推理→行动→观察循环 | 有 | N 次（按需） | 信息检索、多步任务 |
| Plan-then-Execute | 先规划后执行 | 有 | 2+ 次 | 复杂流程、多步骤任务 |
| Reflection | 生成→审查→修正 | 可选 | 3+ 次 | 代码、文档等高质量输出 |

四种模式不是互斥的——可以组合使用。比如 Plan-then-Execute 的执行阶段内部用 ReAct 模式，最后用 Reflection 审查结果。

实际项目中，大多数 Agent 用 ReAct 就够了。遇到特别复杂的任务时再考虑 Plan-then-Execute，遇到质量敏感的任务时加 Reflection。

## 完整代码

以下是一份可以直接运行的完整脚本，包含四种推理模式的演示：

```python
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
    api_key="your-api-key",
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
```
