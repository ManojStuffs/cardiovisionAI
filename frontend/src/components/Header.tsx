import React from 'react';
import type { SystemStatus } from '../types';

interface HeaderProps {
  systemStatus: SystemStatus | null;
}

export const Header: React.FC<HeaderProps> = ({ systemStatus }) => {
  return (
    <header className="app-header">
      <div className="header-container">
        <div className="brand">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="brand-text">
            <h1>CardioVision ECG</h1>
            <p className="tagline">Clinical Atrial Fibrillation & Arrhythmia Diagnostic System</p>
          </div>
        </div>

        <div className="header-status">
          <div className="status-chip">
            <span className="status-dot" />
            <span className="status-label">
              {systemStatus?.torch_available ? 'System Ready • Local Neural Core' : 'System Ready • Diagnostic Engine Active'}
            </span>
          </div>

          <div className="model-badge" title="Underlying Neural Network">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
            <span>{systemStatus?.architecture || 'Vision Transformer (ViT)'}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
