import React, { useRef } from 'react';
import type { SampleItem } from '../types';

interface UploadPanelProps {
  samples: SampleItem[];
  selectedSample: SampleItem | null;
  onSelectSample: (sample: SampleItem) => void;
  selectedFile: File | null;
  onSelectFile: (file: File) => void;
  previewUrl: string | null;
  previewName: string;
  onClearImage: () => void;
  seconds: number;
  onSecondsChange: (val: number) => void;
  onAnalyze: () => void;
  loading: boolean;
}

export const UploadPanel: React.FC<UploadPanelProps> = ({
  samples,
  selectedSample,
  onSelectSample,
  selectedFile,
  onSelectFile,
  previewUrl,
  previewName,
  onClearImage,
  seconds,
  onSecondsChange,
  onAnalyze,
  loading,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add('drag-active');
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('drag-active');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-active');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onSelectFile(e.target.files[0]);
    }
  };

  const canAnalyze = !loading && (selectedFile !== null || selectedSample !== null);

  return (
    <section className="panel input-panel">
      <div className="panel-header">
        <div className="panel-title">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
          </svg>
          <h2>ECG Trace Acquisition</h2>
        </div>
        <span className="panel-subtitle">Upload single-lead rhythm strip or cropped 12-lead paper scan</span>
      </div>

      {/* Quick Reference Cases */}
      <div className="demo-samples-section">
        <label className="section-label">Select Reference ECG Case:</label>
        <div className="demo-pills">
          {samples.length === 0 ? (
            <span className="text-dim-sm">Loading reference cases...</span>
          ) : (
            samples.map((sample) => {
              const isSelected = selectedSample?.filename === sample.filename;
              return (
                <button
                  key={sample.filename}
                  type="button"
                  className={`pill-btn ${isSelected ? 'active' : ''}`}
                  onClick={() => onSelectSample(sample)}
                  title={`Select ${sample.display_name}`}
                >
                  <span className={`pill-tag ${sample.is_afib ? 'tag-afib' : 'tag-norm'}`}>
                    {sample.is_afib ? 'AFIB' : 'NORM'}
                  </span>
                  <span>{sample.display_name}</span>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Drag & Drop Zone */}
      <div
        className="drop-zone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => {
          if (!previewUrl && fileInputRef.current) {
            fileInputRef.current.click();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png, image/jpeg, image/jpg, image/tiff"
          hidden
          onChange={handleFileInputChange}
        />

        {!previewUrl ? (
          <div className="drop-zone-idle">
            <div className="upload-icon-circle">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
            </div>
            <h3>Drag & Drop ECG trace here</h3>
            <p>Supports PNG, JPG, JPEG, TIFF from telemetry monitors or paper captures</p>
            <button
              type="button"
              className="btn btn-secondary browse-btn"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Choose File
            </button>
          </div>
        ) : (
          <div className="drop-zone-preview">
            <div className="preview-card">
              <img src={previewUrl} alt="ECG Preview" />
              <div className="preview-overlay">
                <span>{previewName}</span>
                <button
                  type="button"
                  className="btn-icon"
                  title="Remove image"
                  onClick={(e) => {
                    e.stopPropagation();
                    onClearImage();
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                >
                  &times;
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recording Duration Setting */}
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="secondsInput">Trace Duration (Seconds)</label>
          <div className="input-with-unit">
            <input
              id="secondsInput"
              type="number"
              value={seconds}
              min={4.0}
              max={30.0}
              step={0.5}
              onChange={(e) => onSecondsChange(parseFloat(e.target.value) || 10.0)}
            />
            <span className="unit">sec</span>
          </div>
          <span className="help-text">Standard rhythm strip window is 10.0 seconds</span>
        </div>
      </div>

      {/* Primary Action Button */}
      <button
        type="button"
        className="btn btn-primary btn-glow"
        disabled={!canAnalyze}
        onClick={onAnalyze}
      >
        {loading ? (
          <span className="btn-loader">
            <span className="spinner" />
            Evaluating Cardiac Rhythm...
          </span>
        ) : (
          <span className="btn-text">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Run AI Diagnostic Analysis
          </span>
        )}
      </button>

      {/* Deep Architecture Card */}
      <div className="info-card">
        <div className="info-icon">⚡</div>
        <div className="info-content">
          <h4>Deep Neural Architecture</h4>
          <p>
            Our deep Vision Transformer analyzes 2D spatial waveform contours, detecting absence of
            organized P-waves, baseline fibrillatory ripples, and conduction disturbances across the
            cardiac cycle.
          </p>
        </div>
      </div>
    </section>
  );
};
