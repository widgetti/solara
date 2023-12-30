"""Method for accessing control"""
from functools import wraps
from starlette.requests import Request
from starlette.exceptions import HTTPException
from starlette import status
import os
import importlib.util
import logging
logger = logging.getLogger("solara.server.fastapi")

NOT_AUTHRIZED_MESSAGE = "No sufficient user previlege"

class BadAuthModulePath(Exception):
    """System doesn't find the existing file by the given path"""

class MethodNotFound(Exception):
    """authenticate method should exist in the auth module."""

def import_module_from_env_var(env_var_name):
    """
    Import a Python module from a file path defined in an environment variable.

    :param env_var_name: Name of the environment variable containing the file path.
    :return: Imported module or None if the file cannot be imported.
    """

    # Read the file path from the environment variable
    file_path = os.getenv(env_var_name)
    if not file_path:
        logger.info(f"Environment variable {env_var_name} is not set, no auth will be applied.")
        return None

    if not os.path.exists(file_path):
        logger.error(f"File {file_path} does not exist.")
        raise BadAuthModulePath('File {file_path} does not exist.')

    module_name = os.path.splitext(os.path.basename(file_path))[0]

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        getattr(module, 'authenticate')
        return module
    except AttributeError:
        raise MethodNotFound('authenticate method should exist in the auth module.')
    except Exception as e:
        raise e(f"Failed to import module: {e}")


def auth_required(func):
    """Allow user to customized the authentication when accessing a path."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if os.getenv('BASIC_AUTH_REQUIRED', None):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail=NOT_AUTHRIZED_MESSAGE
                )
            if module := import_module_from_env_var('BASIC_AUTH_MODULE_PATH'):
                if not module.authenticate(request, *args, **kwargs):
                    raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail=NOT_AUTHRIZED_MESSAGE
                )
        return await func(request, *args, **kwargs)
    return wrapper