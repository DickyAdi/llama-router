import asyncio
import time
import pathlib
import httpx

from logger import get_logger
from .config import load_config
from exceptions import ContainerUnhealthyError, ContainerError, ModelNotFound, ContainerNotFound

model_config = load_config('config.yaml')

# last_request_time:dict[str, float] = {}
# server_status:dict[str, bool] = {}
# server_proc:dict[str, asyncio.subprocess.Process] = {}
logger = get_logger()

class ContainerManager:
    def __init__(self):
        self._last_request_time:dict[str, float] = {}
        self._server_status:dict[str, bool] = {}
        self._server_proc:dict[str, asyncio.subprocess.Process] = {}
        self._locks:dict[str, asyncio.Lock] = {}
    
    async def start_container(self, model_name:str, timeout=120) -> bool:
        if model_name not in model_config['models']:
            raise ModelNotFound(model_name)
        if model_name not in self._locks:
            self._locks[model_name] = asyncio.Lock()
        
        cwd = model_config['server']['llama_server_path']
        host = model_config['server']['host']
        config = model_config['models'][model_name]
        port = config['port']
        # model_path = config['model_path']
        model_path = str(pathlib.Path(config['model_path']).expanduser().resolve())
        flag_config = config['config']

        async with self._locks[model_name]:
            if self._server_status.get(model_name, False):
                logger.info(f'Server for model {model_name} already running...')
                return True
            cmd = ['./llama-server', '-m', str(model_path),'--host', str(host), '--port', str(port), *flag_config]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=cwd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                logger.debug(f'printing cmd {cmd}')

                await asyncio.sleep(5)

                start_time = time.time()
                while time.time() - start_time <= timeout:
                    for i in range(30):
                        try:
                            async with httpx.AsyncClient() as http_client:
                                response = await http_client.get(
                                    url=f'http://{host}:{port}/health'
                                )
                                if response.status_code == 200:
                                    logger.info(f'Server for model {model_name} is ready.')
                                    self._server_status[model_name] = True
                                    self._server_proc[model_name] = proc
                                    return True
                        except httpx.ConnectError as e:
                            logger.warning(f'Health check attempt - Connection failed: {e}')
                        except httpx.TimeoutException as e:
                            logger.warning(f'Health check attempt - Timeout: {e}')
                        except Exception as e:
                            logger.warning(f'Health check attempt - Unexpected error: {type(e).__name__}: {e}')
                        await asyncio.sleep(5)
                raise ContainerUnhealthyError(model_name)
            except Exception:
                raise ContainerError(model_name)

    
    async def stop_container(self, model_name:str):
        if model_name not in model_config['models']:
            return
        
        if model_name not in self._locks:
            self._locks[model_name] = asyncio.Lock()

        async with self._locks[model_name]:
            proc = self._server_proc.get(model_name)

            try:
                if not proc:
                    logger.info(f'Server for model {model_name} already stopped')
                    return
                
                self._server_proc[model_name] = None
                self._server_status[model_name] = False
                
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=15)
                    logger.info(f'Terminating server for model {model_name} gracefully')
                except asyncio.TimeoutError:
                    logger.warning(f'Server for model {model_name} hung out. Killing with SIGKILL')
                    proc.kill()
                    await proc.wait()
            except Exception:
                raise

    def update_last_request_time(self, model_name:str):
        self._last_request_time[model_name] = time.time()

async def check_stop_idle_containers(container_manager:"ContainerManager", idle_time:int=180):
    """Check and stop idle container based on the given `idle_time`

    Args:
        idle_time (int, optional): Threshold for idle time. Defaults to 180.
    """
    while True:
        await asyncio.sleep(120)
        curr_time = time.time()
        for model_name, last_time in list(container_manager._last_request_time.items()):
            if curr_time - last_time > idle_time:
                if container_manager._server_status.get(model_name, False):
                    logger.info(f'Stopping idle server for model {model_name}')
                    await container_manager.stop_container(model_name)

