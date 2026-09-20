# AI 知识库问答 Agent

基于 LangChain + LangGraph 的企业级 RAG 知识库问答系统。支持文档上传、智能问答、主动出题、角色扮演，内置多用户隔离、会话管理和文件生命周期管理。

## ✨ 功能特性

### RAG 核心
- **文档解析**：支持 PDF / DOCX / Markdown / TXT 格式
- **向量检索**：BGE 中文 Embedding + Chroma 持久化向量库
- **溯源**：检索结果携带来源文件名，回答有据可查
- **去重**：文件哈希去重 + 同名自动重命名
- **缓存**：Redis 热点检索结果缓存，减少重复计算

### Agent 能力
- **三个工具**：检索（retrieve）/ 出题（quiz）/ 评判（evaluate）
- **多模式**：学习模式 / 面试模式 / 角色扮演
- **自主决策**：基于 LangGraph 的多轮决策调用

### 会话与记忆
- **短期记忆**：SqliteSaver 持久化，服务重启对话不丢
- **上下文压缩**：对话超长时自动摘要，控制 Token 消耗
- **会话管理**：多会话独立、历史加载、重命名、删除
- **双存储**：完整历史（messages 表，用户可见）+ 压缩上下文（checkpointer，模型使用）

### 账号与安全
- **账号系统**：注册 / 登录 / JWT 鉴权
- **用户隔离**：知识库按用户隔离，数据互不可见
- **文件可见范围**：账号级（所有会话共享）/ 会话级（仅当前会话）
- **上传安全**：扩展名白名单 + 大小限制 + 路径穿越防护
- **运行时注入**：用户/会话上下文通过 `context_schema` 注入，Agent 实例复用不膨胀

## 🛠 技术栈

| 模块 | 技术 |
|:---|:---|
| 后端框架 | FastAPI |
| AI 编排 | LangChain + LangGraph |
| 大语言模型 | DeepSeek（OpenAI 兼容 API） |
| Embedding | BAAI/bge-small-zh-v1.5（本地） |
| 向量数据库 | ChromaDB |
| 关系数据库 | SQLite（账号 / 会话 / 文件元数据） |
| 缓存 | Redis |
| 前端 | HTML + 原生 JS（Vue3 版本开发中） |

## 📁 项目结构

```
backend/
├── app.py                    # FastAPI 主入口（路由 / 中间件 / 生命周期）
├── schemas.py                # Pydantic 请求响应模型
├── requirements.txt          # 依赖清单
├── .env.example              # 环境变量模板
├── chat.html                 # 简易前端（联调用）
├── core/
│   ├── agent.py              # Agent 定义 + 会话历史读取
│   ├── tools.py              # 工具定义（检索 / 出题 / 评判）+ 运行时上下文
│   ├── rag.py                # RAG 链路（加载 / 切分 / 向量化 / 检索）
│   ├── prompts.py            # 多模式提示词
│   ├── middleware.py         # 中间件（上下文摘要压缩）
│   ├── auth_service.py       # 账号业务（密码哈希 / JWT）
│   ├── user_repository.py    # 数据访问层（用户 / 会话 / 消息 / 文件）
│   ├── cache.py              # Redis 缓存封装
│   ├── logger.py             # 日志配置
│   └── index_manager.py      # 文件名工具（重命名等）
├── models/                   # Embedding 模型目录（需自行下载）
├── data/                     # 运行时数据（数据库，自动生成）
├── uploads/                  # 上传文件目录（自动生成）
└── chroma_db/                # 向量库（自动生成）
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Redis（可选，不装则缓存功能自动禁用）
- 约 100MB 磁盘空间（Embedding 模型）

### 1. 安装依赖

```bash
conda create -n rag python=3.11
conda activate rag
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的配置：

```bash
cp .env.example .env
```

`.env` 内容说明：

| 变量 | 说明 |
|:---|:---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）|
| `DEEPSEEK_BASE_URL` | API 地址，默认 `https://api.deepseek.com` |
| `SECRET_KEY` | JWT 签名密钥，用 `python -c "import secrets; print(secrets.token_hex(32))"` 生成 |
| `ALGORITHM` | JWT 算法，默认 `HS256` |
| `TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟），默认 1440（24小时）|

### 3. 下载 Embedding 模型

项目使用 `BAAI/bge-small-zh-v1.5`，需下载到 `models/` 目录。

**方式一：从镜像站下载（推荐，国内）**

访问 [hf-mirror.com/BAAI/bge-small-zh-v1.5](https://hf-mirror.com/BAAI/bge-small-zh-v1.5)，
下载全部文件到 `backend/models/bge-small-zh-v1.5/` 目录。

**方式二：程序自动下载**

设置环境变量后首次运行会自动下载到本地缓存：

```bash
# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Linux / macOS
export HF_ENDPOINT=https://hf-mirror.com
```

**目录结构应为**：
```
models/bge-small-zh-v1.5/
├── config.json
├── model.safetensors    # 关键文件
├── tokenizer.json
└── ...
```

### 4. 启动服务

```bash
uvicorn app:app --reload
```

启动成功后：
- API 文档：http://127.0.0.1:8000/docs
- 简易前端：用浏览器打开 `chat.html`

### 5. （可选）启动 Redis

Redis 用于热点检索缓存，不装不影响功能（自动降级）：

```bash
redis-server
```

## 📖 API 接口

### 账号

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/api/register` | 注册（返回 JWT） |
| POST | `/api/login` | 登录（返回 JWT） |
| GET | `/api/me` | 获取当前用户信息 |

### 对话

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/api/chat` | 对话（支持多模式，自动创建会话）|

### 会话

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | `/api/sessions` | 会话列表 |
| GET | `/api/sessions/{id}/history` | 会话历史消息 |
| PUT | `/api/sessions/{id}` | 重命名会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |

### 文件

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/api/upload` | 上传文件（支持账号级/会话级）|
| GET | `/api/files` | 文件列表 |
| DELETE | `/api/files/{id}` | 删除文件 |

**鉴权**：除注册登录外，所有接口需在请求头携带 `Authorization: Bearer <token>`

## 📚 项目文档

- `项目说明.md` — 完整需求与架构设计
- `方案/` — 各模块技术方案（记忆持久化、账号系统、文件管理等）

## 🗺 开发规划

- [x] RAG 核心链路（加载 / 切分 / 向量化 / 检索）
- [x] Agent + 三个工具 + 多模式
- [x] 账号系统 + 用户隔离
- [x] 记忆持久化 + 上下文压缩
- [x] 会话管理 + 历史加载
- [x] 文件管理（可见范围 / 去重 / 删除）
- [x] Redis 热点缓存
- [x] 上传安全
- [ ] 混合检索（向量 + BM25）+ rerank 重排
- [ ] 流式输出（SSE）
- [ ] 图片 OCR
- [ ] 结构感知切分
- [ ] Vue3 前端
