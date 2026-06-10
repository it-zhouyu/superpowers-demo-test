> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="100" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

Manus、OpenClow、Claude Code、Codex，它们都是 **AI Agent**，它们不仅仅会调用大模型API，还额外提供了很多机制，具体什么是AI Agent，学完这些之后我再来总结。

## 如何用调用大模型API

### 准备环境

创建项目目录，安装依赖：

```bash
mkdir ai-agent-demo && cd ai-agent-demo
pip install openai
```

### 调用DeepSeek模型

创建 `agent.py`，调用模型生成一段文本：

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",  # 换成你的 API 地址
    api_key="your-api-key"              # 换成你的 API Key
)

messages = [{"role": "user", "content": "你好，用一句话介绍你自己"}]

response = client.chat.completions.create(
    model="deepseek-v4-flash",  # 换成你要用的模型
    messages=messages
)

print(response.choices[0].message.content)
```

运行它：

```bash
python agent.py
```

输出：

```
你好，我是DeepSeek，由深度求索公司创造的AI助手，是一个纯文本模型，支持阅读链接和上传文件（图像、txt、pdf、ppt、word、excel），拥有1M超长上下文，可以一次性处理三体三部曲体量的书籍，并且完全免费。
```

因为DeepSeek API兼容了OpenAI，所以可以使用OpenAI的方式来调用DeepSeek，大部分模型的API都兼容了OpenAI，调用代码都差不多，改一下 `base_url` 、指定`model`和`api_key`就可以了。

### 加上对话循环

单个问答没什么用，加上循环让对话能持续进行：

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="your-api-key"
)

messages = []

while True:
    user_input = input("你: ")
    if user_input.lower() in ("exit", "quit"):
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages
    )

    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"AI: {assistant_message}\n")
```

运行后可以连续对话：

```
你: 北京有什么好玩的地方
AI: 北京是一座兼具历史底蕴与现代活力的城市，好玩的地方非常丰富。我按风格和主题为你整理了一份推荐清单：

**一、皇城根下的历史回响（必去经典）**
1. 故宫博物院（紫禁城）— 世界最大木结构宫殿群，必须提前预约购票，周一闭馆
2. 天安门广场 & 升旗仪式 — 世界上最大的城市广场
3. 长城（八达岭、慕田峪、司马台等）— 八达岭最著名但人最多，慕田峪景色好人少
4. 天坛公园 — 明清皇帝祭天的场所，祈年殿是北京的标志性建筑之一
5. 颐和园 & 圆明园 — 昆明湖、万寿山、长廊是精华

**二、感受老北京烟火气**
什刹海、南锣鼓巷及周边胡同、大栅栏 & 北京坊

**三、文化与艺术**
国家博物馆、798艺术区、清华大学/北京大学

预约！几乎所有热门景点都需要提前1-7天预约。首选地铁出行。

你: 那附近有什么好吃的
AI: 我为您梳理了几个最热门区域的美食推荐：

**故宫/天安门/前门区域**
- 四季民福（前门/故宫店）：可以边吃烤鸭边看故宫角楼
- 全聚德（前门店）：百年老店
- 门框胡同百年卤煮、方砖厂69号炸酱面

**什刹海/南锣鼓巷/鼓楼**
- 姚记炒肝店（鼓楼店）：炒肝、包子，本地人常去
- 文宇奶酪店（南锣主街）：原味奶酪、双皮奶

**天坛/崇文门**
- 南门涮肉（天坛店）：经典北京铜锅涮肉
- 锦芳小吃：豆汁、艾窝窝、糖火烧
```

注意第二问"附近有什么好吃的"——模型理解了"附近"指的是北京，因为 `messages` 列表里保留了之前的对话，这就是最基础的"记忆"——把历史对话塞进每次请求里，模型就能理解上下文。

但这个实现非常粗糙，`messages` 列表会越来越长，最终超出模型的上下文窗口，对话存在内存里，程序关了就没了，模型只能生成文本，调用不了任何工具，这些问题后面逐个解决。

## 完整代码

把上面的对话循环整合成一份可以直接运行的完整代码：

```python
# 运行方式：pip install openai
# 将 your-api-key 替换为你的 DeepSeek API Key，保存为 agent.py 后运行：python agent.py

from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="your-api-key"
)

messages = []

print("=== AI Agent 对话程序 ===")
print("输入消息开始对话，输入 exit 或 quit 退出")
print("-" * 40)
print()

while True:
    user_input = input("你: ").strip()

    if not user_input or user_input.lower() in ("exit", "quit"):
        print("再见！")
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages
    )

    assistant_message = response.choices[0].message.content
    messages.append({"role": "assistant", "content": assistant_message})

    print(f"AI: {assistant_message}\n")
