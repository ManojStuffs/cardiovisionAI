import React, { useEffect, useRef } from 'react';
import type { WaveformPreview } from '../types';

interface WaveformCanvasProps {
  waveform: WaveformPreview;
}

export const WaveformCanvas: React.FC<WaveformCanvasProps> = ({ waveform }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const container = canvas.parentElement;
    if (container) {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight || 170;
    }

    const W = canvas.width;
    const H = canvas.height;
    const values = waveform.values || [];
    const peakTimes = waveform.peak_indices || [];

    if (values.length < 2) return;

    // Draw standard clinical ECG calibrated paper background
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#fffdfa';
    ctx.fillRect(0, 0, W, H);

    // Minor grid (1 mm equivalent)
    ctx.strokeStyle = '#fee2e2';
    ctx.lineWidth = 0.6;
    const minorStep = 5;
    for (let x = 0; x < W; x += minorStep) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let y = 0; y < H; y += minorStep) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    // Major grid (5 mm equivalent)
    ctx.strokeStyle = '#fca5a5';
    ctx.lineWidth = 1.0;
    const majorStep = 25;
    for (let x = 0; x < W; x += majorStep) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let y = 0; y < H; y += majorStep) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    // Baseline axis
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, H / 2);
    ctx.lineTo(W, H / 2);
    ctx.stroke();

    // Scale values to canvas height
    let minVal = Infinity;
    let maxVal = -Infinity;
    values.forEach((v) => {
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    });

    const range = maxVal - minVal || 1;
    const pad = 24;
    const scaleY = (H - 2 * pad) / range;

    const toCanvasY = (val: number) => {
      return H - pad - (val - minVal) * scaleY;
    };

    // Draw main ECG trace line (clean clinical ink, no glowing neon shadow)
    ctx.beginPath();
    const xStep = W / (values.length - 1);
    ctx.moveTo(0, toCanvasY(values[0]));

    for (let i = 1; i < values.length; i++) {
      ctx.lineTo(i * xStep, toCanvasY(values[i]));
    }

    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1.8;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Peak markers (solid clinical red dots)
    if (waveform.times && waveform.times.length === values.length && peakTimes.length > 0) {
      const maxTime = waveform.times[waveform.times.length - 1] || 1;
      ctx.fillStyle = '#dc2626';

      peakTimes.forEach((pt) => {
        const px = (pt / maxTime) * W;
        const sampleIdx = Math.min(
          values.length - 1,
          Math.max(0, Math.round((pt / maxTime) * (values.length - 1)))
        );
        const py = toCanvasY(values[sampleIdx]);

        ctx.beginPath();
        ctx.arc(px, py, 3.5, 0, 2 * Math.PI);
        ctx.fill();
      });
    }
  }, [waveform]);

  return (
    <div className="waveform-section">
      <div className="section-heading">
        <h4>Digitized ECG Rhythm Strip</h4>
        <div className="legend">
          <span className="legend-item">
            <span className="legend-line" /> Lead Voltage Trace
          </span>
          <span className="legend-item">
            <span className="legend-dot" /> Detected R-Peaks
          </span>
        </div>
      </div>
      <div className="waveform-canvas-container">
        <canvas ref={canvasRef} height={170} />
      </div>
      <div className="waveform-meta-row">
        <span>Standard Calibration: 25 mm/s, 10 mm/mV</span>
        <span>Contour extracted from uploaded recording</span>
      </div>
    </div>
  );
};
