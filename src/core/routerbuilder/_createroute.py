import os
import sys
import importlib
import functools
from typing import Any
from inspect import iscoroutinefunction
from fastapi import APIRouter
from pydantic import DirectoryPath
import logging

# initializing logging
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

    def __sync_decorator(self, func):

        # Use functools.wraps() so that the returned function "look like" for sync functions
        # the wrapped function
        @functools.wraps(func)
        def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
            value = func(*args, **kwargs)
            return value
        return wrapper_decorator
    
    def __async_decorator(self, func):

        # Use functools.wraps() so that the returned function "look like"  async functions
        # the wrapped function
        @functools.wraps(func)
        # def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
        async def wrapper_decorator(*args: Any, **kwargs: Any) -> Any:
            # value = asyncio.run(func(*args, **kwargs))
            value = await func(*args, **kwargs)
            return value
        return wrapper_decorator
    
    def __set_path(self):
        '''
        1. for all the apis module look for main and api_config
        2. main -> api entry point
        3. api_config -> loads api settings & documentations like path, response_model, tags, deprecations, etc
        4. create api curd type based on file name and function type (sync, async)
        '''
        try:
            for mod_name, modules in self.module_dict.items():
                for func in modules:
                    # assign end point function
                    endpoint_function = getattr(func, 'main')
                    # load api config in dictionary
                    api_config = getattr(func, 'api_config')().dict()
                    # reassign path if it's explicitly specified in the api configuration
                    api_config['path'] = f'{mod_name}' if api_config['path'] == '' else api_config['path']
                    # delete all the attributes which have None or ''
                    api_config = {key: value for key, value in api_config.items() if value is not None and value != ""}
                    # check if a function is sync or async and set a flag
                    if(iscoroutinefunction(endpoint_function)):
                        is_async = True
                    else:
                        is_async = False
                    # find curd opertaion based on file name and assign sync or async decortator based on the is_async flag
                    curd_op = func.__file__.split('/')[-1][:-3]
                    if(curd_op == 'post'):
                        self.router.post(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif(curd_op == 'get'):
                        self.router.get(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif(curd_op == 'delete'):
                        self.router.delete(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif(curd_op == 'put'):
                        self.router.put(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
                    elif(curd_op == 'patch'):
                        self.router.patch(**api_config)(self.__async_decorator(endpoint_function) if is_async else self.__sync_decorator(endpoint_function))
        except Exception as err:
            logger.error(f"Following error occured at {getattr(func, '__file__')} while setting the endpoints: {err}")
            exit()
        return                    
    
    def __load_module(self, path: tuple, file: str) -> list:
        '''
        loading modules dynamically
        '''
        try:
            file_path = f'{os.getcwd()}/{path[0]}/{file}'
            module_name = path[0][8:]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except ImportError as e:
                logger.error(f"Error importing module: {e}")
        except ModuleNotFoundError as err:
            logger.error(f"Error loading libraries at {file_path} : {err}")
            exit()
        except Exception as err:
            logger.error(f"Following error occured at {file_path} : {err}")
            exit()
        return module
        
    
    def router_config(self):
        '''
        module_dict -> dictionary to keep all the dynamically loaded api's module 
        1. function traverces through api directory and creates a path map
        2. pass the module path to load module for dynamically loading the functions from api directory
        3. calls set_path by passing module_dict for api end point creation
        '''
        
        try:
            for path in os.walk(self.dir_path):
            # checks for directory which has a file and ends with .py
                if(len(path[2]) != 0 and path[2][0].endswith('.py')):
                    # based on directory structure, creates a url path, and based on file name creates curd operation type
                    url_path, file_name = path[0][7:], path[2]
                    # adjusting url parameter, makes it a query parameter if "_" is encountered at the start of directory name
                    url_path = '/'.join([ '{' + a[1:] + '}'if a!='' and a[0] == '_' else a for a in url_path.split('/')])
                    # calling load modules for all the identified apis
                    self.module_dict[url_path] = [self.__load_module(path, file) for file in file_name]
                    logger.info(f'Route - {url_path}')
                    logger.info(f'Files - {file_name}')
            self.__set_path()
        except Exception as err:
            logger.error(f"Following error while loading modules: {err}")
            exit()
        return self.router