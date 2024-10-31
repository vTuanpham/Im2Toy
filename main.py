from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import ConfigHandler
from app.api.routes import ImageTransformRouter

# Initialize configuration
config = ConfigHandler()
app = FastAPI(**config.get_api_config())

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for client-side assets
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "app" / "static"),
    name="static",
)

# Include routes from routes.py
image_transform = ImageTransformRouter()
app.include_router(image_transform.router)

if __name__ == "__main__":
    import uvicorn

    host = config.get_api_config()["host"]
    port = config.get_api_config()["port"]

    uvicorn.run(f"{Path(__file__).stem}:app", host=host, port=port, reload=True)
