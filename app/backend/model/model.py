from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
import time
import httpx

# from ._internals import ContainerManager, last_request_time, container_status, model_config
from ._internals import ContainerManager, model_config
from logger import get_logger

router = APIRouter()
logger = get_logger()

@router.post('/v1/completions')
@router.post('/v1/chat/completions')
@router.post('/v1/embeddings')
async def chat_proxy_requests(req:Request):
    # global last_request_time
    # global container_status
    global model_config
    CONTAINER_MANAGER:ContainerManager = req.app.state.container_manager
    body = await req.json()
    model_name = body.get('model')

    # last_request_time[model_name] = time.time()
    CONTAINER_MANAGER.update_last_request_time(model_name)
    
    # if not container_status.get(model_name, False):
    if not CONTAINER_MANAGER._server_status.get(model_name, False):
        logger.info(f'Cold starting server for {model_name}')
        _succ = await CONTAINER_MANAGER.start_container(model_name)

    # config = model_config['models'][model_name]
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
    manager:ContainerManager = request.app.state.container_manager
    return {"status": "ok", "active_models": [k for k, v in manager._server_status.items() if v]}