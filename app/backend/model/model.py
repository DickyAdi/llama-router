from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
import time
import httpx
import pynvml

from ._internals import ContainerManager, model_config
from logger import get_logger

router = APIRouter()
logger = get_logger()

@router.post('/v1/completions')
@router.post('/v1/chat/completions')
@router.post('/v1/embeddings')
async def chat_proxy_requests(req:Request):
    """Proxy endpoint for all OpenAI compatible request

    Args:
        req (Request): FastAPI incoming request

    Returns:
        dict: Model responses, usually in a format of OpenAI response. See `https://platform.openai.com/docs/api-reference/chat/create`

    Yields:
        `fastapi.responses.StreamingResponse`: If request streaming response, then will yield FastAPI SSE generator
    """
    global model_config
    CONTAINER_MANAGER:ContainerManager = req.app.state.container_manager
    body = await req.json()
    model_name = body.get('model')

    await CONTAINER_MANAGER.update_last_request_time(model_name)
    
    logger.info(f'Cold starting server for {model_name}')
    _succ = await CONTAINER_MANAGER.start_container(model_name)

    config = model_config['models'].get(model_name)
    target_url = f'http://{model_config['server']['host']}:{config['port']}{req.url.path}'

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                url=target_url,
                json=body,
                timeout=300.0
            )

            if resp.headers.get('content-type', '').startswith('text/event-stream'):
                async def stream_response():
                    async for chunk in resp.aiter_bytes():
                        yield chunk

                return StreamingResponse(stream_response(), media_type='text/event-stream')
            else:
                return resp.json()
    except Exception:
        raise


@router.get("/health")
async def health(request:Request):
    """Health check to list all running server.

    Args:
        request (Request): FastAPI incoming request

    Returns:
        dict: Containing proxy server status and running model server status
    """
    manager:ContainerManager = request.app.state.container_manager
    n_gpu = request.app.state.available_gpus
    gpu_det = []
    if n_gpu:
        for n in range(n_gpu):
            handle = pynvml.nvmlDeviceGetHandleByIndex(n)
            name = pynvml.nvmlDeviceGetName(handle)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            used = info.used / 1024**3
            total = info.total / 1024**3
            gpu_det.append({
                'gpu_name' : name,
                'vram_usage': f'{used:.2f}/{total:.2f} GB'
            })

    return {"status": "ok", "active_models": [k for k, v in manager._server_status.items() if v], 'gpus': gpu_det}


@router.get('/v1/models')
async def list_models(request:Request):
    manager:ContainerManager = request.app.state.container_manager
    models = []
    for model, dict_value in manager._server_status.items():
        config = dict_value.get('config')
        ctx_size = config.get('--ctx-size') or config.get('-c') or 4096 # llama.cpp default context is 4096
        models.append(
            {
                'id': model,
                'object':'model',
                'owned_by': 'user',
                'n_ctx': int(ctx_size)
            }
        )
    return {
        'type':'list',
        'data': models
    }