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
      canvas.height = container.clientHeight || 160;
    }

    const W = canvas.width;
    const H = canvas.height;
    const values = waveform.values || [];
    const peakTimes = waveform.peak_indices || [];

    if (values.length < 2) return;

    // Draw clinical ECG grid background
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.04)';
    ctx.lineWidth = 1;

    // Grid lines
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
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
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

    // Draw main ECG lead trace
    ctx.beginPath();
    const xStep = W / (values.length - 1);
    ctx.moveTo(0, toCanvasY(values[0]));

    for (let i = 1; i < values.length; i++) {
      ctx.lineTo(i * xStep, toCanvasY(values[i]));
    }

    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 2;
    ctx.shadowBlur = 10;
    ctx.shadowColor = 'rgba(0, 240, 255, 0.4)';
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Peak markers
    if (waveform.times && waveform.times.length === values.length && peakTimes.length > 0) {
      const maxTime = waveform.times[waveform.times.length - 1] || 1;
      ctx.fillStyle = '#ff3366';
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#ff3366';

      peakTimes.forEach((pt) => {
        const px = (pt / maxTime) * W;
        const sampleIdx = Math.min(
          values.length - 1,
          Math.max(0, Math.round((pt / maxTime) * (values.length - 1)))
        );
        const py = toCanvasY(values[sampleIdx]);

        ctx.beginPath();
        ctx.arc(px, py, 4, 0, 2 * Math.PI);
        ctx.fill();
      });
      ctx.shadowBlur = 0;
    }
  }, [waveform]);

  return (
    <div className="waveform-section">
      <div className="section-heading">
        <h4>Digitized ECG Waveform Trace</h4>
        <span className="legend">
          <span className="legend-dot" /> Segment Peaks
        </span>
      </div>
      <div className="waveform-canvas-container">
        <canvas ref={canvasRef} height={160} />
      </div>
      <p className="waveform-caption">
        Lead voltage contour extracted from the image across the recording window.
      </p>
    </div>
  );
};
