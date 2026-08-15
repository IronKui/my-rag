from pathlib import Path
from langchain_chroma import Chroma
from datetime import datetime

import hashlib
import uuid
from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader, Docx2txtLoader, JSONLoader, \
    PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.index_manager import get_file_by_hash, get_file_by_source, auto_rename, add_file_to_index
from core.logger import setup_logger

import threading



import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# ========== 全局变量（定义在这里） ==========
vectorstore = None
_vectorstore_lock = threading.Lock()
_embeddings = None   # Embedding 模型缓存


def get_vectorstore():
    """线程安全获取 vectorstore（双重检查锁）"""
    global vectorstore
    if vectorstore is not None:
        return vectorstore
    with _vectorstore_lock:
        if vectorstore is None:
            vectorstore = Chroma(
                collection_name="mvp_knowledge",
                embedding_function=get_embeddings(),
                persist_directory="./chroma_db"
            )
    return vectorstore

# 自动创建当前模块的 logger
logger = setup_logger(__name__)

# 加载 文档:
def load_file(filepath,user_id="default"):
    """
    加载文档，将文档处理为list字符串列表
    """
    logger.info(f"开始加载文件：{filepath}")
    path = Path(filepath)

    #获取后缀名
    suffixes = path.suffix.lower()

    #按后缀操作
    #单个：
    # if suffixes == '.txt':
    #     #加载txt：
    #     txt_loder= TextLoader(file_path = filepath ,encoding = 'utf-8')
    #     #转为list列表
    #     docs = txt_loder.load() #返回List列表(Document对象)
    #     return docs
    if suffixes == '.txt':
        loder = TextLoader(filepath, encoding='utf-8')
    elif suffixes == '.md':
        loder = TextLoader(filepath, encoding='utf-8')
    elif suffixes == '.docx':
        loder = Docx2txtLoader(filepath)
    elif suffixes == '.json':
        loder = JSONLoader(filepath, "." ,False)
    elif suffixes == '.pdf':
        loder = PyPDFLoader(filepath,extraction_mode= "plain")
    elif suffixes == '.png' or suffixes == '.jpg' or suffixes == '.jpeg':
        return load_image(filepath)
    docs = loder.load()
    #todo ：添加一次性读取多个文件的内容，读File Directory

    #打标签，做溯源和去重
    with open(filepath,"rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest() #文件内容哈希

    #去重
    final_name =remove_duplicates(file_hash,filepath,user_id)
    if final_name is None:
        return None #重复跳过

    doc_id = str(uuid.uuid4())  # 一次上传共用一个文档ID

    for doc in docs:
        doc.metadata["source"] = final_name  # 文件名
        doc.metadata["file_hash"] = file_hash  # 内容哈希
        doc.metadata["upload_time"] = datetime.now().isoformat()  # 上传时间
        doc.metadata["doc_id"] = doc_id  # 文档唯一ID
        doc.metadata["user_id"] = user_id


    logger.info(f"加载完毕")
    return docs

def load_image(filepath):
    """读取图片，返回 Document 列表"""
    # TODO: 用 pytesseract 或 多模态大模型
    raise NotImplementedError("图片OCR功能开发中")

def remove_duplicates(file_hash,filepath, user_id):
    '''去重，返回最终文件名；重复返回 None'''
    #获取文件内容哈希

    #硬重复，看账号索引库里有无同hash
    if get_file_by_hash(user_id,file_hash):
        logger.info(f"文件{filepath}内容已存在，跳过入库")
        return  None
    #同名文件进行重命名：
    path =Path(filepath)
    source = path.name
    if get_file_by_source(user_id,source):
        logger.info(f"存在同名文件，进行重命名")
        return auto_rename(source)
    return source

#递归字符文本切分器
def splitter_documents(docs):
    """
    文本切割器，使用递归字符文本切割器
    """
    logger.info(f"开始进行文本切分")
    #1.创建分割器对象
    text_split = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=10,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    #2.切割
    chunks = text_split.split_documents(docs)  # ← 注意是 split_documents
    logger.info(f"切分完毕")
    return chunks

#向量化
def get_embeddings():
    """获取 Embedding 模型（单例模式，只加载一次）"""
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    local_model_path = "./models/bge-small-zh-v1.5"

    # 检查本地模型是否存在
    if os.path.exists(local_model_path):
        # 检查关键文件是否存在
        model_file = os.path.join(local_model_path, "model.safetensors")
        if os.path.exists(model_file):
            logger.info(f"使用本地模型：{local_model_path}")
            return HuggingFaceEmbeddings(
                model_name=local_model_path,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        else:
            logger.warning(f"本地模型文件不完整（缺少 model.safetensors），将重新下载")
    else:
        logger.info("本地模型不存在，开始下载...")

    # 如果本地不存在或文件不完整，从镜像站下载
    # 设置镜像站环境变量
    logger.info("从 Hugging Face 镜像站下载模型...")
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    return _embeddings
def store_to_vectorstore(chunks,user_id="default"):
    """
    存入向量数据库
    """
    logger.info(f"进行向量化")
    global vectorstore
    #如果没有向量库就创建一个
    vs = get_vectorstore()
    vs.add_documents(chunks)
    #更新索引
    first = chunks[0]
    add_file_to_index(user_id, first.metadata["file_hash"], {
        "filename": first.metadata["source"],
        "doc_id": first.metadata["doc_id"],
        "file_hash": first.metadata["file_hash"],
        "upload_time": first.metadata["upload_time"],
        "status": "active"
    })

    logger.info(f"文件向量化存入完毕")
    return

def search_knowledge_base(query:str, k: int = 3,user_id ="default") -> list:
    """
    从向量库中检索与 query 最相关的 k 个文本块
    返回 List[Document]
    """
    vs = get_vectorstore()
    #先判断在这里有没有vectorstore
    count = vs.get(where={"user_id":user_id})["ids"]
    if not count:
        logger.info(f"用户{user_id}的知识库为空")
        return []
    #检索
    logger.info(f"检索问题：{query[:50]}...")
    results = vs.similarity_search(query, k=k,filter={"user_id":user_id})
    logger.info(f"检索到了{len(results)}个相关的文本块")

    return results

def process_and_store(filepath: str,user_id="default") -> int:
  """加载文件 → 切分 → 入库，返回文本块数量"""
  docs = load_file(filepath,user_id)
  if docs is None:
      return 0, "duplicate"  # 重复，跳过
  chunks = splitter_documents(docs)
  store_to_vectorstore(chunks,user_id)
  return len(chunks),"ok"

