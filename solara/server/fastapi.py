from fastapi import FastAPI

from . import starlette

app = FastAPI(routes=starlette.routes)
