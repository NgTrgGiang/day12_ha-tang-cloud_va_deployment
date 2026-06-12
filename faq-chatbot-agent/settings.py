"""
Cấu hình tập trung — đọc tất cả từ biến môi trường (nguyên tắc 12-Factor).

Khác bài mẫu: ở đây dùng `pydantic-settings` (BaseSettings) thay cho dataclass.
pydantic-settings tự động map biến môi trường theo TÊN field (không phân biệt hoa thường),
và đọc thêm từ file .env nếu có.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Đọc .env nếu tồn tại; bỏ qua biến môi trường lạ không khai báo ở đây
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    debug: bool = False

    # App
    app_name: str = "FAQ Chatbot Agent"
    app_version: str = "1.0.0"

    # Bảo mật — KHÔNG để giá trị thật trong code
    api_key: str = "dev-key-doi-trong-production"
    allowed_origins: str = "*"

    # Giới hạn
    rate_limit_per_minute: int = 15
    daily_budget_usd: float = 2.0

    # LLM (tùy chọn — trống thì dùng FAQ brain offline)
    openai_api_key: str = ""

    def origins_list(self) -> list[str]:
        """Tách chuỗi ALLOWED_ORIGINS thành danh sách cho CORS."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


# Singleton — import từ file nào cũng dùng chung một cấu hình
settings = Settings()
