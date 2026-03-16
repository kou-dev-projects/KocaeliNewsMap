from fastapi import FastAPI

app = FastAPI(title="Kocaeli News Map API")

@app.get("/")
def root():
    return {"message": "API is running"}