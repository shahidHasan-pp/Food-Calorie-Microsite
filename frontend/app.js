/**
 * CalorieSnap — app.js
 *
 * Responsibilities:
 *  - Device ID generation / persistence (localStorage)
 *  - Image upload via browse / camera / drag-and-drop
 *  - Sending multipart/form-data to the backend
 *  - Rendering nutrition results with animated macros bar
 *  - Loading step progression animation
 *  - Error handling with friendly messages
 */

"use strict";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */
const API_BASE      = "/api";
const ANALYZE_URL   = `${API_BASE}/analyze-food`;
const DEVICE_KEY    = "caloriesnap_device_id";
const MAX_SIZE_MB   = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED_TYPES  = ["image/jpeg", "image/png", "image/webp"];

/* ------------------------------------------------------------------ */
/* Device ID (Singleton — generated once, stored in localStorage)     */
/* ------------------------------------------------------------------ */
function getOrCreateDeviceId() {
  let id = localStorage.getItem(DEVICE_KEY);
  if (!id) {
    id = generateUUID();
    localStorage.setItem(DEVICE_KEY, id);
  }
  return id;
}

function generateUUID() {
  // RFC 4122 v4 UUID using crypto.randomUUID if available
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/* ------------------------------------------------------------------ */
/* DOM References                                                      */
/* ------------------------------------------------------------------ */
const dropZone         = document.getElementById("drop-zone");
const fileInput        = document.getElementById("file-input");
const cameraInput      = document.getElementById("camera-input");
const btnFile          = document.getElementById("btn-file");
const btnCamera        = document.getElementById("btn-camera");
const btnClear         = document.getElementById("btn-clear");
const btnAnalyze       = document.getElementById("btn-analyze");
const btnAnalyzeAnother= document.getElementById("btn-analyze-another");
const btnTryAgain      = document.getElementById("btn-try-again");
const previewSection   = document.getElementById("preview-section");
const previewImg       = document.getElementById("preview-img");
const fileMeta         = document.getElementById("file-meta");
const loadingSection   = document.getElementById("loading-section");
const resultsSection   = document.getElementById("results-section");
const errorSection     = document.getElementById("error-section");

// Loading steps
const stepEls = [
  document.getElementById("step-1"),
  document.getElementById("step-2"),
  document.getElementById("step-3"),
];

// Results elements
const resultFoodName  = document.getElementById("results-title");
const resultCalories  = document.getElementById("result-calories");
const resultProtein   = document.getElementById("result-protein");
const resultCarbs     = document.getElementById("result-carbs");
const resultFat       = document.getElementById("result-fat");
const resultSugar     = document.getElementById("result-sugar");
const confidenceBadge = document.getElementById("confidence-badge");
const macroBar        = document.getElementById("macro-bar");

// Error elements
const errorTitle   = document.getElementById("error-title");
const errorMessage = document.getElementById("error-message");

/* ------------------------------------------------------------------ */
/* Application State                                                   */
/* ------------------------------------------------------------------ */
let selectedFile = null;
const deviceId   = getOrCreateDeviceId();

/* ------------------------------------------------------------------ */
/* Section Visibility Helpers                                          */
/* ------------------------------------------------------------------ */
function showOnly(sectionId) {
  const all = ["preview-section","loading-section","results-section","error-section"];
  all.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  });
  if (sectionId) {
    const el = document.getElementById(sectionId);
    if (el) el.classList.remove("hidden");
  }
}

function resetToUpload() {
  selectedFile = null;
  fileInput.value = "";
  cameraInput.value = "";
  previewImg.src = "";
  fileMeta.textContent = "";
  dropZone.classList.remove("hidden");
  showOnly(null); // hide all sub-sections
  previewSection.classList.add("hidden");
}

/* ------------------------------------------------------------------ */
/* File Validation                                                     */
/* ------------------------------------------------------------------ */
function validateFile(file) {
  if (!file) return "No file selected.";
  if (!ALLOWED_TYPES.includes(file.type)) {
    return `Unsupported file type. Please upload a JPG, PNG, or WEBP image.`;
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `File is too large (${formatBytes(file.size)}). Maximum size is ${MAX_SIZE_MB}MB.`;
  }
  return null;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/* ------------------------------------------------------------------ */
/* Image Preview                                                        */
/* ------------------------------------------------------------------ */
function showPreview(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewImg.alt = `Preview of ${file.name}`;
  };
  reader.readAsDataURL(file);

  fileMeta.textContent = `${file.name}  ·  ${formatBytes(file.size)}  ·  ${file.type}`;
  previewSection.classList.remove("hidden");
}

