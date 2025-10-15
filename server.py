from fastapi import FastAPI
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
from tools import save_order_tool
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import mysql.connector

app = FastAPI()

origins = ["http://127.0.0.1:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_DATABASE", "chatbot"),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci"
    )

API_KEY = os.getenv("API_KEY")
model = os.getenv("model")
llm = ChatGroq(api_key=API_KEY, model=model)

menu = """
Menu cửa hàng Mixue - Món nổi bật:
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


prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Bạn là nhân viên order Mixue thân thiện."
     " Giới thiệu menu cho khách ngay khi nói chuyện với họ."
     " Khi khách chọn món xong, nếu chưa cung cấp tên, số điện thoại hoặc loại đơn hàng (Ăn tại quán/Mang về) thì BẮT BUỘC hỏi đầy đủ."
     " Hỏi đầy đủ thông tin khách hàng thì mới được hỏi xác nhận đơn hàng."
     " Hiển thị lại thông tin đơn hàng: tên, số điện thoại, món đã chọn."
     " Hỏi khách: 'Thông tin trên đã chính xác chưa?'"
     """- Luôn hỏi và thu đủ thông tin:  
     - Tên khách hàng  
     - Số điện thoại  
     - Địa chỉ giao hàng  
   - Nếu thiếu thông tin → không tạo đơn."""
     " ✅ Nếu khách xác nhận đúng, gọi tool save_order_tool để lưu vào DB và thông báo khách chờ."
     " ❌ Nếu khách muốn thay đổi, không lưu và hỏi lại thông tin."
     " Khi lưu xong đơn hàng bắt buộc phải cảm ơn khách hàng."
     f"\nMenu hiện tại:\n{menu}"
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])


memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

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


class ChatInput(BaseModel):
    message: str
    session_uuid: str | None = None   


def create_session():
    session_uuid = str(uuid.uuid4())
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (session_uuid) VALUES (%s)", (session_uuid,))
    conn.commit()
    cursor.close()
    conn.close()
    return session_uuid

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

@app.post("/chat")
def chat(input_data: ChatInput):
    session_uuid = input_data.session_uuid or create_session()

    save_message(session_uuid, "user", input_data.message)

    # Gọi LLM
    result = agent_executor.invoke({"input": input_data.message})
    reply = result["output"]

    save_message(session_uuid, "assistant", reply)

    # ---- Kiểm tra nếu đơn hàng đã được lưu -> reset session và memory ----
    new_session_uuid = session_uuid
    if any(kw in reply.lower() for kw in ["đơn hàng đã được lưu", "đơn hàng của bạn đã được lưu", "cảm ơn"]):
        # tạo session mới
        new_session_uuid = create_session()

        # reset bộ nhớ hội thoại LangChain
        memory.clear()

        print("✅ Đơn hàng thành công — tạo session mới và reset memory")

    return {
        "response": reply,
        "session_uuid": new_session_uuid
    }
