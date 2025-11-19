import os
import dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import pathlib
import pynvml

env_path = '.env'
if pathlib.Path(env_path).exists():    
    dotenv.load_dotenv()

from backend import router, check_stop_idle_containers, ContainerManager
from exceptions import error_handler, unexpected_error_handler, BaseError
from logger import get_logger

logger = get_logger()
PRE_START = True if os.getenv('PRE_START', 'n').lower() == 'y' else False

@asynccontextmanager
async def lifespan(app: FastAPI):
    #pre start
    manager = ContainerManager()
    app.state.available_gpus = None
    try:
        pynvml.nvmlInit()
        app.state.available_gpus = pynvml.nvmlDeviceGetCount()
    except Exception:
        logger.warning('Could not determine number of GPU using nvml. Skipping.')
    if PRE_START:
        logger.info('Starting with pre-start version')
        await manager.pre_start()
    else:
        logger.info('Starting with load-on-demand version')
        asyncio.create_task(check_stop_idle_containers(manager))
    app.state.container_manager = manager

    yield

    #post start
    await manager.stop_all_container()
    if app.state.available_gpus:
        pynvml.nvmlShutdown()

app = FastAPI(lifespan=lifespan)


app.include_router(router)
app.add_exception_handler(BaseError, error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)