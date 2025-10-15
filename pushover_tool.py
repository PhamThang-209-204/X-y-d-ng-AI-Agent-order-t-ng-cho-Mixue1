import requests
from langchain.tools import tool
import os

PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN")

@tool
def send_pushover_notification(message: str) -> str:
    """
    Gửi thông báo đến Pushover khi có đơn hàng mới.
    """
    try:
        if not PUSHOVER_USER_KEY or not PUSHOVER_APP_TOKEN:
            return "❌ Chưa cấu hình Pushover API keys."
        
        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": PUSHOVER_APP_TOKEN,
                "user": PUSHOVER_USER_KEY,
                "message": message
            }
        )
        if resp.status_code == 200:
            return "✅ Thông báo Pushover đã gửi thành công."
        else:
            return f"❌ Gửi thông báo thất bại: {resp.text}"
    except Exception as e:
        return f"❌ Lỗi khi gửi thông báo: {e}"
