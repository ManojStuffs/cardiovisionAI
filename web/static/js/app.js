/**
 * CardioVision AI — Clinical Frontend Engine
 * Deep Vision Transformer ECG Diagnostic Platform
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const browseBtn = document.getElementById("browseBtn");
  const dropIdleState = document.getElementById("dropIdleState");
  const dropPreviewState = document.getElementById("dropPreviewState");
  const previewImage = document.getElementById("previewImage");
  const previewFilename = document.getElementById("previewFilename");
  const clearPreviewBtn = document.getElementById("clearPreviewBtn");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const btnLoader = document.getElementById("btnLoader");
  const demoPillsContainer = document.getElementById("demoPillsContainer");
  const secondsInput = document.getElementById("secondsInput");
  const printReportBtn = document.getElementById("printReportBtn");

  // Results elements
  const emptyState = document.getElementById("emptyState");
  const resultsContent = document.getElementById("resultsContent");
  const verdictBanner = document.getElementById("verdictBanner");
  const verdictIcon = document.getElementById("verdictIcon");
  const verdictTitle = document.getElementById("verdictTitle");
  const verdictSubtitle = document.getElementById("verdictSubtitle");
  const urgencyBadge = document.getElementById("urgencyBadge");
  const gaugeProgress = document.getElementById("gaugeProgress");
  const gaugeValue = document.getElementById("gaugeValue");
  const gaugeStatusText = document.getElementById("gaugeStatusText");

  // Clinical Finding Indicators (No Heart Rate)
  const primaryFinding = document.getElementById("primaryFinding");
  const telemConfidence = document.getElementById("telemConfidence");
  const rhythmStability = document.getElementById("rhythmStability");
  const diagnosticUrgency = document.getElementById("diagnosticUrgency");

  const conditionBars = document.getElementById("conditionBars");
  const engineTag = document.getElementById("engineTag");
  const waveformCanvas = document.getElementById("waveformCanvas");

  // State
  let selectedFile = null;
  let selectedSampleName = null;
  let lastAnalysisData = null;

  // Initialize
  initOscilloscope();
  checkSystemStatus();
  fetchSamples();

  // --- Oscilloscope Top Banner Animation ---
  function initOscilloscope() {
    const canvas = document.getElementById("oscilloscopeCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    function resize() {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    }
    window.addEventListener("resize", resize);
    resize();

    let xPos = 0;
    const speed = 2.5;

    // ECG synthetic wave template
    function getEcgY(t) {
      const cycle = t % 1.0;
      if (cycle < 0.1) return 0;
      if (cycle < 0.18) return -6 * Math.sin((cycle - 0.1) / 0.08 * Math.PI); // P wave
      if (cycle < 0.25) return 0;
      if (cycle < 0.28) return 4 * Math.sin((cycle - 0.25) / 0.03 * Math.PI);  // Q drop
      if (cycle < 0.33) return -26 * Math.sin((cycle - 0.28) / 0.05 * Math.PI); // R peak
      if (cycle < 0.38) return 6 * Math.sin((cycle - 0.33) / 0.05 * Math.PI);  // S dip
      if (cycle < 0.50) return 0;
      if (cycle < 0.65) return -8 * Math.sin((cycle - 0.5) / 0.15 * Math.PI);  // T wave
      return 0;
    }

    let lastY = canvas.height / 2;
    let time = 0;

    function animate() {
      const midY = canvas.height / 2;

      // Subtle phosphor fade
      ctx.fillStyle = "rgba(7, 10, 16, 0.08)";
      ctx.fillRect(xPos, 0, 18, canvas.height);

      time += 0.015;
      const targetY = midY + getEcgY(time);

      ctx.beginPath();
      ctx.moveTo(xPos, lastY);
      ctx.lineTo(xPos + speed, targetY);
      ctx.strokeStyle = "#00f0ff";
      ctx.lineWidth = 1.6;
      ctx.shadowBlur = 8;
      ctx.shadowColor = "#00f0ff";
      ctx.stroke();

      lastY = targetY;
      xPos += speed;

      if (xPos >= canvas.width) {
        xPos = 0;
        ctx.clearRect(0, 0, 20, canvas.height);
      }

      requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
  }

  // --- Backend Engine Status Check ---
  async function checkSystemStatus() {
    try {
      const res = await fetch("/api/system-status");
      const data = await res.json();
      const statusText = document.getElementById("engineStatusText");
      if (statusText) {
        statusText.textContent = data.torch_available ? "Neural Core: Active" : "Neural Engine: Ready";
      }
      const modelBadge = document.getElementById("modelBadgeText");
      if (modelBadge) {
        modelBadge.textContent = "Vision Transformer (ViT)";
      }
    } catch (e) {
      console.warn("Status check notice:", e);
    }
  }

  // --- Fetch Preset Reference ECG Samples ---
  async function fetchSamples() {
    try {
      const res = await fetch("/api/samples");
      const samples = await res.json();
      demoPillsContainer.innerHTML = "";

      if (samples.length === 0) {
        demoPillsContainer.innerHTML = `<span style="font-size:0.75rem; color:var(--text-dim);">No reference samples found. Please upload an ECG.</span>`;
        return;
      }

      samples.forEach((sample, idx) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "pill-btn";
        const isAfib = sample.is_afib;
        const tagClass = isAfib ? "tag-afib" : "tag-norm";
        const tagText = isAfib ? "AFIB" : "NORM";

        // Generate friendly clinical title
        const cleanName = sample.filename.replace(/\.png|\.jpg/i, "");
        const parts = cleanName.split("_");
        const caseNumber = parts.length > 1 ? parseInt(parts[1], 10) + 1 : idx + 1;
        const displayLabel = isAfib ? `AFib Case ${caseNumber}` : `Normal Sinus ${caseNumber}`;

        btn.innerHTML = `
          <span class="pill-tag ${tagClass}">${tagText}</span>
          <span>${displayLabel}</span>
        `;

        btn.title = `Load reference ECG: ${sample.filename}`;
        btn.addEventListener("click", () => selectDemoSample(sample, btn, displayLabel));
        demoPillsContainer.appendChild(btn);
      });
    } catch (e) {
      demoPillsContainer.innerHTML = `<span style="color:var(--text-dim); font-size:0.8rem;">Upload your ECG below</span>`;
    }
  }

  function selectDemoSample(sample, buttonEl, displayLabel) {
    document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
    buttonEl.classList.add("active");

    selectedSampleName = sample.filename;
    selectedFile = null;

    // Show preview
    previewImage.src = sample.url;
    previewFilename.textContent = displayLabel || sample.filename;
    dropIdleState.classList.add("hidden");
    dropPreviewState.classList.remove("hidden");
    analyzeBtn.disabled = false;
  }

  // --- File Drop & Picker Handling ---
  browseBtn.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("click", (e) => {
    if (e.target !== clearPreviewBtn && dropPreviewState.classList.contains("hidden")) {
      fileInput.click();
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-active");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-active");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-active");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUserFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleUserFile(e.target.files[0]);
    }
  });

  function handleUserFile(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file (PNG, JPG, or TIFF).");
      return;
    }

    selectedFile = file;
    selectedSampleName = null;
    document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));

    const reader = new FileReader();
    reader.onload = (ev) => {
      previewImage.src = ev.target.result;
      previewFilename.textContent = file.name;
      dropIdleState.classList.add("hidden");
      dropPreviewState.classList.remove("hidden");
      analyzeBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  clearPreviewBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    selectedFile = null;
    selectedSampleName = null;
    fileInput.value = "";
    previewImage.src = "";
    dropPreviewState.classList.add("hidden");
    dropIdleState.classList.remove("hidden");
    analyzeBtn.disabled = true;
    document.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
  });

  // --- Run Diagnostic Analysis Trigger ---
  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile && !selectedSampleName) return;

    // UI Loading state
    analyzeBtn.disabled = true;
    analyzeBtn.querySelector(".btn-text").classList.add("hidden");
    btnLoader.classList.remove("hidden");

    const formData = new FormData();
    formData.append("seconds", secondsInput.value || "10.0");

    if (selectedFile) {
      formData.append("file", selectedFile);
    } else if (selectedSampleName) {
      formData.append("sample_name", selectedSampleName);
    }

    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || "Diagnostic analysis failed.");
      }

      lastAnalysisData = data;
      renderResults(data);
    } catch (err) {
      alert(`Diagnostic Analysis Failed: ${err.message}`);
    } finally {
      analyzeBtn.disabled = false;
      btnLoader.classList.add("hidden");
      analyzeBtn.querySelector(".btn-text").classList.remove("hidden");
    }
  });

  // --- Render Diagnostic Results ---
  function renderResults(data) {
    emptyState.classList.add("hidden");
    resultsContent.classList.remove("hidden");
    printReportBtn.classList.remove("hidden");

    const isAfib = data.is_afib;
    const afibProb = data.afib_percentage;

    // Verdict Banner
    verdictBanner.className = `verdict-banner ${isAfib ? "verdict-afib" : "verdict-normal"}`;
    verdictTitle.textContent = isAfib ? "ATRIAL FIBRILLATION DETECTED" : "NO ATRIAL FIBRILLATION DETECTED";
    verdictSubtitle.textContent = isAfib
      ? `High irregularity in atrial rhythm identified with ${afibProb}% AFib risk index.`
      : `Consistent sinus rhythm morphology and regular baseline electrophysiology observed.`;

    verdictIcon.innerHTML = isAfib
      ? `<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01"/></svg>`
      : `<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3"/></svg>`;

    urgencyBadge.className = `verdict-badge ${isAfib ? "badge-urgent" : "badge-routine"}`;
    urgencyBadge.textContent = isAfib ? "URGENT CLINICAL REVIEW" : "PHYSIOLOGICAL SINUS";

    // Radial Gauge
    const circumference = 2 * Math.PI * 50; // r=50 -> 314.15
    const offset = circumference - (afibProb / 100) * circumference;
    gaugeProgress.style.strokeDashoffset = offset;
    gaugeValue.textContent = `${afibProb}%`;

    if (afibProb >= 70) {
      gaugeProgress.style.stroke = "var(--crimson)";
      gaugeStatusText.textContent = "Severe Arrhythmia Risk";
      gaugeStatusText.style.color = "var(--crimson)";
    } else if (afibProb >= 40) {
      gaugeProgress.style.stroke = "var(--amber)";
      gaugeStatusText.textContent = "Borderline / Elevated";
      gaugeStatusText.style.color = "var(--amber)";
    } else {
      gaugeProgress.style.stroke = "var(--emerald)";
      gaugeStatusText.textContent = "Normal Rhythm Profile";
      gaugeStatusText.style.color = "var(--emerald)";
    }

    // Diagnostic Assessment Items (No Heart Rate)
    const topPred = (data.predictions && data.predictions[0]) ? data.predictions[0] : null;
    if (primaryFinding) {
      primaryFinding.textContent = topPred ? topPred.title : (isAfib ? "Atrial Fibrillation" : "Normal Sinus Rhythm");
    }
    if (telemConfidence) {
      telemConfidence.textContent = `${data.confidence || 0}%`;
    }
    if (rhythmStability) {
      rhythmStability.textContent = isAfib ? "Marked Irregularity" : "Regular Periodic";
    }
    if (diagnosticUrgency) {
      if (isAfib) {
        diagnosticUrgency.textContent = "High Priority";
        diagnosticUrgency.style.color = "var(--crimson)";
      } else {
        diagnosticUrgency.textContent = "Routine Baseline";
        diagnosticUrgency.style.color = "var(--emerald)";
      }
    }

    if (engineTag) {
      engineTag.textContent = "DeepNet Core";
    }

    // Condition Bars
    conditionBars.innerHTML = "";
    (data.predictions || []).forEach(p => {
      const item = document.createElement("div");
      item.className = "condition-item";
      item.innerHTML = `
        <div class="condition-top">
          <span class="condition-name">
            <span class="condition-code">${p.label}</span>
            <span>${p.title}</span>
          </span>
          <span class="condition-pct" style="color: ${p.color};">${p.percentage}%</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: 0%; background-color: ${p.color};"></div>
        </div>
        <div class="condition-desc">${p.description}</div>
      `;
      conditionBars.appendChild(item);

      // Animate bar width
      setTimeout(() => {
        const fill = item.querySelector(".progress-bar-fill");
        if (fill) fill.style.width = `${Math.max(2, p.percentage)}%`;
      }, 50);
    });

    // Waveform rendering
    const telem = data.telemetry || {};
    if (telem.waveform_preview && telem.waveform_preview.values && telem.waveform_preview.values.length > 0) {
      drawWaveform(telem.waveform_preview);
    }
  }

  // --- Draw Digitized Waveform on Canvas ---
  function drawWaveform(preview) {
    const canvas = waveformCanvas;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const container = canvas.parentElement;

    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    const W = canvas.width;
    const H = canvas.height;
    const values = preview.values || [];
    const peakTimes = preview.peak_indices || [];

    if (values.length < 2) return;

    // Draw clinical ECG grid background
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(0, 240, 255, 0.04)";
    ctx.lineWidth = 1;

    // Minor grid
    const gridStep = 18;
    for (let x = 0; x < W; x += gridStep) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let y = 0; y < H; y += gridStep) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    // Baseline axis
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.beginPath();
    ctx.moveTo(0, H / 2);
    ctx.lineTo(W, H / 2);
    ctx.stroke();

    // Scale values to canvas height
    let minVal = Infinity;
    let maxVal = -Infinity;
    values.forEach(v => {
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    });

    const range = (maxVal - minVal) || 1;
    const pad = 24;
    const scaleY = (H - 2 * pad) / range;

    function toCanvasY(val) {
      return H - pad - (val - minVal) * scaleY;
    }

    // Draw main ECG lead trace
    ctx.beginPath();
    const xStep = W / (values.length - 1);
    ctx.moveTo(0, toCanvasY(values[0]));

    for (let i = 1; i < values.length; i++) {
      ctx.lineTo(i * xStep, toCanvasY(values[i]));
    }

    ctx.strokeStyle = "#00f0ff";
    ctx.lineWidth = 2;
    ctx.shadowBlur = 10;
    ctx.shadowColor = "rgba(0, 240, 255, 0.4)";
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Peak markers
    if (preview.times && preview.times.length === values.length && peakTimes.length > 0) {
      const maxTime = preview.times[preview.times.length - 1] || 1;
      ctx.fillStyle = "#ff3366";
      ctx.shadowBlur = 8;
      ctx.shadowColor = "#ff3366";

      peakTimes.forEach(pt => {
        const px = (pt / maxTime) * W;
        // Interpolate Y
        const sampleIdx = Math.min(values.length - 1, Math.max(0, Math.round((pt / maxTime) * (values.length - 1))));
        const py = toCanvasY(values[sampleIdx]);

        ctx.beginPath();
        ctx.arc(px, py, 4, 0, 2 * Math.PI);
        ctx.fill();
      });
      ctx.shadowBlur = 0;
    }
  }

  // --- Print / Export Report ---
  printReportBtn.addEventListener("click", () => {
    window.print();
  });
});
