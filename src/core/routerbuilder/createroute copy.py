import os
import sys
import importlib
import functools
from typing import Any
from inspect import iscoroutinefunction
from fastapi import APIRouter, HTTPException
from pydantic import DirectoryPath
import logging
import traceback

# Initializing logging
logger = logging.getLogger(__name__)

class RouteBuilder:
    def __init__(self, dir_path: DirectoryPath):
        """
        Initializes an instance of the class.

        Args:
            dir_path (DirectoryPath): The directory path.

        Returns:
            None
        """
        self.dir_path = dir_path
        self.router = APIRouter()
        self.module_dict = {}
        self._load_modules()

    def __sync_decorator(self, func):
        @functools.wraps(func)
        def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Sync function error: {e}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail="Internal Server Error")
        return wrapper_decorator

    def __async_decorator(self, func):
        @functools.wraps(func)
        async def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Async function error: {e}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail="Internal Server Error")
        return wrapper_decorator

    def _load_modules(self):
        """
        Traverses through the API directory and creates a path map for dynamic loading of functions.
        """
        try:
            for path in os.walk(self.dir_path):
                if len(path[2]) != 0 and path[2][0][-3:] == '.py':
                    url_path, file_name = path[0][7:], path[2]
                    url_path = '/'.join(['{' + a[1:] + '}' if a != '' and a[0] == '_' else a for a in url_path.split('/')])
                    self.module_dict[url_path] = [self.__load_module(path, file) for file in file_name]
                    logger.info(f'Route - {url_path}')
                    logger.info(f'Files - {file_name}')
            self._set_path()
        except Exception as err:
            logger.error(f"Error while loading modules: {err}")
            traceback.print_exc()
            exit()

    def __load_module(self, path: tuple, file: str):
        """
        Loads modules dynamically based on the provided path and file.

        Args:
            path (tuple): The directory path.
            file (str): The file name.

        Returns:
            module: The loaded module.
        """
        try:
            file_path = f'{os.getcwd()}/{path[0]}/{file}'
            module_name = path[0][8:]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except ModuleNotFoundError as err:
            logger.error(f"Module not found at {file_path}: {err}")
            exit()
        except Exception as err:
            logger.error(f"Error loading module at {file_path}: {err}")
            traceback.print_exc()
            exit()

    def _set_path(self):
        """
        Sets the API paths based on the dynamically loaded modules.
        """
        try:
            for mod_name, modules in self.module_dict.items():
                for func in modules:
                    endpoint_function = getattr(func, 'main')
                    api_config = getattr(func, 'api_config')().dict()
                    api_config['path'] = f'{mod_name}' if api_config['path'] == '' else api_config['path']
                    api_config = {key: value for key, value in api_config.items() if value is not None and value != ""}
                    is_async = iscoroutinefunction(endpoint_function)
                    crud_op = func.__file__.split('/')[-1][:-3]
                    if crud_op == 'post':
                        self.router.post(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif crud_op == 'get':
                        self.router.get(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif crud_op == 'delete':
                        self.router.delete(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif crud_op == 'put':
                        self.router.put(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif crud_op == 'patch':
                        self.router.patch(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
        except Exception as err:
            logger.error(f"Error setting endpoints at {getattr(func, '__file__')}: {err}")
            traceback.print_exc()
            exit()

    def router_config(self):
        """
        Returns the configured APIRouter with dynamically loaded routes.
        """
        return self.router
