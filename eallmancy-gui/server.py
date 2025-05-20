# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Serve React static files
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_react():
    with open("frontend/build/index.html") as f:
        return f.read()

@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI"}

@app.get("/api/echo")
def echo(msg: str):
    return {"echo": msg}
