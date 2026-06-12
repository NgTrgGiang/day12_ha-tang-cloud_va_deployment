"""
FAQ Brain — "bộ não" tra cứu câu hỏi thường gặp của shop online ShopMini.

Đây là phần đứng thay cho LLM thật: dựa vào từ khóa trong câu hỏi để chọn câu trả lời.
Khi có API key thật (OpenAI/Anthropic), chỉ cần thay hàm answer() bằng lời gọi LLM.
"""
import time
import random

# Kho tri thức FAQ: "từ_khóa1|từ_khóa2" -> câu trả lời
FAQ = {
    "ship|giao|vận chuyển|bao lâu|ship":
        "ShopMini giao nội thành trong 1-2 ngày, ngoại tỉnh 3-5 ngày. "
        "Phí ship đồng giá 25.000đ, miễn phí cho đơn trên 300.000đ.",
    "đổi|trả|hoàn|return":
        "Bạn được đổi/trả hàng trong vòng 7 ngày kể từ khi nhận, "
        "miễn phí nếu lỗi từ shop. Liên hệ hotline 1900-xxxx để được hỗ trợ.",
    "thanh toán|payment|trả tiền|cod|chuyển khoản":
        "ShopMini hỗ trợ thanh toán khi nhận hàng (COD), chuyển khoản ngân hàng, "
        "và ví điện tử Momo/ZaloPay.",
    "giờ|mở cửa|làm việc|hoạt động":
        "Cửa hàng và tổng đài hoạt động 8h-22h tất cả các ngày trong tuần.",
    "khuyến mãi|giảm giá|voucher|mã|sale":
        "Nhập mã NEWBIE để giảm 10% cho đơn đầu tiên. "
        "Theo dõi fanpage ShopMini để nhận voucher mỗi tuần.",
    "địa chỉ|cửa hàng|ở đâu|chi nhánh":
        "ShopMini ở 123 Đường ABC, Quận 1, TP.HCM. "
        "Bạn có thể đến trực tiếp hoặc đặt online.",
}

GREETING = ("Xin chào! Mình là trợ lý ảo của ShopMini. "
            "Bạn cần hỗ trợ gì về đơn hàng, vận chuyển hay đổi trả?")

FALLBACK = ("Xin lỗi, mình chưa có thông tin cho câu hỏi này. Bạn thử hỏi về: "
            "vận chuyển, đổi trả, thanh toán, khuyến mãi, giờ mở cửa, hoặc địa chỉ nhé.")


def answer(message: str, delay: float = 0.05) -> str:
    """Nhận tin nhắn của khách, trả về câu trả lời FAQ phù hợp."""
    time.sleep(delay + random.uniform(0, 0.05))  # giả lập độ trễ gọi API thật
    text = message.lower()

    # Lời chào
    if any(g in text for g in ["xin chào", "hello", "hi ", "chào", "alo"]):
        return GREETING

    # Dò từng nhóm từ khóa
    for keywords, response in FAQ.items():
        if any(kw in text for kw in keywords.split("|")):
            return response

    return FALLBACK
