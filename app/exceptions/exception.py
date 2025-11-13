class BaseError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"

    def __reduce__(self):
        return (
            self.__class__,
            (
                getattr(self, "message", "Base exception message"),
                getattr(self, "error_code", None),
                getattr(self, "details", {}),
            ),
        )
    
class ModelNotFound(BaseError):
    def __init__(self, model_name:str):
        msg = f'Could not find {model_name}'
        super().__init__(message=msg, error_code='MODEL_NOT_FOUND', details={'model_name':model_name})

class ContainerUnhealthyError(BaseError):
    def __init__(self, container_name:str):
        msg = f'Could not perform healthcheck on container {container_name}'
        error_code = 'CONTAINER_UNHEALTHY'
        details = {
            'container_name': container_name
        }
        super().__init__(message=msg, error_code=error_code, details=details)

class ContainerError(BaseError):
    def __init__(self, container_name:str):
        msg = f'Error when starting container {container_name}'
        error_code = 'DOCKER_CONTAINER_ERROR'
        details = {
            'container_name':container_name
        }
        super().__init__(message=msg, error_code=error_code, details=details)

class ContainerNotFound(BaseError):
    def __init__(self, container_name:str):
        msg = f'Container {container_name} not found'
        error_code = 'CONTAINER_NOT_FOUND'
        details = {
            'container_name':container_name
        }
        super().__init__(message=msg, error_code=error_code, details=details)

class ModelFileError(BaseError):
    def __init__(self, model_path:str, model_name:str):
        msg = f"Model `{model_name}` file with path `{model_path}` does not pass sanity test. Ensure you are pointing to .gguf file. If shard, point to the first shard"
        error_code = 'MODEL_FILE_NOT_ACCESSIBLE'
        details = {
            'model_name': model_name,
            'model_path': model_path 
        }
        super().__init__(message=msg, error_code=error_code, details=details)

class ContainerExitedEarly(BaseError):
    def __init__(self, ret_code, model_name):
        msg = f"Server for {model_name} process exited early with code {ret_code}. Ensure args in config is correct."
        err = "CONTAINER_EXITED_EARLY"
        det = {
            'model_name': model_name,
            'return_code': ret_code
        }
        super().__init__(message=msg, error_code=err, details=det)