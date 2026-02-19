import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        #host="0.0.0.0",
        #port=3606,
        reload=True  # cambiar a False en producción
    )
