from fastapi import FastAPI

app = FastAPI()


@app.get("/api/v1/users/")
async def root():
    return {"data": []}
