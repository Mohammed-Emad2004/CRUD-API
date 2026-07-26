from fastapi import FastAPI

app = FastAPI(title="Task API", version="1.0")


@app.get("/", summary="API information")
async def root() -> dict:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok"}
