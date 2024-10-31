class ImageTransformer {
  constructor() {
    this.video = document.getElementById("video");
    this.canvas = document.getElementById("canvas");
    this.context = this.canvas?.getContext("2d");
    this.currentStream = null;
    this.fileInput = document.getElementById("fileInput");
    this.inputImage = document.getElementById("inputImage");
    this.resultImage = document.getElementById("resultImage");
    this.description = document.getElementById("description");
    this.toy_description = document.getElementById("toy_description");
    this.main_object = document.getElementById("main_object");
    this.detected_objects = document.getElementById("detected_objects");
    this.error = document.getElementById("error");

    if (!this.canvas || !this.context) {
      console.error("Required elements not found");
      return;
    }

    this.initializeEventListeners();
  }

  initializeEventListeners() {
    // File input change handler
    this.fileInput?.addEventListener("change", () => {
      const file = this.fileInput.files[0];
      if (file) this.validateAndPreviewFile(file);
    });
  }

  showLoading() {
    const overlay = document.getElementById("loadingOverlay");
    const spinner = document.getElementById("loadingSpinner");
    const checkmark = document.getElementById("successCheckmark");
    const progressBar = document.getElementById("progressBar");

    overlay.style.display = "flex";
    spinner.style.display = "block";
    checkmark.style.display = "none";
    progressBar.style.width = "0%";

    const phases = [
      "Initializing...",
      "Analyzing image...",
      "Applying transformations...",
      "Generating result...",
    ];

    let currentPhase = 0;
    const phaseElement = document.getElementById("loadingPhase");

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

  hideLoading(phaseInterval, success = true) {
    const overlay = document.getElementById("loadingOverlay");
    const spinner = document.getElementById("loadingSpinner");
    const checkmark = document.getElementById("successCheckmark");
    const progressBar = document.getElementById("progressBar");

    clearInterval(phaseInterval);

    if (success) {
      spinner.style.display = "none";
      checkmark.style.display = "block";
      progressBar.style.width = "100%";
      document.getElementById("loadingPhase").textContent = "Complete!";

      setTimeout(() => {
        overlay.style.display = "none";
      }, 1000);
    } else {
      overlay.style.display = "none";
    }
  }

  async startCamera(facingMode = "user") {
    if (!navigator.mediaDevices?.getUserMedia) {
      this.showError("Camera access is not supported in this browser");
      return;
    }

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

        // Create a DataTransfer object to set the files property
        const dataTransfer = new DataTransfer();
        const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
        dataTransfer.items.add(file);

        // Assign the DataTransfer's files to the file input
        this.fileInput.files = dataTransfer.files;

        // Dispatch change event to trigger the event listener
        const event = new Event("change", { bubbles: true });
        this.fileInput.dispatchEvent(event);
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
      // this.resultImage.src = e.target.result;
      // this.resultImage.classList.remove("hidden");
      this.inputImage.src = e.target.result;
      this.inputImage.classList.remove("hidden");
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
    const phaseInterval = this.showLoading();
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
        this.toy_description.textContent = result.toy_description;
        this.main_object.textContent = "Main object: " + result.main_object;

        // Convert list of detected objects to a string
        const detected_objects = result.detected_objects.join(", ");
        this.detected_objects.textContent =
          "Detected objects: " + detected_objects;

        this.resultImage.scrollIntoView({ behavior: "smooth" });
        this.showToast("Image transformed successfully!");
        this.hideLoading(phaseInterval, true);
      } else {
        throw new Error(result.error || "Unknown error occurred");
      }
    } catch (err) {
      this.showError(`Error: ${err.message}`);
      this.hideLoading(phaseInterval, false);
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
  // Cleanup on page unload
  window.addEventListener("beforeunload", () => {
    window.imageTransformer.stopCamera();
  });
});

// Expose methods for HTML onclick handlers
window.startCamera = (facingMode) =>
  window.imageTransformer.startCamera(facingMode);
window.stopCamera = () => window.imageTransformer.stopCamera();
window.capturePhoto = () => window.imageTransformer.capturePhoto();
window.uploadFile = () => window.imageTransformer.uploadFile();
