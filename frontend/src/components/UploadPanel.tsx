import React, { useRef } from 'react';

interface UploadPanelProps {
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

  const canAnalyze = !loading && selectedFile !== null;

  return (
    <section className="panel input-panel">
      <div className="panel-header">
        <div className="panel-title">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
          </svg>
          <h2>ECG Trace Input</h2>
        </div>
        <span className="panel-subtitle">Upload rhythm strip image for automated arrhythmia evaluation</span>
      </div>

      {/* Drag & Drop Upload Zone */}
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
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <h3>Upload ECG Rhythm Strip</h3>
            <p>Drag and drop image file here, or click to browse</p>
            <span className="format-note">Supports PNG, JPG, JPEG, TIFF (rhythm strips or cropped 12-lead rows)</span>
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
              Select Image File
            </button>
          </div>
        ) : (
          <div className="drop-zone-preview">
            <div className="preview-card">
              <img src={previewUrl} alt="ECG Preview" />
              <div className="preview-overlay">
                <div className="preview-info">
                  <span className="preview-name">{previewName}</span>
                  {selectedFile && (
                    <span className="preview-size">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  className="btn-remove"
                  title="Remove image and choose another"
                  onClick={(e) => {
                    e.stopPropagation();
                    onClearImage();
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                  Remove
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recording Duration Setting */}
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="secondsInput">Trace Duration</label>
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
            <span className="unit">seconds</span>
          </div>
          <span className="help-text">Standard rhythm strip span is 10.0 seconds</span>
        </div>
      </div>

      {/* Primary Action Button */}
      <button
        type="button"
        className="btn btn-primary"
        disabled={!canAnalyze}
        onClick={onAnalyze}
      >
        {loading ? (
          <span className="btn-loader">
            <span className="spinner" />
            Analyzing Rhythm & Generating Report...
          </span>
        ) : (
          <span className="btn-text">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Analyze ECG & Generate Report
          </span>
        )}
      </button>

      {/* Clinical Reference Box */}
      <div className="clinical-specs">
        <div className="spec-item">
          <span className="spec-label">Target Condition</span>
          <span className="spec-val">Atrial Fibrillation (AFib) & Arrhythmias</span>
        </div>
        <div className="spec-item">
          <span className="spec-label">Evaluation Engine</span>
          <span className="spec-val">Vision Transformer (ViT) Multi-Label</span>
        </div>
        <div className="spec-item">
          <span className="spec-label">Input Requirement</span>
          <span className="spec-val">Single-lead strip, ≥800px width, ≥8s span</span>
        </div>
      </div>
    </section>
  );
};
