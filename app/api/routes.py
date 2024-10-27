from fastapi import APIRouter, File, UploadFile
from fastapi.responses import HTMLResponse
from google.generativeai.files import logging
from ..services.image_processor import ImageProcessor
from ..core.config import ConfigHandler
from ..api.models import TransformResponse

# Initialize APIRouter
router = APIRouter()

# Initialize services
config = ConfigHandler()
processor = ImageProcessor(config)


@router.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Image Transformation App</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f0f2f5;
            }
            .container {
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #1a73e8;
                text-align: center;
            }
            .upload-section {
                margin: 20px 0;
                padding: 20px;
                border: 2px dashed #ccc;
                border-radius: 5px;
                text-align: center;
            }
            .camera-section {
                margin: 20px 0;
                text-align: center;
            }
            #video {
                width: 100%;
                max-width: 400px;
                margin: 10px 0;
                border-radius: 5px;
            }
            #canvas {
                display: none;
            }
            .button {
                background-color: #1a73e8;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin: 5px;
                font-size: 16px;
            }
            .button:hover {
                background-color: #1557b0;
            }
            #result {
                margin-top: 20px;
                text-align: center;
            }
            #resultImage {
                max-width: 100%;
                border-radius: 5px;
                margin-top: 10px;
            }
            .error {
                color: red;
                margin: 10px 0;
            }
            .loading-overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                z-index: 1000;
                justify-content: center;
                align-items: center;
                flex-direction: column;
            }
            .loading-spinner {
                width: 50px;
                height: 50px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid #1a73e8;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            .loading-text {
                color: white;
                margin-top: 20px;
                font-size: 18px;
                text-align: center;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .progress-bar-container {
                width: 200px;
                height: 6px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                margin-top: 15px;
            }
            .progress-bar {
                width: 0%;
                height: 100%;
                background: #1a73e8;
                border-radius: 3px;
                transition: width 0.3s ease;
            }
            .success-checkmark {
                display: none;
                color: #34a853;
                font-size: 48px;
                margin-bottom: 15px;
            }
            .loading-phases {
                color: white;
                margin-top: 10px;
                font-size: 14px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="loading-overlay" id="loadingOverlay">
            <div class="success-checkmark" id="successCheckmark">✓</div>
            <div class="loading-spinner" id="loadingSpinner"></div>
            <div class="loading-text">Transforming your image...</div>
            <div class="progress-bar-container">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="loading-phases" id="loadingPhase">Initializing...</div>
        </div>

        <div class="container">
            <h1>🎨 Image Transformation App</h1>
            
            <div class="upload-section">
                <h2>Upload Image</h2>
                <input type="file" id="fileInput" accept="image/*">
                <button class="button" onclick="uploadFile()">Transform Uploaded Image</button>
            </div>

            <div class="camera-section">
                <h2>Take Photo</h2>
                <video id="video" autoplay playsinline></video>
                <canvas id="canvas"></canvas>
                <div>
                    <button class="button" onclick="startCamera()">Start Camera</button>
                    <button class="button" onclick="capturePhoto()">Take Photo</button>
                </div>
            </div>

            <div id="result">
                <h2>Result</h2>
                <img id="resultImage" style="display: none;">
                <p id="description"></p>
                <p class="error" id="error"></p>
            </div>
        </div>

        <script>
            let video = document.getElementById('video');
            let canvas = document.getElementById('canvas');
            let context = canvas.getContext('2d');

            async function startCamera() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                    video.srcObject = stream;
                } catch (err) {
                    document.getElementById('error').textContent = 'Error accessing camera: ' + err.message;
                }
            }

            async function capturePhoto() {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                canvas.toBlob(async (blob) => {
                    const formData = new FormData();
                    formData.append('file', blob, 'capture.jpg');
                    await uploadImage(formData);
                }, 'image/jpeg');
            }

            async function uploadFile() {
                const fileInput = document.getElementById('fileInput');
                if (fileInput.files.length > 0) {
                    const formData = new FormData();
                    formData.append('file', fileInput.files[0]);
                    await uploadImage(formData);
                } else {
                    document.getElementById('error').textContent = 'Please select a file first';
                }
            }

            function showLoading() {
                const overlay = document.getElementById('loadingOverlay');
                const spinner = document.getElementById('loadingSpinner');
                const checkmark = document.getElementById('successCheckmark');
                const progressBar = document.getElementById('progressBar');
                
                overlay.style.display = 'flex';
                spinner.style.display = 'block';
                checkmark.style.display = 'none';
                progressBar.style.width = '0%';
                
                const phases = [
                    'Initializing...',
                    'Analyzing image...',
                    'Applying transformations...',
                    'Generating result...'
                ];
                
                let currentPhase = 0;
                const phaseElement = document.getElementById('loadingPhase');
                
                const phaseInterval = setInterval(() => {
                    if (currentPhase < phases.length) {
                        phaseElement.textContent = phases[currentPhase];
                        const progress = (currentPhase + 1) * (100 / phases.length);
                        progressBar.style.width = `${progress}%`;
                        currentPhase++;
                    } else {
                        clearInterval(phaseInterval);
                    }
                }, 1000);

                return phaseInterval;
            }

            function hideLoading(phaseInterval, success = true) {
                const overlay = document.getElementById('loadingOverlay');
                const spinner = document.getElementById('loadingSpinner');
                const checkmark = document.getElementById('successCheckmark');
                const progressBar = document.getElementById('progressBar');
                
                clearInterval(phaseInterval);
                
                if (success) {
                    spinner.style.display = 'none';
                    checkmark.style.display = 'block';
                    progressBar.style.width = '100%';
                    document.getElementById('loadingPhase').textContent = 'Complete!';
                    
                    setTimeout(() => {
                        overlay.style.display = 'none';
                    }, 1000);
                } else {
                    overlay.style.display = 'none';
                }
            }

            async function uploadImage(formData) {
                const phaseInterval = showLoading();
                
                try {
                    document.getElementById('error').textContent = '';
                    const response = await fetch('/transform', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        const resultImage = document.getElementById('resultImage');
                        resultImage.src = 'data:image/jpeg;base64,' + result.image_bytes;
                        resultImage.style.display = 'block';
                        document.getElementById('description').textContent = result.description;
                        hideLoading(phaseInterval, true);
                    } else {
                        document.getElementById('error').textContent = result.error;
                        hideLoading(phaseInterval, false);
                    }
                } catch (err) {
                    document.getElementById('error').textContent = 'Error processing image: ' + err.message;
                    hideLoading(phaseInterval, false);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/transform", response_model=TransformResponse)
async def transform_image(file: UploadFile = File(...)):
    """Transform an image into a toy-like character."""
    try:
        result = await processor.process_image(file)
        logging.log(logging.INFO, "Image transformation completed")
        return TransformResponse(
            success=True,
            image_bytes=result["image_bytes"],
            image_url=result["image_url"],
            description=result["description"],
        )
    except Exception as e:
        return TransformResponse(success=False, error=str(e))
