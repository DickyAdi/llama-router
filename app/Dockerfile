FROM ghcr.io/ggml-org/llama.cpp:server-cuda AS llama-cpp-server

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Jakarta

RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.12 python3.12-venv curl \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

RUN ln -s /app/llama-server /usr/local/bin/llama-server
ENV LD_LIBRARY_PATH="/app:${LD_LIBRARY_PATH}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENTRYPOINT []

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]