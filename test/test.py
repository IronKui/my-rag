# backend/test.py
from core.rag import load_file, splitter_documents, store_to_vectorstore, search_knowledge_base


def test_load_and_split(filepath):
    """测试文档加载和切分"""
    print(f"📄 测试文件：{filepath}")
    print("-" * 50)

    # 1. 测试加载
    print("⏳ 正在加载文档...")
    docs = load_file(filepath)
    print(f"✅ 加载成功！共 {len(docs)} 个 Document 对象")
    print(f"   第一个 Document 预览：{docs[0].page_content[:100]}...")
    print()

    # 2. 测试切分
    print("⏳ 正在切分文档...")
    chunks = splitter_documents(docs)
    print(f"✅ 切分成功！共 {len(chunks)} 个文本块")
    if chunks:
        print(f"   第一块预览：{chunks[0].page_content[:100]}...")
        print(f"   第一块元数据：{chunks[0].metadata}")
    print()

    return docs, chunks


def test_store(chunks):
    """测试向量化存储"""
    print("⏳ 正在存入向量库...")
    store_to_vectorstore(chunks)
    print("✅ 存入成功！")
    print()


def test_search(query, k=3):
    """测试检索"""
    print(f"⏳ 正在检索：{query}")
    results = search_knowledge_base(query, k=k)
    print(f"✅ 检索到 {len(results)} 个结果")
    for i, doc in enumerate(results):
        print(f"   结果 {i + 1}: {doc.page_content[:150]}...")
        print(f"   元数据: {doc.metadata}")
        print()
    return results


if __name__ == "__main__":
    filepath = "test.pdf"

    # 第1步：加载 + 切分
    docs, chunks = test_load_and_split(filepath)

    # 第2步：存入向量库
    test_store(chunks)

    # 第3步：检索测试
    test_search("什么是RAG", k=3)

    print("🎉 全部测试通过！")
