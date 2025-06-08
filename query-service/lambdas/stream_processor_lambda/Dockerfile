# Multi-stage Dockerfile for Stream Processor Lambda

# ==========================================
# Build Stage - 用於安裝依賴
# ==========================================
FROM public.ecr.aws/lambda/python:3.12 as builder

# 複製 requirements.txt 文件
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# 升級 pip 並安裝依賴到臨時目錄
RUN pip install --no-cache-dir --upgrade pip==25 && \
    pip install --no-cache-dir -r requirements.txt -t /tmp/packages

# ==========================================
# Runtime Stage - 最終運行環境
# ==========================================
FROM public.ecr.aws/lambda/python:3.12 as runtime

# 從 builder stage 複製安裝的依賴
COPY --from=builder /tmp/packages ${LAMBDA_TASK_ROOT}

# 複製應用程式代碼
COPY app.py ${LAMBDA_TASK_ROOT}
COPY __init__.py ${LAMBDA_TASK_ROOT}

# 設置 Lambda 函數的處理程序
CMD ["app.lambda_handler"]
