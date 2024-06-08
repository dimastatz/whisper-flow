""" fast api declaration """

from fastapi import FastAPI


app = FastAPI()


@app.get("/health", response_model=bool)
def health():
    """health function on API"""
    return True
