> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

前六篇我们学会了用 LangChain 调用 LLM、拼 Chain、加工具、管记忆、做流式输出，还学会了把 DeepSeek 的思考过程实时展示出来。但有个问题一直没碰：LLM 的知识来自训练数据，它不知道你公司的内部文档、你个人的笔记、你项目的代码。

RAG（Retrieval Augmented Generation，检索增强生成）就是解决这个问题的。思路很直接：在生成回答之前，先从你的文档库里找到相关内容，然后把这些内容作为上下文一起发给 LLM，让它基于这些内容来回答。

## RAG 的完整流程

一个 RAG 系统分两阶段：

**准备阶段（离线）：** 把文档处理成可检索的格式

1. 加载文档 — 读取 PDF、TXT、网页等原始文件
2. 文本分割 — 把长文档切成小块
3. 向量化 — 用 Embedding 模型把文本块转成向量
4. 存储 — 把向量存进向量数据库

**查询阶段（在线）：** 用户提问时实时检索

5. 检索 — 把用户问题转成向量，在向量数据库中找最相似的文档块
6. 生成 — 把检索到的文档块和用户问题一起发给 LLM，生成回答

这节我们用 LangChain 把这个流程跑通。

## 文档加载

RAG 的第一步是把原始内容加载进来。本教程用字符串模拟文档内容，方便直接运行。实际项目中可以用 LangChain 提供的文档加载器：

```python
SAMPLE_DOCUMENTS = [
    """LangChain 是一个用于开发由大型语言模型驱动的应用程序的框架。
它的核心价值在于将 LLM 与外部数据源、工具和记忆系统连接起来。
LangChain 提供了模块化的组件设计，包括 Model I/O、Retrieval、Chains、Agents 等核心模块。
通过这些模块，开发者可以快速搭建如文档问答、聊天机器人、数据提取等应用。""",

    """RAG（Retrieval-Augmented Generation，检索增强生成）是一种将检索系统与生成模型结合的技术。
它的核心思想是：在生成回答之前，先从知识库中检索相关文档，然后把检索到的内容作为上下文传给 LLM。
RAG 解决了 LLM 的两个核心问题：知识过期和幻觉问题。
典型流程包括：文档加载 -> 文本分割 -> 向量化 -> 存储 -> 检索 -> 生成回答。""",

    """向量数据库是 RAG 系统的核心基础设施。常见的包括 FAISS、Chroma、Pinecone、Milvus 等。
FAISS 是 Meta 开源的高效向量相似度搜索库，适合本地使用和小规模数据。
向量数据库的工作原理是将文本转换为高维向量，然后用最近邻算法找到最相似的文档。""",

    """文本分割是 RAG 预处理的关键步骤。RecursiveCharacterTextSplitter 是最常用的分割器。
分割时需要设置 chunk_size（每个块的最大长度）和 chunk_overlap（相邻块的重叠长度）。
重叠的作用是避免关键信息被截断在两个块的边界处。""",

    """LangChain 的 Chain 机制允许将多个组件串联成处理链。
使用 LCEL 可以用 | 操作符把组件连接起来。
对于 RAG 场景，chain 的输入通常包含 context 和 question 两个字段。
context 由 retriever 提供，question 由用户传入。""",
]
```

生产环境中常用的文档加载器：

| 加载器 | 用途 | 安装包 |
|--------|------|--------|
| `TextLoader` | 加载纯文本文件 | langchain-community |
| `PyPDFLoader` | 加载 PDF 文件 | pypdf |
| `WebBaseLoader` | 加载网页内容 | beautifulsoup4 |
| `CSVLoader` | 加载 CSV 文件 | langchain-community |
| `DirectoryLoader` | 批量加载目录下所有文件 | langchain-community |

## 文本分割：RecursiveCharacterTextSplitter

原始文档通常很长，直接塞给 LLM 不现实（超过上下文窗口），也不利于精准检索（查找粒度太粗）。需要把文档切成小块。

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,       # 每个块最多 100 个字符
    chunk_overlap=20,     # 相邻块重叠 20 个字符
    separators=["\n\n", "\n", "。", "，", " "],
)

doc = SAMPLE_DOCUMENTS[0]
print(f"原始文档长度: {len(doc)} 字符")

chunks = splitter.split_text(doc)
print(f"分割后块数: {len(chunks)}")
for i, chunk in enumerate(chunks):
    print(f"  块 {i + 1} ({len(chunk)} 字符): {chunk}")
