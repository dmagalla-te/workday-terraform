import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field


# Cargar las variables de entorno desde el archivo .env
load_dotenv()


class Config(BaseModel):

    API_TOKEN: str = Field(default=os.getenv("API_TOKEN", "TOKEN MISSING"))

    #API OAUTH
    org_name: str = Field(default=os.getenv("ORG_NAME", ""))
    headers: dict = Field(default={'Content-Type': 'application/json', 'Authorization': f'Bearer {os.getenv("API_TOKEN", "TOKEN MISSING")}'})
    terraform_project_path: str = Field(default=os.getenv("TERRAFORM_PROJECT_PATH", ""))
    te_tf_version:str = Field(default=os.getenv("TE_TF_VERSION",""))


config = Config()