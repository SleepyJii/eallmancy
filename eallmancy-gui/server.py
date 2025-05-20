# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from api.config_page import router as api_config_router  # import your router



app = FastAPI()
app.include_router(api_config_router)  # register it


# Serve React static files
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_react_catchall(full_path: str):
    with open("frontend/build/index.html") as f:
        return f.read()



# @app.get("/api/hello")
# def hello():
#     return {"message": "Hello from FastAPI"}

# @app.get("/api/echo")
# def echo(msg: str):
#     return {"echo": msg}
