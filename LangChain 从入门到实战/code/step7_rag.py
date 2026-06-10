"""
Step 7: RAG (Retrieval Augmented Generation)
演示文档分割、向量存储、检索器链的完整 RAG 流程
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_deepseek import ChatDeepSeek

from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


# ==================================================
# 示例文档数据
# ==================================================
SAMPLE_DOCUMENTS = [
    """LangChain 是一个用于开发由大型语言模型（LLM）驱动的应用程序的框架。
它的核心价值在于将 LLM 与外部数据源、工具和记忆系统连接起来，构建更强大的 AI 应用。
LangChain 提供了模块化的组件设计，包括 Model I/O、Retrieval、Chains、Agents 等核心模块。
通过这些模块，开发者可以快速搭建如文档问答、聊天机器人、数据提取等应用。""",

    """RAG（Retrieval-Augmented Generation，检索增强生成）是一种将检索系统与生成模型结合的技术。
它的核心思想是：在生成回答之前，先从知识库中检索相关文档，然后把检索到的内容作为上下文传给 LLM。
RAG 解决了 LLM 的两个核心问题：一是知识过期（训练数据有截止日期），二是幻觉问题（编造不存在的事实）。
典型的 RAG 流程包括：文档加载 -> 文本分割 -> 向量化 -> 存储 -> 检索 -> 生成回答。""",

    """向量数据库是 RAG 系统的核心基础设施。常见的向量数据库包括 FAISS、Chroma、Pinecone、Milvus 等。
FAISS 是 Meta 开源的高效向量相似度搜索库，适合本地使用和小规模数据。
向量数据库的工作原理是将文本转换为高维向量（通过 Embedding 模型），然后用最近邻算法找到最相似的文档。
选择向量数据库时需要考虑：数据规模、查询延迟、是否需要持久化、是否支持分布式等因素。""",

    """文本分割（Text Splitting）是 RAG 预处理的关键步骤。原始文档通常很长，不能直接作为检索单位。
RecursiveCharacterTextSplitter 是 LangChain 中最常用的分割器，它按字符数递归分割。
分割时需要设置两个参数：chunk_size（每个块的最大长度）和 chunk_overlap（相邻块的重叠长度）。
重叠的作用是避免关键信息被截断在两个块的边界处，确保检索时不会遗漏上下文。
一般建议 chunk_size 设为 500-1000 字符，chunk_overlap 设为 chunk_size 的 10%-20%。""",

    """LangChain 的 Chain 机制允许将多个组件串联成处理流水线。
