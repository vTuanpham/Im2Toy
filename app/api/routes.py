import os
import time
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import aiofiles
from datetime import datetime

from ..core.logging import setup_logging
from ..services.image_processor import ImageProcessor
from ..core.config import ConfigHandler
from ..api.models import TransformResponse


# Set up logging with more detailed configuration
logger = setup_logging()


class ImageTransformRouter:
    def __init__(self):
        self.router = APIRouter()
        self.config = ConfigHandler()
        self.processor = ImageProcessor(self.config)
        self.templates = Jinja2Templates(
            directory=Path(__file__).parent.parent / "templates"
        )

        # Setup routes
        self._setup_routes()

        self.upload_dir = Path(self.config.get_storage_config()["upload_dir"])
        self.upload_dir.mkdir(exist_ok=True)

        self.output_dir = Path(self.config.get_storage_config()["output_dir"])
        self.output_dir.mkdir(exist_ok=True)

        self.log_dir = Path(self.config.get_storage_config()["log_dir"])
        self.log_dir.mkdir(exist_ok=True)

        self.MAX_FILE_SIZE = self.config.get_storage_config().get(
            "max_file_size", 10 * 1024 * 1024
        )

        self.max_upload_storage = self.config.get_storage_config().get(
            "max_upload_storage", 30
        )

    def _setup_routes(self):
        """Initialize all routes"""
        self.router.get("/")(self.index)
        self.router.get("/logs")(self.get_logs)
        self.router.get("/gallery")(self.get_gallery)
        self.router.get("/images/{file_path:path}")(self.get_image)
        self.router.post("/transform")(self.transform_image)
        self.router.get("/health")(self.health_check)

    async def save_upload_file(self, upload_file: UploadFile) -> Path:
        # Limit number of files in upload directory by deleting the oldest file
        files = list(self.upload_dir.iterdir())
        if len(files) > self.max_upload_storage:
            oldest_file = min(files, key=lambda p: p.stat().st_ctime)
            logger.log(logging.INFO, f"Deleting oldest file: {oldest_file}")
            oldest_file.unlink()

        file_path = self.upload_dir / os.path.basename(upload_file.filename)

        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await upload_file.read(1024):  # Read in chunks
                await out_file.write(content)

        # Reset file pointer to beginning
        await upload_file.seek(0)

        return file_path

    async def index(self, request: Request):
        """Render main page"""
        today = time.strftime("%Y-%m-%d")
        return self.templates.TemplateResponse(
            "index.html",
            {"request": request, "title": "Image Transformation App", "now": today},
        )

    async def get_logs(self, request: Request):
        """Display application logs with filtering and pagination"""
        try:
            page = int(request.query_params.get("page", 1))
            level = request.query_params.get("level", "ALL")

            log_path = self.log_dir / "toy_transformer.log"

            if not log_path.exists():
                raise HTTPException(status_code=404, detail="Log file not found")

            # Read logs with pagination
            LOGS_PER_PAGE = 100
            all_logs = log_path.read_text().splitlines()

            # Clean up logs if exceeding maximum number of lines
            if len(all_logs) > 3000:
                all_logs = all_logs[-3000:]

            # Filter logs by level if specified
            if level != "ALL":
                all_logs = [log for log in all_logs if level in log]

            # Sort logs in reverse order (most recent first)
            all_logs.reverse()

            # Calculate pagination
            total_pages = (len(all_logs) + LOGS_PER_PAGE - 1) // LOGS_PER_PAGE
            start_idx = (page - 1) * LOGS_PER_PAGE
            end_idx = start_idx + LOGS_PER_PAGE

            logs_to_show = all_logs[start_idx:end_idx]

            return self.templates.TemplateResponse(
                "logs.html",
                {
                    "request": request,
                    "logs": logs_to_show,
                    "current_page": page,
                    "total_pages": total_pages,
                    "level": level,
                },
            )
        except Exception as e:
            logger.log(logging.ERROR, f"Error accessing logs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_gallery(self, request: Request):
        """Display a gallery of uploaded and transformed images side-by-side."""
        try:
            upload_path = self.upload_dir
            output_path = self.output_dir

            gallery_items = []
            for upload_file in upload_path.iterdir():
                if upload_file.is_file() and upload_file.suffix.lower() in (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                ):
                    output_file = output_path / upload_file.name
                    upload_file = upload_path / output_file.name
                    if output_file.exists() and upload_file.exists():
                        gallery_items.append(
                            {
                                "upload_path": str(upload_file),
                                "output_path": str(output_file),
                            }
                        )

            return self.templates.TemplateResponse(
                "gallery.html", {"request": request, "gallery_items": gallery_items}
            )

        except Exception as e:
            logger.log(logging.ERROR, f"Error accessing gallery: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_image(self, file_path: str):
        if Path(file_path).exists():
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="Image not found")

    async def transform_image(self, file: UploadFile = File(...)):
        """Transform an uploaded image with comprehensive error handling"""

        logger.log(logging.INFO, f"Received file: {file}")

        try:
            # Validate file size
            if file.size > self.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413, detail="File too large. Maximum size is 10MB"
                )

            # Validate file type
            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=415, detail="Uploaded file must be an image"
                )

            # Save file
            file_path = await self.save_upload_file(file)

            # Process image
            try:
                result = await self.processor.process_image(file)

                logger.log(
                    logging.INFO,
                    f"Successfully transformed image: {file.filename}",
                )

                return TransformResponse(
                    success=True,
                    image_bytes=result["image_bytes"],
                    image_url=result["image_url"],
                    description=result["description"],
                    toy_description=result["toy_description"],
                    main_object=result["main_object"],
                    detected_objects=result["detected_objects"],
                )

            except Exception as process_error:
                logger.log(
                    logging.ERROR,
                    f"Error processing image: {str(process_error)}",
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing image: {str(process_error)}",
                )

        except HTTPException:
            raise  # Re-raise HTTPException to return the error to the client
        except Exception as e:
            logger.log(logging.ERROR, f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def health_check(self):
        """API health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
