import asyncio
import time
import pathlib
from pathlib import Path
import re
import httpx

from logger import get_logger
from .config import load_config
from exceptions import ContainerUnhealthyError, ContainerError, ModelNotFound, ContainerNotFound, ModelFileError, ContainerExitedEarly

model_config = load_config('config.yaml')

logger = get_logger()

class ContainerManager:
    """Container manager for model server
    """
    def __init__(self):
        self._last_request_time:dict[str, float] = {}
        self._server_status:dict[str, bool] = {}
        self._server_proc:dict[str, asyncio.subprocess.Process] = {}
        self._locks:dict[str, asyncio.Lock] = {}

    def _validate_gguf_file(self, path_str:str):
        pat = re.compile(r'0*1-of-\d+\.gguf$', re.IGNORECASE)
        path = Path(path_str)
        return (path.exists() and path.is_file() and path.suffix == '.gguf') or bool(pat.search(path_str))
    
    async def start_container(self, model_name:str, timeout=120) -> True:
        """Start container/server for the given `model_name`. This method will be based on the given config.

        Args:
            model_name (str): Model name based on the config. This is case sensitive and must be the same as the one specified within the config.yaml
            timeout (int, optional): Timeout setting when loading the model. Defaults to 120.

        Raises:
            ModelNotFound: If model doesnt exist within the config.yaml
            ContainerUnhealthyError: When starting the container/server and could not perform health check to determine if container/server is ready
            ContainerError: When starting the container/server encountered an error

        Returns:
            True: Return True if container/server is running and ready to use 
        """
        if model_name not in model_config['models']:
            raise ModelNotFound(model_name)
        if model_name not in self._locks:
            self._locks[model_name] = asyncio.Lock()
        
        cwd = model_config['server']['llama_server_path']
        host = model_config['server']['host']
        config = model_config['models'][model_name]
        port = config['port']
        model_path = str(pathlib.Path(config['model_path']).expanduser().resolve())
        if not self._validate_gguf_file(model_path):
            raise ModelFileError(model_path=model_path, model_name=model_name)
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

                await asyncio.sleep(2)

                if proc.returncode is not None:
                    raise ContainerExitedEarly(ret_code=proc.returncode, model_name=model_name)

                start_time = time.time()
                while time.time() - start_time <= timeout:
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as http_client:
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
                    await asyncio.sleep(3)
                raise ContainerUnhealthyError(model_name)
            except Exception:
                raise ContainerError(model_name)
    
    async def stop_container(self, model_name:str):
        """Will stop the running container/server based on the given `model_name`

        Args:
            model_name (str): The model name server that want to be stopped
        """
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
                
                self._server_status[model_name] = False
                
                try:
                    logger.info(f'Terminating server for model {model_name} gracefully')
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=15)
                    logger.info(f'Server for model {model_name} terminated gracefully')
                except asyncio.TimeoutError:
                    logger.warning(f'Server for model {model_name} hung out. Killing with SIGKILL')
                    proc.kill()
                    await proc.wait()
                finally:
                    self._server_proc[model_name] = None

            except Exception:
                raise

    async def stop_all_container(self):
        """Stop all running container/server. Usually used when closing/shutting down the app
        """
        logger.info(f'App shutting down, stopping all running model')
        if not self._server_status:
            logger.info('No server running')
            return
        for model_name, status in self._server_status.items():
            if status:
                logger.info(f'Stopping model {model_name} server')
                await self.stop_container(model_name)
            else:
                logger.info(f'Server model {model_name} already stopped')
                continue
        if not self._server_status:
            logger.error('Encountered an error while stopping all running server')
        else:
            logger.info('All running server stopped succesfully')

    def update_last_request_time(self, model_name:str):
        """Update last request time for the given model container/server

        Args:
            model_name (str): Model name server wished to be updated
        """
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

