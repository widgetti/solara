from fastapi import FastAPI

from . import starlette

# reuse the middleware stack of the starlette app (gzip, and the session
# middleware when auth is configured), so both entrypoints behave the same
app = FastAPI(routes=starlette.routes, middleware=starlette.middleware)
