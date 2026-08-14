
from langchain.agents import create_agent

from langgraph.checkpoint.sqlite import SqliteSaver
from rich import print as rprint

from core.prompts import DEFAULT_PROMPT, get_prompt
from core.tools import model,  make_retrieve_tool, make_quiz_tool, evaluate_tool

_saver_ctx = SqliteSaver.from_conn_string("checkpoints.sqlite")
checkpointer = _saver_ctx.__enter__()

# agent = create_agent(
#     model= model,
#     tools=[retrieve_tool,quiz_tool,evaluate_tool],
#     system_prompt= DEFAULT_PROMPT,
#     checkpointer = checkpointer
# )
def create_agent_by_mode(mode:str,user_id:str):
    system_prompt = get_prompt(mode)
    return create_agent(
        model =model,
        tools=[make_retrieve_tool(user_id),make_quiz_tool(user_id),evaluate_tool],
        system_prompt= system_prompt,
        checkpointer = checkpointer
    )
#agent字典,创建空字典，对话切换模式的时候可以再创建新的agent
AGENTS = {}
def get_agent( mode:str,user_id:str):
    mode=mode if mode in ("learning", "interview", "roleplay") else "default"
    key = (user_id,mode)
    if key not in AGENTS:
        AGENTS[key] = create_agent_by_mode(mode,user_id)
    return AGENTS[key]

#新增，供给app.py调用的函数方法：
def agent_chat( question:str,mode:str="default",session_id:str = "default",user_id ="default")->str:
    '''
    接收用户的问题，记录id，返回大模型的回复
    '''
    agent = get_agent(mode,user_id)
    #把session_id映射到进程id
    config = {
        "configurable":{
        "thread_id":session_id
        }
    }
    #获取模型回复
    res = agent.invoke({"messages": [{"role": "user", "content": question}]}, config=config)
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
            agent = create_agent_by_mode("default","default")
            response = agent.invoke({"messages": [{"role": "user", "content": user_input}]},config={"configurable":{"thread_id":"1"}})
            rprint(f"回复：{response['messages'][-1].content}")
        except Exception as e:
            print(e)

        