```

输出：

```
原始文档长度: 190 字符
分割后块数: 3
  块 1 (87 字符): LangChain 是一个用于开发由大型语言模型（LLM）驱动的应用程序的框架。
它的核心价值在于将 LLM 与外部数据源、工具和记忆系统连接起来，构建更强大的 AI 应用。
  块 2 (65 字符): LangChain 提供了模块化的组件设计，包括 Model I/O、Retrieval、Chains、Agents 等核心模块。
  块 3 (36 字符): 通过这些模块，开发者可以快速搭建如文档问答、聊天机器人、数据提取等应用。
```

`RecursiveCharacterTextSplitter` 的工作方式：

1. 先尝试用第一个分隔符 `\n\n`（段落换行）分割
2. 如果某个片段仍然超过 chunk_size，就用下一个分隔符 `\n`（换行）再分割
3. 以此类推，直到最后按单个字符分割

这种递归策略的好处是尽量在自然断句处切分，不会把一句话从中间劈开。

分割参数的效果：

| 参数 | 作用 | 建议值 |
|------|------|--------|
| `chunk_size` | 每个块的最大字符数 | 500-1000（太小丢失上下文，太大检索不精准） |
| `chunk_overlap` | 相邻块重叠的字符数 | chunk_size 的 10%-20% |
| `separators` | 分隔符优先级列表 | 默认 `["\n\n", "\n", " ", ""]`，中文可加 `"。"` `"，"` |

用更大的 chunk_size 再试一次，对比效果：

```python
splitter_large = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=40,
    separators=["\n\n", "\n", "。", "，", " "],
)
chunks_large = splitter_large.split_text(doc)
print(f"chunk_size=200: {len(chunks_large)} 块")
```

输出：

```
chunk_size=200: 1 块
```

chunk_size=200 时整个文档只有 190 字符，一块就放下了。chunk_size 越大，块数越少，每块包含的信息越多，但检索精准度会降低。

## 向量存储：FAISS + FakeEmbeddings

文本分割完成后，下一步是把文本块转成向量并存进向量数据库。这里用 FAISS（Facebook AI Similarity Search）作为向量数据库。

为了让教程代码能直接运行（不需要额外的 Embedding API），这里用 LangChain 提供的 `FakeEmbeddings`——它生成随机向量，不调用任何 API，适合学习和测试：

```python
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings.fake import FakeEmbeddings

embeddings = FakeEmbeddings(size=128)

# 先把所有文档分割成小块
splitter = RecursiveCharacterTextSplitter(
    chunk_size=150,
    chunk_overlap=30,
    separators=["\n\n", "\n", "。", "，", " "],
)

all_chunks = []
for doc in SAMPLE_DOCUMENTS:
    chunks = splitter.split_text(doc)
    all_chunks.extend(chunks)

print(f"总共分割出 {len(all_chunks)} 个文本块")

# 创建向量存储
vectorstore = FAISS.from_texts(
    texts=all_chunks,
    embedding=embeddings,
)
print(f"向量存储创建完成，包含 {vectorstore.index.ntotal} 个向量")
```

输出：

```
总共分割出 11 个文本块
向量存储创建完成，包含 11 个向量
```

`FAISS.from_texts()` 做了两件事：对每个文本块生成 embedding 向量，然后构建索引。

测试相似度检索：

```python
results = vectorstore.similarity_search("什么是RAG", k=3)
print(f"查询: '什么是RAG'")
for i, doc in enumerate(results):
    print(f"  结果 {i + 1}: {doc.page_content[:60]}...")