/* ------------------------------------------------------------------ */
/* Handle File Selection                                               */
/* ------------------------------------------------------------------ */
function handleFileSelected(file) {
  const error = validateFile(file);
  if (error) {
    showError("Invalid File", error);
    return;
  }
  selectedFile = file;
  showOnly("preview-section");
  previewSection.classList.remove("hidden");
  showPreview(file);
}

/* ------------------------------------------------------------------ */
/* Loading Step Animation                                              */
/* ------------------------------------------------------------------ */
let stepTimers = [];

function startLoadingSteps() {
  // Reset all steps
  stepEls.forEach((el) => {
    el.classList.remove("active", "done");
  });
  stepEls[0].classList.add("active");

  stepTimers.push(
    setTimeout(() => {
      stepEls[0].classList.remove("active");
      stepEls[0].classList.add("done");
      stepEls[1].classList.add("active");
    }, 1200)
  );
  stepTimers.push(
    setTimeout(() => {
      stepEls[1].classList.remove("active");
      stepEls[1].classList.add("done");
      stepEls[2].classList.add("active");
    }, 2800)
  );
}

function stopLoadingSteps() {
  stepTimers.forEach(clearTimeout);
  stepTimers = [];
  stepEls.forEach((el) => el.classList.remove("active", "done"));
}

/* ------------------------------------------------------------------ */
/* Error Display                                                        */
/* ------------------------------------------------------------------ */
function showError(title, message) {
  errorTitle.textContent = title;
  errorMessage.textContent = message;
  showOnly("error-section");
  errorSection.classList.remove("hidden");
}

/* ------------------------------------------------------------------ */
/* Macronutrient Bar                                                    */
/* ------------------------------------------------------------------ */
function renderMacroBar(protein, carbs, fat, sugar) {
  const total = (protein || 0) + (carbs || 0) + (fat || 0) + (sugar || 0);
  if (total === 0) {
    macroBar.innerHTML = "";
    return;
  }

  const segments = [
    { value: protein || 0, color: "#6ee7b7", label: "protein" },
    { value: carbs   || 0, color: "#60a5fa", label: "carbs" },
    { value: fat     || 0, color: "#f59e0b", label: "fat" },
    { value: sugar   || 0, color: "#f472b6", label: "sugar" },
  ];

  macroBar.innerHTML = segments
    .map(({ value, color, label }) => {
      const pct = ((value / total) * 100).toFixed(1);
      return `<div
        class="macro-bar-segment"
        style="width:${pct}%; background:${color};"
        title="${label}: ${value}g (${pct}%)"
        aria-label="${label} ${pct}%"
      ></div>`;
    })
    .join("");
}

/* ------------------------------------------------------------------ */
/* Confidence Badge                                                     */
/* ------------------------------------------------------------------ */
function renderConfidenceBadge(score) {
  if (!score) {
    confidenceBadge.textContent = "";
    confidenceBadge.className = "confidence-badge";
    return;
  }
  let cls, label;
  if (score >= 75) {
    cls = "confidence-high";
    label = `${score}% confident`;
  } else if (score >= 50) {
    cls = "confidence-medium";
    label = `${score}% confident`;
  } else {
    cls = "confidence-low";
    label = `${score}% confident`;
  }
  confidenceBadge.className = `confidence-badge ${cls}`;
  confidenceBadge.textContent = label;
  confidenceBadge.setAttribute("aria-label", `AI confidence: ${label}`);
}

/* ------------------------------------------------------------------ */
/* Animated Number Counter                                             */
/* ------------------------------------------------------------------ */
function animateNumber(element, targetValue, duration = 900) {
  const start = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (targetValue - start) * eased);
    element.textContent = current;
    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.textContent = targetValue;
    }
  }

  requestAnimationFrame(update);
}

