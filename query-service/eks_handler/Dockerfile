# Multi-stage Dockerfile for Query Service

# ==========================================
# Build Stage - 用於安裝依賴和構建
# ==========================================
FROM python:3.12-slim as builder

# 安裝構建依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    && rm -rf /var/lib/apt/lists/*

# 創建虛擬環境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 複製並安裝 Python 依賴
WORKDIR /opt/build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==25 && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# Runtime Stage - 最終運行環境
# ==========================================
FROM python:3.12-slim as runtime

# 創建非 root 用戶
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# 安裝運行時依賴（僅健康檢查需要的 curl）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 設置工作目錄
WORKDIR /app

# 從 builder stage 複製虛擬環境
COPY --from=builder /opt/venv /opt/venv

# 複製應用程式碼
COPY . .

# 設置目錄擁有者為 appuser
RUN chown -R appuser:appgroup /app

# 切換到非 root 用戶
USER appuser

# 設置環境變數
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
