import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_experimental.utilities import PythonREPL
from langchain.tools import tool
from langchain.agents import create_agent
from datetime import datetime
import uuid

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="🧠 小智AI助理",
    layout="centered"
)

load_dotenv()

# ==================== 工具定义 ====================
@tool
def get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取当前系统时间"""
    return datetime.now().strftime(format)

@tool
def read_text_file(file_path: str) -> str:
    """读取指定路径的文本文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败: {str(e)}"

# ==================== 初始化 Agent ====================
@st.cache_resource
def get_agent():
    llm = ChatOpenAI(
        model="deepseek-chat",
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0
    )
    
    search = DuckDuckGoSearchRun()
    
    @tool
    def python_repl_tool(code: str) -> str:
        """执行 Python 代码"""
        repl = PythonREPL()
        return repl.run(code)
    
    tools = [
        search,
        python_repl_tool,
        get_current_time,
        read_text_file
    ]
    
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="""你好！我叫小智,是一个AI智能助理。你可以使用搜索、Python执行、获取时间、读取文件等工具。
        如果用户上传了文件，文件内容会通过系统消息提供，你可以直接利用这些内容回答问题。"""
    )
    return agent

# ==================== 对话管理初始化 ====================
if "conversations" not in st.session_state:
    first_id = str(uuid.uuid4())
    st.session_state.conversations = {
        first_id: {
            "title": "新对话",
            "messages": [{"role": "assistant", "content": "你好！我是小智AI助理，你的智能助手，有什么可以帮你的吗？😊"}]
        }
    }
    st.session_state.current_id = first_id

if "uploaded_file_content" not in st.session_state:
    st.session_state.uploaded_file_content = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# ==================== 辅助函数 ====================
def get_current_messages():
    return st.session_state.conversations[st.session_state.current_id]["messages"]

def set_current_messages(messages):
    st.session_state.conversations[st.session_state.current_id]["messages"] = messages

def add_message(role, content):
    msgs = get_current_messages()
    msgs.append({"role": role, "content": content})
    set_current_messages(msgs)

def save_current_conversation():
    msgs = get_current_messages()
    for msg in msgs:
        if msg["role"] == "user":
            title = msg["content"][:10] + ("..." if len(msg["content"]) > 10 else "")
            st.session_state.conversations[st.session_state.current_id]["title"] = title
            break

def switch_conversation(conv_id):
    save_current_conversation()
    st.session_state.current_id = conv_id
    st.session_state.uploaded_file_content = None
    st.session_state.uploaded_file_name = None
    st.rerun()

def new_conversation():
    save_current_conversation()
    new_id = str(uuid.uuid4())
    st.session_state.conversations[new_id] = {
        "title": "新对话",
        "messages": [{"role": "assistant", "content": "你好！我是小智AI助理，有什么新问题吗？😊"}]
    }
    st.session_state.current_id = new_id
    st.session_state.uploaded_file_content = None
    st.session_state.uploaded_file_name = None
    st.rerun()

def delete_conversation(conv_id):
    if len(st.session_state.conversations) <= 1:
        st.warning("至少保留一个对话")
        return
    del st.session_state.conversations[conv_id]
    if conv_id == st.session_state.current_id:
        st.session_state.current_id = list(st.session_state.conversations.keys())[0]
    st.session_state.uploaded_file_content = None
    st.session_state.uploaded_file_name = None
    st.rerun()

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("### 💬 对话管理")
    if st.button("➕ 新建对话", use_container_width=True):
        new_conversation()
    
    st.divider()
    
    st.markdown("#### 历史对话")
    conv_ids = list(st.session_state.conversations.keys())
    for cid in reversed(conv_ids):
        conv = st.session_state.conversations[cid]
        title = conv["title"]
        if cid == st.session_state.current_id:
            st.markdown(f"**👉 {title}**")
        else:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(title, key=f"switch_{cid}", use_container_width=True):
                    switch_conversation(cid)
            with col2:
                if st.button("✕", key=f"del_{cid}", help="删除此对话"):
                    delete_conversation(cid)
    
    st.divider()
    
    st.markdown("### 📤 上传文件")
    uploaded_file = st.file_uploader(
        "选择文件",
        type=["txt", "csv", "md", "py", "json", "xml", "html"],
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            try:
                uploaded_file.seek(0)
                content = uploaded_file.read().decode("gbk")
            except Exception as e:
                st.error(f"文件编码不支持：{e}")
                content = None
        
        if content:
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.uploaded_file_content = content
            system_msg = f"用户上传了文件《{uploaded_file.name}》，内容如下：\n```\n{content[:2000]}{'...(内容过长已截断)' if len(content) > 2000 else ''}\n```"
            msgs = get_current_messages()
            replaced = False
            for i, msg in enumerate(msgs):
                if msg["role"] == "system" and "用户上传了文件" in msg["content"]:
                    msgs[i] = {"role": "system", "content": system_msg}
                    replaced = True
                    break
            if not replaced:
                msgs.insert(0, {"role": "system", "content": system_msg})
            set_current_messages(msgs)
            st.success(f"✅ 已加载文件：{uploaded_file.name}")
            st.rerun()
    
    if st.button("🗑️ 清除上传的文件"):
        st.session_state.uploaded_file_content = None
        st.session_state.uploaded_file_name = None
        msgs = get_current_messages()
        msgs = [msg for msg in msgs if not (msg["role"] == "system" and "用户上传了文件" in msg["content"])]
        set_current_messages(msgs)
        st.success("已清除上传的文件内容")
        st.rerun()

# ==================== 显示当前对话 ====================
st.title("🧠 小智AI助理")
st.caption("💡 支持多轮对话 · 文件上传 · 搜索 · 代码执行")

msgs = get_current_messages()
for msg in msgs:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==================== 输入框 ====================
if prompt := st.chat_input("输入你的问题……"):
    add_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("思考中……"):
            try:
                agent = get_agent()
                result = agent.invoke({
                    "messages": get_current_messages()
                })
                answer = result["messages"][-1].content
                st.markdown(answer)
                add_message("assistant", answer)
                save_current_conversation()
            except Exception as e:
                error_msg = f"❌ 出错了：{str(e)}"
                st.error(error_msg)
                add_message("assistant", error_msg)