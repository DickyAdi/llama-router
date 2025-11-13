FROM ghcr.io/ggml-org/llama.cpp:server-cuda AS llama-cpp-server
FROM python:3.12.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY ../config.yaml /app
COPY --from=llama-cpp-server /app/server /usr/local/bin/llama-server

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
