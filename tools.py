from dotenv import load_dotenv
load_dotenv() 
from langchain.tools import tool
import mysql.connector
import os
from pushover_tool import send_pushover_notification

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_CHARSET = os.getenv("DB_CHARSET")
DB_COLLATION = os.getenv("DB_COLLATION")

def get_connection():
    return mysql.connector.connect(
        user=DB_USER,             
        password=DB_PASSWORD, 
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE,
        charset=DB_CHARSET,
        collation=DB_COLLATION       
    )

def save_order(customer_name, phone, items, note="", order_type="Mang về"):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (customer_name, phone, items, note, order_type) VALUES (%s, %s, %s, %s, %s)",
            (customer_name, phone, items, note, order_type)
        )
        conn.commit()
        cur.close()
        conn.close()
        message = f"Đơn hàng mới từ {customer_name} ({phone}) - {order_type}: {items}"
        send_pushover_notification(message)
        return f"✅ Đã lưu đơn hàng của {customer_name} ({phone}) vào DB!"
    except mysql.connector.Error as e:
        return f"❌ Lỗi khi lưu đơn hàng: {e}"


@tool
def save_order_tool(customer_name: str, phone: str, items: str, note: str = "", order_type: str = "Mang về") -> str:
    """
    Tool LƯU ĐƠN HÀNG vào cơ sở dữ liệu MySQL.
    BẮT BUỘC gọi tool này khi khách hàng đã cung cấp:
    - Tên khách hàng
    - Số điện thoại
    - Danh sách món ăn
    - Loại đơn hàng (Ăn tại quán hoặc Mang về)

    KHÔNG chỉ trả lời, mà phải gọi tool để ghi dữ liệu.
    """
    return save_order(customer_name, phone, items, note, order_type)
