from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exception import BaseError
from logger.log import get_logger

STATUS_CODE_MAP = {
    'MODEL_NOT_FOUND': status.HTTP_404_NOT_FOUND,
    'CONTAINER_UNHEALTHY': status.HTTP_503_SERVICE_UNAVAILABLE,
    'DOCKER_CONTAINER_ERROR': status.HTTP_500_INTERNAL_SERVER_ERROR,
    'CONTAINER_NOT_FOUND': status.HTTP_404_NOT_FOUND,
    'MODEL_FILE_NOT_ACCESSIBLE': status.HTTP_404_NOT_FOUND,
    'CONTAINER_EXITED_EARLY': status.HTTP_503_SERVICE_UNAVAILABLE
}

logger = get_logger()

async def error_handler(request:Request, exc:BaseError):
    """Global exception handler

    Args:
        request (Request): FastAPI request that cause this error.
        exc (BaseError): Received exception/error.
    """
    status_code = STATUS_CODE_MAP.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    response_content = {
        'error_code': exc.error_code,
        'message': exc.message,
        'details': exc.details
    }

    if status_code >= 500:
        logger.error('Server error: %s - %s', exc.error_code, exc.message, exc_info=True)
        response_content['message'] = "Unexpected error occured. Please try again later"
    else:
        logger.info('Client error: %s - %s', exc.error_code, exc.message)

    if exc.error_code != 'CONTAINER_NOT_FOUND':
        resp = JSONResponse(
            content=response_content, status_code=status_code
        )
        return resp
    else:
        pass # pass due to unimportant error for now

async def unexpected_error_handler(request:Request, exc:Exception):
    """Handle unexpected exceptions

    Args:
        request (Request): FastAPI request that cause this error.
        exc (Exception): Received exception/error.
    """
    logger.error(
    f"Unexpected error in {request.method} {request.url}: {type(exc).__name__}: {exc}",
    exc_info=True,
    extra={
        "method": request.method,
        "url": str(request.url),
    },
)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occured. Please try again later.",
            "details": {},
        },
    )