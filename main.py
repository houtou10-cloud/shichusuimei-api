from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="Shichusuimei API", version="0.1.0")
app.include_router(router)

@app.get("/")
def root():
    return {"status":"ok","message":"Shichusuimei API is running."}
