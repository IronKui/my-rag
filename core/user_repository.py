import sqlite3
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR/"data/users.db"

def get_connection():
    """
    获取数据库连接
    """
    conn = sqlite3.connect(str(DB_DIR))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    初始化数据库，建表
    """
    conn =get_connection()
    cur =conn.cursor()

    #user表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_uuid TEXT NOT NULL UNIQUE ,
        username TEXT NOT NULL UNIQUE,
        nickname TEXT DEFAULT '',
        password_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)
    #session 表（会话元数据，内容存 LangGraph checkpoints）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_uuid TEXT NOT NULL,
        session_id TEXT NOT NULL UNIQUE,
        session_name TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_uuid) REFERENCES users(user_uuid)
    )
    """)
    #messages 表（完整对话历史，供用户查看，不受上下文压缩影响）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_uuid TEXT NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_uuid) REFERENCES users(user_uuid)
    )
    """)
    conn.commit()
    conn.close()
    print("数据库初始话完毕")


def create_user(username: str, password_hash: str, nickname: str = "") -> str:
    """插入新用户，没传昵称自动生成，返回用户id"""
    #查重
    if get_user_by_username(username):
        raise ValueError(f"该用户名已被占用")

    #没有昵称就用用户名
    if not nickname:
        nickname = f"用户{username}"

    #生成uuid
    user_uuid = str(uuid.uuid4())

    #插入执行
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(user_uuid, username ,nickname,password_hash) VALUES (?,?,?,?)",
            (user_uuid, username, nickname, password_hash)
        )
        conn.commit()
        return user_uuid
    except sqlite3.IntegrityError as e:
        # 极低概率：user_uuid 冲突
        raise RuntimeError("注册失败，请重试")
    finally:
        conn.close()

def get_user_by_username(username: str, include_deleted: bool = False):
    conn = get_connection()
    cur = conn.cursor()
    if include_deleted:
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    else:
        cur.execute("SELECT * FROM users WHERE username = ? AND status = 'active'", (username,))
    user = cur.fetchone()
    conn.close()
    return user


# ========== 会话表操作 ==========

def create_session(user_uuid: str, session_id: str, first_message: str = ""):
    """创建会话记录，从第一条消息生成会话名，返回是否成功"""
    # 从第一条消息截取前20字作为会话名
    if first_message and first_message.strip():
        session_name = first_message.strip()[:20]
        if len(first_message.strip()) > 20:
            session_name += "..."
    else:
        session_name = "新会话"

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO sessions (user_uuid, session_id, session_name) VALUES (?, ?, ?)",
            (user_uuid, session_id, session_name)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # session_id 重复
    finally:
        conn.close()


def get_sessions_by_user(user_uuid: str):
    """获取某用户的会话列表，按最后更新时间倒序"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT session_id, session_name, created_at, updated_at FROM sessions WHERE user_uuid = ? ORDER BY updated_at DESC",
        (user_uuid,)
    )
    sessions = cur.fetchall()
    conn.close()
    return sessions


def get_session_by_id(user_uuid: str, session_id: str):
    """查询某个会话是否属于该用户，返回会话记录或 None"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM sessions WHERE user_uuid = ? AND session_id = ?",
        (user_uuid, session_id)
    )
    session = cur.fetchone()
    conn.close()
    return session


def update_session_time(user_uuid: str, session_id: str):
    """更新会话最后使用时间"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET updated_at = datetime('now') WHERE user_uuid = ? AND session_id = ?",
        (user_uuid, session_id)
    )
    conn.commit()
    conn.close()


def delete_session(user_uuid: str, session_id: str):
    """删除会话记录"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM sessions WHERE user_uuid = ? AND session_id = ?",
        (user_uuid, session_id)
    )
    conn.commit()
    conn.close()


def rename_session(user_uuid: str, session_id: str, session_name: str):
    """重命名会话"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET session_name = ? WHERE user_uuid = ? AND session_id = ?",
        (session_name, user_uuid, session_id)
    )
    conn.commit()
    conn.close()


# ========== 消息表操作（完整对话历史，用户可见） ==========

def save_message(user_uuid: str, session_id: str, role: str, content: str):
    """保存一条消息（完整历史，不受压缩影响）"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (user_uuid, session_id, role, content) VALUES (?, ?, ?, ?)",
        (user_uuid, session_id, role, content)
    )
    conn.commit()
    conn.close()


def get_messages_by_session(user_uuid: str, session_id: str) -> list:
    """获取某会话的完整历史消息，按时间正序"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE user_uuid = ? AND session_id = ? ORDER BY id ASC",
        (user_uuid, session_id)
    )
    messages = cur.fetchall()
    conn.close()
    return messages