/* ------------------------------------------------------------------ */
/* Render Results                                                       */
/* ------------------------------------------------------------------ */
function renderResults(data) {
  resultFoodName.textContent = data.food_name || "Unknown Food";
  resultFoodName.setAttribute("aria-label", `Food: ${data.food_name}`);

  // Animate calories counter
  animateNumber(resultCalories, data.calories || 0);

  // Set macro values
  resultProtein.textContent = data.protein != null ? data.protein : "--";
  resultCarbs.textContent   = data.carbs   != null ? data.carbs   : "--";
  resultFat.textContent     = data.fat     != null ? data.fat     : "--";
  resultSugar.textContent   = data.sugar   != null ? data.sugar   : "--";

  // Confidence
  renderConfidenceBadge(data.confidence_score);

  // Macro bar
  renderMacroBar(data.protein, data.carbs, data.fat, data.sugar);

  // Show results section
  showOnly("results-section");
  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ------------------------------------------------------------------ */
/* API Call                                                             */
/* ------------------------------------------------------------------ */
async function analyzeFood() {
  if (!selectedFile) {
    showError("No Image Selected", "Please upload or take a food photo first.");
    return;
  }

  // Show loading
  showOnly("loading-section");
  loadingSection.classList.remove("hidden");
  dropZone.classList.add("hidden");
  startLoadingSteps();

  const formData = new FormData();
  formData.append("image", selectedFile);
  formData.append("device_id", deviceId);

  try {
    const response = await fetch(ANALYZE_URL, {
      method: "POST",
      body: formData,
    });

    stopLoadingSteps();

    if (!response.ok) {
      let detail = `Server error ${response.status}.`;
      try {
        const errJson = await response.json();
        detail = errJson.detail || detail;
      } catch (_) { /* ignore parse errors */ }
      showError("Analysis Failed", detail);
      return;
    }

    const data = await response.json();

    if (!data.success) {
      showError(
        "No Food Detected",
        data.message || "We could not detect any food in this image. Please try a clearer photo of your meal."
      );
      return;
    }

    renderResults(data);

  } catch (err) {
    stopLoadingSteps();
    console.error("Analysis error:", err);
    showError(
      "Connection Error",
      "Could not reach the server. Please check your connection and try again."
    );
  }
}

/* ------------------------------------------------------------------ */
/* Event Listeners                                                      */
/* ------------------------------------------------------------------ */

// Browse files button
btnFile.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});

// Camera button
btnCamera.addEventListener("click", (e) => {
  e.stopPropagation();
  cameraInput.click();
});

// File input change
fileInput.addEventListener("change", () => {
  if (fileInput.files && fileInput.files[0]) {
    handleFileSelected(fileInput.files[0]);
  }
});

// Camera input change
cameraInput.addEventListener("change", () => {
  if (cameraInput.files && cameraInput.files[0]) {
    handleFileSelected(cameraInput.files[0]);
  }
});

// Drop zone click (open file browser)
dropZone.addEventListener("click", (e) => {
  if (e.target === dropZone || e.target.closest(".drop-zone-icon") || e.target.tagName === "P") {
    fileInput.click();
  }
});

// Keyboard access for drop zone
dropZone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

// Drag and drop
dropZone.addEventListener("dragenter", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", (e) => {
  if (!dropZone.contains(e.relatedTarget)) {
    dropZone.classList.remove("drag-over");
  }
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const files = e.dataTransfer.files;
  if (files && files[0]) {
    handleFileSelected(files[0]);
  }
});

// Clear / remove selected image
btnClear.addEventListener("click", () => {
  resetToUpload();
  dropZone.classList.remove("hidden");
});

// Analyze button
btnAnalyze.addEventListener("click", analyzeFood);

// Analyze another
btnAnalyzeAnother.addEventListener("click", () => {
  resetToUpload();
  dropZone.classList.remove("hidden");
});

// Try again after error
btnTryAgain.addEventListener("click", () => {
  if (selectedFile) {
    // Image is still in memory — show preview again
    showOnly("preview-section");
    previewSection.classList.remove("hidden");
    dropZone.classList.remove("hidden");
  } else {
    resetToUpload();
    dropZone.classList.remove("hidden");
  }
});

/* ------------------------------------------------------------------ */
/* Init                                                                 */
/* ------------------------------------------------------------------ */
(function init() {
  // Pre-flight: ensure device ID created
  getOrCreateDeviceId();
})();
