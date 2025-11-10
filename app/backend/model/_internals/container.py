import docker
import httpx
import asyncio
import time

from logger import get_logger
from .config import load_config
from exceptions import ContainerUnhealthyError, ContainerError, ModelNotFound, ContainerNotFound

model_config = load_config('../config.yaml')

client = docker.from_env()
# client = None # for testing the API, later delete this when ready to write the docker compose
last_request_time:dict[str, float] = {}
container_status:dict[str, bool] = {}
logger = get_logger()

class ContainerManager:
    @staticmethod
    async def start_container(model_name:str) -> bool:
        if model_name not in model_config['models']:
            # return False
            raise ModelNotFound(model_name)
        config = model_config['models'][model_name]
        container_name = config['container_name']

        try:
            container = client.containers.get(container_name)
            if container.status != 'running':
                logger.info(f'Container found {container_name}! Starting...')
                container.start()
            else:
                logger.info(f'Container {container_name} already running.')
            await asyncio.sleep(2)
            for i in range(30):
                try:
                    async with httpx.AsyncClient() as http_client:
                        response = await http_client.get(
                            url=f'http://localhost:{config['port']}/health',
                            timeout=2.0
                        )
                        if response.status_code == 200:
                            logger.info(f'Container {container_name} is ready.')
                            container_status[model_name] = True
                            return True
                except Exception:
                    await asyncio.sleep(2)
            # logger.error(f'Container {container_name} failed to start.')
            raise ContainerUnhealthyError(container_name)
        except Exception:
            # logger.error(f'Error when starting container {container_name}', exc_info=e)
            raise ContainerError(container_name)
    
    async def stop_container(model_name:str):
        if model_name not in model_config['models']:
            return
        
        config = model_config['models'][model_name]
        container_name = config['container_name']

        try:
            container = client.containers.get(container_name)
            logger.info(f'Stopping container {container_name}.')
            container.stop(timeout=10)
            container_status[model_name] = False
        except docker.errors.NotFound:
            # logger.warning(f'Container {container_name} doesnt exist. Stopping nothing!')
            raise ContainerNotFound(container_name)
        except Exception:
            # logger.error(f'Error when stopping container {container_name}.', exc_info=e)
            raise

async def check_stop_idle_containers(idle_time:int=180):
    """Check and stop idle container based on the given `idle_time`

    Args:
        idle_time (int, optional): Threshold for idle time. Defaults to 180.
    """
    while True:
        await asyncio.sleep(120)

        curr_time = time.time()
        for model_name, last_time in list(last_request_time.items()):
            if curr_time - last_time > idle_time:
                if container_status.get(model_name, False):
                    logger.info(f'Stopping idle container for model {model_name}')
                    await ContainerManager.stop_container(model_name)

