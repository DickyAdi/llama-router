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
    await manager.pre_start()
    app.state.container_manager = manager
    # asyncio.create_task(check_stop_idle_containers(manager))

    yield

    #post start
    await manager.stop_all_container()
    if app.state.available_gpus:
        pynvml.nvmlShutdown()

app = FastAPI(lifespan=lifespan)


app.include_router(router)
app.add_exception_handler(BaseError, error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)