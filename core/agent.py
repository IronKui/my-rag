
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from rich import print as rprint

from core.prompts import DEFAULT_PROMPT
from core.tools import model, retrieve_tool, quiz_tool, evaluate_tool

checkpointer = InMemorySaver()

agent = create_agent(
    model= model,
    tools=[retrieve_tool,quiz_tool,evaluate_tool],
    system_prompt= DEFAULT_PROMPT,
    checkpointer = checkpointer
)
config ={
    "configurable":{
        "thread_id":"1"
    }
}
#新增，供给app.py调用的函数方法：
def agent_chat(question:str,session_id:str = "default")->str:
    '''
    接收用户的问题，记录id，返回大模型的回复
    '''
    #把session_id映射到进程id
    config = {
        "configurable":{
        "thread_id":session_id
        }
    }
    #获取模型回复
    response = agent.invoke({"messages": [{"role": "user", "content": question}]}, config=config)
    return response['messages'][-1].content

if __name__ == "__main__":
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("对话结束，再见")
            break
        if not user_input or user_input.strip() == "":
            continue
        try:
            response = agent.invoke({"messages": [{"role": "user", "content": user_input}]},config=config)
            rprint(f"回复：{response}")
        except Exception as e:
            print(e)

        