import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from typing import Any, Dict

import yaml
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.routes.patterns.reflection import router as agents_router


def load_env_file():
    # Try to find and load the default .env file first
    if any(key in os.environ for key in ['OPENAI_API_KEY', 'AZURE_OPENAI_API_KEY']):
        logging.info("Environment variables already set, skipping .env file loading.")
        return
    env_path = find_dotenv()
    if env_path != "":
        load_dotenv(dotenv_path=env_path, override=True)
        logging.info(f"Loaded environment variables from {env_path}")
    else:
        # If the default .env file is not found, try to find and load .env.azure
        env_azure_path = find_dotenv(".env.azure")
        if env_azure_path:
            load_dotenv(dotenv_path=env_azure_path, override=True)
            logging.info(f"Loaded environment variables from {env_azure_path}")
        else:
            logging.error("Neither .env nor .env.azure files were found")
            raise FileNotFoundError("Neither .env nor .env.azure files were found")


def get_text_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=0,
        length_function=len,
        is_separator_regex=False,
        separators=[
            "\n\n",
            "\n",
        ],
    )


class YAMLContent(BaseModel):
    original_content: str
    parsed_content: Dict[str, Any]

    @field_validator('parsed_content', mode='before')
    def parse_yaml(cls, v, values):
        try:
            return yaml.safe_load(values['original_content'])
        except yaml.YAMLError as e:
            logging.error(f"Failed to parse YAML content: {str(e)}")
            raise ValueError(f"Invalid YAML content: {str(e)}")


@asynccontextmanager
async def lifespan(fast_app: FastAPI):
    try:
        # load_env_file()
        # add_joke_agent_route(fast_app)
        # add_cascade_agent_route(fast_app)
        routes = [route.path for route in fast_app.router.routes]
        logging.info(f"Available routes: {routes}")

        fast_app.state.app_state = AppState()
        fast_app.state.app_state.text_splitter = get_text_splitter()

        logging.info("App state initialized successfully")
        yield
    except Exception as e:
        logging.error(f"Error during app initialization: {str(e)}")
        raise
    finally:
        logging.info("App shutdown")


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Determine the absolute path to the 'static' directory
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
static_directory = os.path.join(current_dir, '..', 'static')


# Serve the static files


def add_handlers(app: FastAPI):
    @app.get("/", response_class=FileResponse)
    async def read_root():
        return os.path.join(static_directory, "index.html")


def create_app():
    app = FastAPI(lifespan=lifespan, title="Agentic DB API", description="API for managing Agentic DB",
                  version="0.1.0")

    # Set all CORS enabled origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=static_directory), name="static")
    add_handlers(app)
    app.include_router(ratings_router)
    app.include_router(agents_router)
    app.include_router(applications_router)
    app.include_router(database_router)

    return app


if __name__ == "__main__":
    app = create_app()
    logging.info("Starting Langgraph Server API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
    logging.info("Application shutdown")
