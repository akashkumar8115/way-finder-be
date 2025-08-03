import os
import sys
import importlib
from pathlib import Path
import functools
from typing import Any, List
from inspect import iscoroutinefunction
from fastapi import APIRouter
from pydantic import DirectoryPath
import asyncio
import logging

# initializing logging
logger = logging.getLogger(__name__)


class DirectorySetup():
    def __init__(self, replicate_from: DirectoryPath, replicate_to: List[DirectoryPath]):
        self.replicate_from = replicate_from
        self.replicate_to = replicate_to
        return


    def __create_dir(self, file_path: str) -> list:
        '''
        loading modules dynamically
        '''

        logger.debug(file_path)

        # Create a Path object from the file path
        file_path = Path(file_path)

        # Ensure the parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create the file if it doesn't exist
        if not file_path.exists():
            file_path.touch()
            logger.info(f"File created: {file_path}")
        else:
            logger.info(f"File already exists: {file_path}")

        return


    def read_dir_structure(self):
        '''
        module_dict -> dictionary to keep all the dynamically loaded api's module 
        1. function traverces through api directory and creates a path map
        2. pass the module path to load module for dynamically loading the functions from api directory
        3. calls set_path by passing module_dict for api end point creation
        '''

        for path in os.walk(self.replicate_from):
            # checks for directory which has a file and ends with .py
            if(len(path[2]) != 0 and path[2][0][-3:] == '.py'):
                # based on directory structure, creates a url path, and based on file name creates curd operation type
                file_path, file_name = path[0], path[2]
                logger.debug(f'Route - {file_path}')
                logger.debug(f'Files - {file_name}')
                # calling load modules for all the identified apis
                [[self.__create_dir(os.path.join(file_path.replace(self.replicate_from._str, dirTo),file)) for file in file_name ] for dirTo in self.replicate_to]
        return