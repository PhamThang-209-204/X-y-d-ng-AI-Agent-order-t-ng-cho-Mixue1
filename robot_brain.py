from dotenv import load_dotenv
load_dotenv() 
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor, create_tool_calling_agent
import os
import sys
from tools import save_order_tool

API_KEY = os.getenv("API_KEY")
model = os.getenv("model")

if not API_KEY:
    print("❌ Chưa thấy GROQ_API_KEY. Hãy set biến môi trường trước khi chạy.")
    sys.exit(1) 

llm = ChatGroq(
    api_key=API_KEY,
    model=model
)

menu = """
Menu cửa hàng Mixue:
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
     "Bạn là một nhân viên order đồ của Mixue thân thiện."
     " Khi có khách nói với bạn, bạn hãy giới thiệu bạn là nhân viên order và giới thiệu menu cho khách hàng."
     " Khi khách hàng chọn xong món, BẮT BUỘC hỏi thông tin khách hàng là tên, số điện thoại và ăn tại quán hay mang về."
     " Khi khách cung cấp thông tin xong, vui lòng cho khách hàng xem lại thông tin đơn hàng bao gồm cả tổng tiền đơn hàng, tên và số điện thoại khách hàng."
     " Sau đó HỎI KHÁCH: 'Thông tin trên đã chính xác chưa?'"
     " ✅ Nếu khách hàng xác nhận 'Đúng', 'Ok', 'Chính xác' thì bạn PHẢI gọi tool save_order_tool để lưu đơn hàng vào cơ sở dữ liệu."
     " ❌ Nếu khách hàng nói sai, thiếu hoặc muốn thay đổi thì KHÔNG gọi tool, mà hãy hỏi lại và cập nhật lại thông tin đơn hàng."
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

while True: 
    user_say = input("Xin chào! Quý khách muốn dùng gì?：")
    if user_say.lower() in ["exit", "quit"]:
        print("Tạm biệt! Hẹn gặp lại 👋")
        break
    res = agent_executor.invoke({"input": user_say})
    print(res["output"])


