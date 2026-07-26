from fastapi import FastAPI

app = FastAPI(title="Task API", version="1.0")


@app.get("/")
async def hello() -> dict:
    return {"message": "Hello, server!"}
