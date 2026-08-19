
from langchain.agents import create_agent

from langgraph.checkpoint.sqlite import SqliteSaver
from rich import print as rprint

from core.middleware import build_context_middleware
from core.prompts import DEFAULT_PROMPT, get_prompt
from core.tools import model, retrieve_tool, quiz_tool, evaluate_tool, Context
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_saver_ctx = SqliteSaver.from_conn_string(str(BASE_DIR/"data/checkpoints.sqlite"))
checkpointer = _saver_ctx.__enter__()

# agent = create_agent(
#     model= model,
#     tools=[retrieve_tool,quiz_tool,evaluate_tool],
#     system_prompt= DEFAULT_PROMPT,
#     checkpointer = checkpointer
# )
def create_agent_by_mode(mode:str):
    system_prompt = get_prompt(mode)
    return create_agent(
        model =model,
        tools=[retrieve_tool,
               quiz_tool,
               evaluate_tool
               ],
        system_prompt= system_prompt,
        context_schema=Context,   # 运行时上下文注入
        middleware=[
            build_context_middleware(4000,2000)
        ],
        checkpointer = checkpointer
    )
#agent字典,创建空字典，对话切换模式的时候可以再创建新的agent
AGENTS = {}
def get_agent(mode:str):
    mode=mode if mode in ("learning", "interview", "roleplay") else "default"
    if mode not in AGENTS:
        AGENTS[mode] = create_agent_by_mode(mode)
    return AGENTS[mode]

#新增，供给app.py调用的函数方法：
def agent_chat(question:str, mode:str="default", session_id:str="default", user_id:str="default")->str:
    '''
    接收用户的问题，记录id，返回大模型的回复
    '''
    agent = get_agent(mode)
    # thread_id 组合 user_id + session_id，隔离不同用户和会话的历史
    config = {
        "configurable":{
            "thread_id": f"{user_id}:{session_id}"
        }
    }
    # 通过 context 注入当前用户和会话（运行时，不闭包）
    context = Context(user_id=user_id, session_id=session_id)
    #获取模型回复
    res = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
        context=context
    )
    return res['messages'][-1].content

if __name__ == "__main__":
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("对话结束，再见")
            break
        if not user_input or user_input.strip() == "":
            continue
        try:
            agent = create_agent_by_mode("default")
            context = Context(user_id="cli", session_id="main")
            response = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config={"configurable": {"thread_id": "cli:main"}},
                context=context
            )
            rprint(f"回复：{response['messages'][-1].content}")
        except Exception as e:
            print(e)

        