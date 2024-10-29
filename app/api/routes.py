import time
from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
import aiofiles
import uuid
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
        self.templates = Jinja2Templates(directory="app/templates")

        # Setup routes
        self._setup_routes()

        # Create upload directory if it doesn't exist
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

        # Maximum file size (10MB)
        self.MAX_FILE_SIZE = 10 * 1024 * 1024

    def _setup_routes(self):
        """Initialize all routes"""
        self.router.get("/")(self.index)
        self.router.get("/logs")(self.get_logs)
        self.router.post("/transform")(self.transform_image)
        self.router.get("/health")(self.health_check)

    async def save_upload_file(self, upload_file: UploadFile) -> Path:
        """Save uploaded file with secure filename"""
        file_extension = Path(upload_file.filename).suffix
        secure_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = self.upload_dir / secure_filename

        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await upload_file.read(1024):  # Read in chunks
                await out_file.write(content)

        # Reset file pointer to beginning
        await upload_file.seek(0)

        return file_path

    async def index(self, request: Request):
        """Render main page"""
        time = datetime.utcnow().isoformat().split(".")[0]
        return self.templates.TemplateResponse(
            "index.html",
            {"request": request, "title": "Image Transformation App", "now": time},
        )

    async def get_logs(self, request: Request):
        """Display application logs with filtering and pagination"""
        try:
            page = int(request.query_params.get("page", 1))
            level = request.query_params.get("level", "ALL")

            log_path = Path("logs/toy_transformer.log")
            if not log_path.exists():
                raise HTTPException(status_code=404, detail="Log file not found")

            # Read logs with pagination
            LOGS_PER_PAGE = 50
            all_logs = log_path.read_text().splitlines()

            # Filter logs by level if specified
            if level != "ALL":
                all_logs = [log for log in all_logs if level in log]

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
            logger.error(f"Error accessing logs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def transform_image(self, file: UploadFile = File(...)):
        """Transform an uploaded image with comprehensive error handling"""

        logger.info(f"Received file: {file}")

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

                # Clean up uploaded file
                file_path.unlink()

                logger.info(
                    f"Successfully transformed image: {file.filename}",
                    # extra={"filename": file.filename},
                )

                return TransformResponse(
                    success=True,
                    image_bytes=result["image_bytes"],
                    image_url=result["image_url"],
                    description=result["description"],
                )

            except Exception as process_error:
                logger.error(
                    f"Error processing image: {str(process_error)}",
                    # extra={"filename": file.filename},
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing image: {str(process_error)}",
                )

        except HTTPException:
            raise  # Re-raise HTTPException to return the error to the client
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def health_check(self):
        """API health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
