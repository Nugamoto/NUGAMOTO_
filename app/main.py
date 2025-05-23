from fastapi import FastAPI
from app.api import users

app = FastAPI(title="NUGAMOTO – Smart Kitchen Assistant")

app.include_router(users.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to NUGAMOTO API"}