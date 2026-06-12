# ============================================================
# Multi-stage Dockerfile — image nhỏ, chạy bằng non-root user
#
# Khác bài mẫu: dùng VIRTUALENV (/opt/venv) thay cho pip --user.
# Cách này tránh hẳn lỗi "không tìm thấy thư viện" do home/PYTHONPATH.
# ============================================================

# ── Stage 1: builder — cài thư viện vào một virtualenv ──────
FROM python:3.11-slim AS builder

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime — chỉ bê virtualenv + code sang ───────
FROM python:3.11-slim AS runtime

# Non-root user cho an toàn
RUN useradd -m -r appuser

# Copy virtualenv đã cài sẵn từ builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . .
RUN chown -R appuser:appuser /app

USER appuser

ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check — đọc cổng từ $PORT (mặc định 8000 khi chạy local)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c \
    "import os,urllib.request; urllib.request.urlopen('http://localhost:'+os.getenv('PORT','8000')+'/health')" \
    || exit 1

# $PORT do Render/Railway tự cấp; exec để uvicorn nhận SIGTERM trực tiếp
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
