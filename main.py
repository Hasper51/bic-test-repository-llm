from app.routes import app_openrouter


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app_openrouter", host="0.0.0.0", port=8000, reload=True)