```

注意：因为 FakeEmbeddings 生成的是随机向量，检索结果不反映真实的语义相似度。生产环境用真实的 Embedding 模型（如 OpenAIEmbeddings 或 DeepSeek Embedding），检索结果会准确得多。

向量数据库的常用方法：

| 方法 | 说明 |
|------|------|
| `FAISS.from_texts(texts, embedding)` | 从文本列表创建向量存储 |
| `FAISS.from_documents(docs, embedding)` | 从 Document 对象列表创建 |
| `similarity_search(query, k)` | 检索最相似的 k 个文档，返回 Document 列表 |
| `similarity_search_with_score(query, k)` | 同上，但额外返回相似度分数 |
| `as_retriever(search_kwargs)` | 转换为 Retriever 对象，可直接接入 LCEL Chain |
| `add_texts(texts)` | 向已有索引中添加新文本 |
| `save_local(path)` / `load_local(path)` | 持久化到磁盘 |

## RAG 检索链：把所有组件串起来

前面的步骤都是准备阶段，现在进入查询阶段——构建 RAG Chain。

### 第一步：创建检索器

```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
```

`as_retriever()` 把向量数据库包装成 Retriever 接口。`k=2` 表示每次检索返回最相似的 2 个文档块。

Retriever 和直接调用 `similarity_search()` 的区别在于：Retriever 是 Runnable，能直接用 `|` 接入 LCEL Chain，支持 invoke、stream 等标准方法。

### 第二步：定义格式化函数

```python
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)
```

检索器返回的是 Document 对象列表，需要把它们合并成一个字符串才能放进 prompt。

### 第三步：构建 RAG Chain

```python
from langchain_core.runnables import RunnablePassthrough

rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个知识问答助手。根据以下检索到的文档内容来回答用户的问题。
如果文档中没有相关信息，请诚实地说"根据已有资料无法回答"。

检索到的文档内容:
{context}"""),
    ("human", "{question}"),
])

llm = ChatDeepSeek(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

rag_chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough(),
    }
    | rag_prompt
    | llm
    | StrOutputParser()
)
```

这个 Chain 的数据流：

1. 用户输入一个字符串（问题）
2. `"context": retriever | format_docs` — 用问题去检索文档，然后格式化为字符串
3. `"question": RunnablePassthrough()` — 把用户输入原样透传为 question 字段
4. 两个字段组装成字典，传给 rag_prompt
5. prompt 输出传给 llm 生成回答
6. StrOutputParser 提取纯文本

`RunnablePassthrough()` 的作用就是"什么都不做，直接透传"。在这个位置，它把用户输入的问题原封不动地传给 prompt 的 `{question}` 占位符。

### 第四步：测试 RAG 问答

```python
questions = [
    "LangChain 是什么？",
    "RAG 的核心思想是什么？",
    "文本分割时为什么要设置 overlap？",
]

for question in questions:
    print(f"\n--- 问: {question} ---")
    # 先看检索到了哪些文档
    retrieved_docs = retriever.invoke(question)
    print(f"检索到 {len(retrieved_docs)} 个文档块:")
    for i, doc in enumerate(retrieved_docs):
        print(f"  文档 {i + 1}: {doc.page_content[:50]}...")

    # 获取 RAG 回答
    answer = rag_chain.invoke(question)
    print(f"答: {answer}")
```

每个问题的处理流程是：问题 -> 检索相关文档 -> 文档 + 问题一起发给我 LLM -> 生成回答。如果检索命中了正确的文档，LLM 就能基于文档内容准确回答；如果没命中，LLM 会说"根据已有资料无法回答"。

RAG Chain 同样支持流式输出：

```python
question = "FAISS 是什么？"
print(f"问: {question}")
print("答: ", end="", flush=True)
for chunk in rag_chain.stream(question):
    print(chunk, end="", flush=True)
print()
```

用 `stream()` 替换 `invoke()`，就能逐字输出 RAG 的回答，和之前学的流式输出完全一致。

## 总结：核心内容回顾

到这里，LangChain 入门教程已经覆盖了几个核心环节。回顾一下学过的内容：

- **模型调用**：接入 LLM，用 ChatDeepSeek 调用模型，理解消息类型（HumanMessage、AIMessage、SystemMessage）
- **Chain 编排**：用 LCEL 拼装 Chain（`prompt | llm | parser`），绑定工具让 LLM 调用外部函数
- **对话记忆**：用 RunnableWithMessageHistory 管理对话记忆，用 trim_messages 控制上下文长度
- **流式输出**：用 stream()、astream()、astream_events() 实现流式输出
- **思考模式**：开启 DeepSeek 思考模式，流式输出 reasoning_content 和最终回答
- **RAG 检索链**：用 RecursiveCharacterTextSplitter 分割文档，FAISS 存储向量，构建 RAG 检索链

七个知识点覆盖了 LLM 应用开发的核心环节：模型调用、Chain 编排、工具调用、记忆管理、流式输出、思考过程展示、知识检索。

到这里，我们已经会手写 Chain、手写工具调用循环，也会把私有文档接进 RAG。但手写工具循环仍然偏底层：每次都要自己解析 `tool_calls`、执行工具、追加 `ToolMessage`、再次调用模型。
