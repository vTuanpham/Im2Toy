class ImageTransformer {
  constructor() {
    this.video = document.getElementById("video");
    this.canvas = document.getElementById("canvas");
    this.context = this.canvas?.getContext("2d");
    this.currentStream = null;
    this.fileInput = document.getElementById("fileInput");
    this.resultImage = document.getElementById("resultImage");
    this.description = document.getElementById("description");
    this.error = document.getElementById("error");
    this.loadingOverlay = document.getElementById("loadingOverlay");

    this.initializeEventListeners();
  }

  initializeEventListeners() {
    // File input change handler
    this.fileInput?.addEventListener("change", () => {
      const file = this.fileInput.files[0];
      if (file) this.validateAndPreviewFile(file);
    });
  }

  async startCamera(facingMode = "user") {
    try {
      this.stopCamera();

      const constraints = {
        video: { facingMode: { exact: facingMode } },
      };

      this.currentStream =
        await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = this.currentStream;
      this.video.classList.remove("hidden");
    } catch (err) {
      if (err.name === "OverconstrainedError") {
        try {
          const constraints = {
            video: { facingMode: facingMode },
          };
          this.currentStream =
            await navigator.mediaDevices.getUserMedia(constraints);
          this.video.srcObject = this.currentStream;
          this.video.classList.remove("hidden");
        } catch (fallbackErr) {
          this.showError("Camera not available: " + fallbackErr.message);
        }
      } else {
        this.showError("Error accessing camera: " + err.message);
      }
    }
  }

  stopCamera() {
    if (this.currentStream) {
      this.currentStream.getTracks().forEach((track) => track.stop());
      this.video.classList.add("hidden");
    }
  }

  async capturePhoto() {
    if (!this.currentStream) {
      this.showError("Camera is not active");
      return;
    }

    this.canvas.width = this.video.videoWidth;
    this.canvas.height = this.video.videoHeight;
    this.context.drawImage(
      this.video,
      0,
      0,
      this.canvas.width,
      this.canvas.height,
    );

    this.canvas.toBlob(
      async (blob) => {
        const formData = new FormData();
        formData.append("file", blob, "capture.jpg");
        await this.uploadImage(formData);
      },
      "image/jpeg",
      0.9,
    );
  }

  validateAndPreviewFile(file) {
    if (!file.type.startsWith("image/")) {
      this.showError("Please select an image file");
      return false;
    }

    if (file.size > 10 * 1024 * 1024) {
      this.showError("File size must be less than 10MB");
      return false;
    }

    // Preview image
    const reader = new FileReader();
    reader.onload = (e) => {
      this.resultImage.src = e.target.result;
      this.resultImage.classList.remove("hidden");
    };
    reader.readAsDataURL(file);

    return true;
  }

  async uploadFile() {
    const file = this.fileInput.files[0];

    if (!file) {
      this.showError("Please select a file");
      return;
    }

    if (!this.validateAndPreviewFile(file)) {
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    await this.uploadImage(formData);
  }

  async uploadImage(formData) {
    this.loadingOverlay.style.display = "flex";
    this.error.textContent = "";

    try {
      const response = await fetch("/transform", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Error processing image");
      }

      if (result.success) {
        this.resultImage.src = "data:image/jpeg;base64," + result.image_bytes;
        this.resultImage.classList.remove("hidden");
        this.description.textContent = result.description;
        this.resultImage.scrollIntoView({ behavior: "smooth" });
        this.showToast("Image transformed successfully!");
      } else {
        throw new Error(result.error || "Unknown error occurred");
      }
    } catch (err) {
      this.showError(`Error: ${err.message}`);
    } finally {
      this.loadingOverlay.style.display = "none";
    }
  }

  showError(message) {
    this.error.textContent = message;
    this.error.scrollIntoView({ behavior: "smooth" });
  }

  showToast(message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Trigger reflow
    toast.offsetHeight;

    toast.classList.add("show");

    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
}

// Initialize the application
document.addEventListener("DOMContentLoaded", () => {
  window.imageTransformer = new ImageTransformer();
});

// Expose methods for HTML onclick handlers
window.startCamera = (facingMode) =>
  window.imageTransformer.startCamera(facingMode);
window.stopCamera = () => window.imageTransformer.stopCamera();
window.capturePhoto = () => window.imageTransformer.capturePhoto();
window.uploadFile = () => window.imageTransformer.uploadFile();
