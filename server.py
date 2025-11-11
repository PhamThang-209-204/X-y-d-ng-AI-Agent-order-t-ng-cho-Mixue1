from fastapi import FastAPI
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
from tools import save_order_tool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
import mysql.connector
from dotenv import load_dotenv   # ✅ Thêm

# ✅ Load các biến môi trường từ file .env
load_dotenv()

# ---- Khởi tạo FastAPI ----
app = FastAPI()

# ---- Cấu hình CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi domain (nếu bạn muốn chỉ localhost:3000 thì đổi ở đây)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Xử lý preflight request (OPTIONS /chat) ----
@app.options("/chat")
async def options_chat():
    return JSONResponse(status_code=200, content={"message": "OK"})


# ---- Kết nối Database ----
def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_DATABASE", "chatbot"),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci"
    )


# ---- Khởi tạo LLM ----
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("model")

llm = ChatGroq(api_key=API_KEY, model=MODEL)

# ---- Menu Mixue ----
menu = """
🍧 Menu Mixue:
1. Kem ốc quế - 10k (Must Try)
2. Super sundae trân châu đường đen - 25k (Must Try)
3. Sữa kem lắc dâu tây - 25k (Best Seller)
4. Hồng trà kem - 25k
5. Nước chanh tươi lạnh - 20k (Must Try)
6. Dương chi cam lộ - 35k
7. Trà sữa trân châu đường đen - 25k
8. Trà Đào Bốn Mùa - 25k (Must Try)
9. Hồng trà vải - 25k
"""

# ---- Prompt chính ----
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Bạn là nhân viên order Mixue thân thiện."
     " Giới thiệu menu cho khách ngay khi bắt đầu trò chuyện."
     " Khi khách chọn món, nếu chưa cung cấp tên, số điện thoại hoặc loại đơn hàng (Ăn tại quán/Mang về) thì BẮT BUỘC hỏi đủ."
     " Sau khi có đủ thông tin, hãy hiển thị lại đơn hàng gồm: tên, số điện thoại, món đã chọn."
     " Hỏi khách: 'Thông tin trên đã chính xác chưa?'"
     " ✅ Nếu khách xác nhận đúng, gọi tool save_order_tool để lưu đơn hàng vào DB và cảm ơn khách."
     " ❌ Nếu khách muốn thay đổi, hỏi lại thông tin cần sửa."
     f"\nMenu hiện tại:\n{menu}"
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# ---- Bộ nhớ hội thoại ----
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# ---- Tạo agent ----
agent = create_tool_calling_agent(
    llm=llm,
    tools=[save_order_tool],
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=[save_order_tool],
    memory=memory,
    verbose=True,
)


# ---- Model input ----
class ChatInput(BaseModel):
    message: str
    session_uuid: str | None = None


# ---- Tạo session ----
def create_session():
    session_uuid = str(uuid.uuid4())
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (session_uuid) VALUES (%s)", (session_uuid,))
    conn.commit()
    cursor.close()
    conn.close()
    return session_uuid


# ---- Lưu message ----
def save_message(session_uuid: str, role: str, content: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (session_uuid, role, content) VALUES (%s, %s, %s)",
        (session_uuid, role, content)
    )
    conn.commit()
    cursor.close()
    conn.close()


# ---- Route chính /chat ----
@app.post("/chat")
def chat(input_data: ChatInput):
    session_uuid = input_data.session_uuid or create_session()

    save_message(session_uuid, "user", input_data.message)

    result = agent_executor.invoke({"input": input_data.message})
    reply = result["output"]

    save_message(session_uuid, "assistant", reply)

    new_session_uuid = None
    try:
        if "actions" in result and any(
            act.tool == "save_order_tool" for act in result["actions"]
        ):
            new_session_uuid = create_session()
    except Exception as e:
        print("Không tìm thấy tool call:", e)

    return {
        "response": reply,
        "session_uuid": new_session_uuid or session_uuid
    }
