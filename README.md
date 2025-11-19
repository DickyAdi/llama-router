# llama-router
llama-cpp model router

## Docker build
Docker image is ready to built. Follow the step below to build the image:
1. Clone the repo with `git clone https://github.com/DickyAdi/llama-router.git`
2. Go to /app with `cd app/`
3. Run docker build `docker build -t llama-router:latest .`
4. Wait for the process to finish and then go ahead check your docker image by doing `docker image ls`

## Pull image
You could also pull the latest image by running this command below
`docker pull ghcr.io/dickyadi/llama-router:dev`

## Docker run
The router has multiple start option which are on-demand load or pre-start load
- On-demand load
Each model server will only be loaded when there's a request that needs that model. After several idle time, the server will be shutdown to reduce memory usages. Suits best if resource are constrained
- Pre-start load
All detected model will be loaded once the application start, with this load approach it will significantly cut model loading time when constantly switching the models. Suits best if require fast model switching, however beware of Out Of Memory (OOM)

To use pre-start load, you could simply just provide `PRE_START="y"` in the docker run or compose. Look below

1. Run the image with this command below
    ```sh
    docker run -d --gpus all -p 8000:8000 \
    -v [your models folder]:/app/models \
    -v [your config.yaml file]:/app/config.yaml \
    -e PRE_START="y" \
    llama-router:latest #or ghcr.io/dickyadi/llama-router:dev depending on where you have the image
    ```
2. You could test the model router via localhost:8000/docs (FastAPI swagger UI) or using your endpoint tester such as postman or similar


## Notes

### Model directory path definition
When defining the models path, ensure the path points to the root of the models directory. Take a look at the example below.

```
.
└── models/ <---- models path must refer to this directory
    ├── Qwen2.5/ <----- not this
    │   └── Qwen2.5.gguf
    ├── Gemma3/ <----- or this
    │   └── Gemma3.gguf
    └── Qwen3-Embedding/ <----- or this
        └── Qwen3-Embedding.gguf
```

### Config writing guide
Here are the template of the config, which you could find in the config.template.yaml
```yaml
server:
  llama_server_path:
  host: "127.0.0.1"

models:
  Qwen3-Embedding:
    model_path: "Qwen3-Embedding/Qwen3-Embedding-0.6B-f16.gguf"
    port: 8081
    config: ["--no-webui", "--embeddings"]
```
Rules:
1. Leave llama_server_path to blanks unless you want to use your llama-server binary outside of the container (experimental)
2. When defining the models, ensure each model port is difference as the model will be served based on this port definition
3. Ensure `model_path` points/refer to the model directory inside the model root directory
4. `config` is any extra flag you could configure based on [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#Usage). Must be written in a list style, example `config: ["--n-gpu-layers", "0"]` notice the flag and the value is separated by comma