from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from backend import router, check_stop_idle_containers, ContainerManager
from exceptions import error_handler, unexpected_error_handler, BaseError

@asynccontextmanager
async def lifespan(app: FastAPI):
    #pre start
    manager = ContainerManager()
    app.state.container_manager = manager
    asyncio.create_task(check_stop_idle_containers(manager))
    yield
    #post start

app = FastAPI(lifespan=lifespan)


# app.add_route(router)
app.include_router(router)
app.add_exception_handler(BaseError, error_handler)
app.add_exception_handler(Exception, unexpected_error_handler)