使用 LCEL（LangChain Expression Language）可以用 | 操作符把组件连接起来。
例如: chain = prompt | llm | output_parser，这种写法简洁且支持流式输出。
对于 RAG 场景，chain 的输入通常包含两个字段：context（检索到的文档）和 question（用户问题）。
context 由 retriever 提供，question 由用户传入，通过 RunnablePassthrough 直接传递。""",
]


# ==================================================
# Demo 1: 文档分割
# ==================================================
def demo1_text_splitting():
    print("=" * 50)
    print("Demo 1: 文档分割 - RecursiveCharacterTextSplitter")
    print("=" * 50)

    # 创建分割器
    # chunk_size: 每个文本块的最大字符数
    # chunk_overlap: 相邻块之间的重叠字符数，避免信息在边界处被截断
    # separators: 分割优先级，先尝试 "\n\n"，再尝试 "\n"，最后按字符分割
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20,
        separators=["\n\n", "\n", "。", "，", " "],
    )

    # 用第一个文档做演示
    doc = SAMPLE_DOCUMENTS[0]
    print(f"原始文档长度: {len(doc)} 字符")
    print(f"原始文档: {doc[:80]}...\n")

    chunks = splitter.split_text(doc)
    print(f"分割后块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\n  块 {i + 1} ({len(chunk)} 字符): {chunk}")

    # 用更大的 chunk_size 重新分割
    print("\n" + "-" * 30)
    splitter_large = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=40,
        separators=["\n\n", "\n", "。", "，", " "],
    )
    chunks_large = splitter_large.split_text(doc)
    print(f"\nchunk_size=200, chunk_overlap=40 时: {len(chunks_large)} 块")
    for i, chunk in enumerate(chunks_large):
        print(f"  块 {i + 1} ({len(chunk)} 字符)")


# ==================================================
# Demo 2: 向量存储
# ==================================================
def demo2_vector_store():
    print("\n" + "=" * 50)
    print("Demo 2: 向量存储 - FAISS + FakeEmbeddings")
    print("=" * 50)

    # FakeEmbeddings 是 LangChain 提供的测试用 Embedding
    # 它生成随机向量，不需要调用任何 API，适合学习和测试
    # 生产环境应替换为真实的 Embedding 模型（如 OpenAIEmbeddings 等）
    embeddings = FakeEmbeddings(size=128)
    print(f"Embedding 维度: 128")
    print(f"FakeEmbeddings 说明: 生成随机向量，仅用于演示和测试")

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

    print(f"\n总共分割出 {len(all_chunks)} 个文本块")

    # 用 FAISS.from_texts 创建向量存储
    # 这个方法会：1. 对每个文本块生成 embedding 向量  2. 构建索引
    vectorstore = FAISS.from_texts(
        texts=all_chunks,
        embedding=embeddings,
    )
    print(f"向量存储创建完成，包含 {vectorstore.index.ntotal} 个向量")

    # 测试相似度检索
    # 注意: FakeEmbeddings 生成的是随机向量，所以检索结果不反映真实语义相似度
    # 这里只是演示 API 用法
    print("\n--- 相似度检索测试 ---")
    results = vectorstore.similarity_search("什么是RAG", k=3)
    print(f"查询: '什么是RAG'")
    print(f"返回 {len(results)} 个结果:")
    for i, doc in enumerate(results):
        content = doc.page_content[:60] + "..." if len(doc.page_content) > 60 else doc.page_content
        print(f"  结果 {i + 1}: {content}")

    # similarity_search_with_score 返回带分数的结果
    results_with_scores = vectorstore.similarity_search_with_score("向量数据库", k=2)
    print(f"\n查询: '向量数据库' (带分数)")
    for doc, score in results_with_scores:
        content = doc.page_content[:50] + "..."
        print(f"  分数={score:.4f}, 内容: {content}")

    return vectorstore


# ==================================================
# Demo 3: RAG 检索链
# ==================================================
def demo3_rag_chain(vectorstore):
    print("\n" + "=" * 50)
    print("Demo 3: RAG 检索链")
    print("=" * 50)

    # 步骤 1: 从向量存储创建检索器
    # as_retriever() 把 vectorstore 包装成 retriever 接口
    # search_kwargs={"k": 2} 表示每次检索返回最相似的 2 个文档块
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # 步骤 2: 定义文档格式化函数
    # 把检索到的 Document 列表合并成一个字符串，作为 LLM 的上下文
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # 步骤 3: 创建 RAG prompt
    # 包含两个变量: context（检索到的文档）和 question（用户问题）
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个知识问答助手。根据以下检索到的文档内容来回答用户的问题。
如果文档中没有相关信息，请诚实地说"根据已有资料无法回答"。

检索到的文档内容:
{context}"""),
        ("human", "{question}"),
    ])

    # 步骤 4: 构建 RAG chain
    # LCEL 语法:
    #   {"context": ..., "question": ...} -> rag_prompt -> llm -> StrOutputParser
    # RunnablePassthrough() 表示 "question" 字段直接透传用户输入
    # retriever | format_docs 表示先用检索器获取文档，再格式化为字符串
    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
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

    # 步骤 5: 测试 RAG 问答
    # 注意: 由于使用 FakeEmbeddings，检索结果是随机的
    # 所以回答质量取决于检索是否刚好命中了相关文档
    # 生产环境使用真实 Embedding 模型即可
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
            content = doc.page_content[:50] + "..."
            print(f"  文档 {i + 1}: {content}")

        # 获取 RAG 回答
        answer = rag_chain.invoke(question)
        print(f"答: {answer}")


# ==================================================
# Demo 4: RAG 流式输出（补充演示）
# ==================================================
def demo4_rag_chain_stream(vectorstore):
    print("\n" + "=" * 50)
    print("Demo 4: RAG Chain 流式输出")
    print("=" * 50)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个知识问答助手。根据以下检索到的文档内容来回答用户的问题。
如果文档中没有相关信息，请诚实地说"根据已有资料无法回答"。

检索到的文档内容:
{context}"""),
        ("human", "{question}"),
    ])

    llm = ChatDeepSeek(
        model=DEEPSEEK_MODEL,
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

    # RAG chain 同样支持 stream()
    # 因为使用了 FakeEmbeddings，检索结果随机，回答可能不准确
    question = "FAISS 是什么？"
    print(f"问: {question}")
    print("答: ", end="", flush=True)
    for chunk in rag_chain.stream(question):
        print(chunk, end="", flush=True)
    print("\n")


# ==================================================
# Main
# ==================================================
if __name__ == "__main__":
    # Demo 1: 纯本地操作，不需要 API
    demo1_text_splitting()

    # Demo 2: 纯本地操作（FakeEmbeddings 不调用 API）
    vectorstore = demo2_vector_store()

    # Demo 3: 需要 LLM API 生成回答
    demo3_rag_chain(vectorstore)

    # Demo 4: 需要 LLM API，演示流式 RAG
    demo4_rag_chain_stream(vectorstore)
