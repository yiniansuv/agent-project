import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

# 导入新的 create_agent（替代旧的 create_react_agent）
from langchain.agents import create_agent

# 导入工具装饰器，用来包装 PythonREPL
from langchain.tools import tool
# 导入 PythonREPL（注意它不再是工具，需要包装）
from langchain_experimental.utilities import PythonREPL

load_dotenv()

# 1. 模型
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)

# 2. 定义工具

# 搜索工具（直接可用）
search = DuckDuckGoSearchRun()

# Python 执行工具：将 PythonREPL 包装成一个标准工具
@tool
def python_repl_tool(code: str) -> str:
    """执行一段 Python 代码并返回输出结果。"""
    repl = PythonREPL()
    return repl.run(code)

tools = [search, python_repl_tool]

# 3. 创建 Agent（新方式）
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="你是一个有用的助手，可以使用搜索和Python代码执行工具来回答问题。"
)

# 4. 运行 Agent
result = agent.invoke({
    "messages": [("user", "告诉我今天上海的天气，然后用Python计算一下华氏温度。")]
})

# 5. 输出结果
print(result["messages"][-1].content)