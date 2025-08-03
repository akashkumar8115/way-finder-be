# import os
# from pathlib import Path
# from dotenv import load_dotenv

# import yaml
# from pydantic import FilePath
# from src.datamodel.datavalidation.appconfig import ApplicationConfig

# class LoadConfig():
#     def __init__(self):
#         self.app_config: ApplicationConfig
#         return
    
#     def override_with_key_valt(self) -> ApplicationConfig:
#         '''
#         override all the config values if it's set in key valt
#         '''

#         '''
#         next step: load and override
#         '''

#         return self.app_config
    
#     def override_with_env(self) -> ApplicationConfig:
#         '''
#         override all the config values if it's set in env variable
#         '''
#         env_path = Path('.') / '.env.local'
#         load_dotenv(dotenv_path=env_path) 
#         '''
#         next step: load and override
#         https://www.fastapitutorial.com/blog/database-connection-fastapi/
#         '''


#         return self.app_config
    
#     def load_config(self, file_path: FilePath) -> ApplicationConfig:
#         '''
#         Load application config
#         '''
#         with open(file_path, "r") as file:
#             config_data = yaml.safe_load(file)
#         # standandarized app config
#         self.app_config = ApplicationConfig(**config_data)
#         # over ride config with env
#         self.app_config = self.override_with_env()
#         # over ride config with key valt
#         self.app_config = self.override_with_key_valt()
#         return self.app_config


import os
from pathlib import Path
from dotenv import load_dotenv

import yaml
from pydantic import FilePath
from src.datamodel.datavalidation.appconfig import ApplicationConfig

class LoadConfig():
    def __init__(self):
        self.app_config: ApplicationConfig
        return
    
    def override_with_key_valt(self) -> ApplicationConfig:
        '''
        override all the config values if it's set in key valt
        '''

        '''
        next step: load and override
        '''

        return self.app_config
    
    def override_with_env(self) -> ApplicationConfig:
        '''
        override all the config values if it's set in env variable
        '''
        # Try multiple env file locations
        env_files = [
            Path('.') / '.env.local',
            Path('.') / '.env',
        ]
        
        env_loaded = False
        for env_file in env_files:
            if env_file.exists():
                load_dotenv(dotenv_path=env_file)
                env_loaded = True
                print(f"Loaded environment from: {env_file}")
                break
        
        if not env_loaded:
            # Load from system environment variables (production)
            load_dotenv()
            print("Loading from system environment variables")
        
        '''
        next step: load and override
        https://www.fastapitutorial.com/blog/database-connection-fastapi/
        '''

        return self.app_config
    
    def load_config(self, file_path: FilePath) -> ApplicationConfig:
        '''
        Load application config
        '''
        with open(file_path, "r") as file:
            config_data = yaml.safe_load(file)
        # standandarized app config
        self.app_config = ApplicationConfig(**config_data)
        # over ride config with env
        self.app_config = self.override_with_env()
        # over ride config with key valt
        self.app_config = self.override_with_key_valt()
        return self.app_config
