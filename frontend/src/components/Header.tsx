import React from 'react';
import { Oscilloscope } from './Oscilloscope';
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
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div className="brand-text">
            <h1>
              CARDIOVISION<span>AI</span>
            </h1>
            <p className="tagline">Clinical Atrial Fibrillation & Arrhythmia Intelligence</p>
          </div>
        </div>

        <div className="header-status">
          <div className="status-chip">
            <span className="status-dot pulsating" />
            <span className="status-label">
              {systemStatus?.torch_available ? 'Neural Core: Active' : 'Neural Core: Ready'}
            </span>
          </div>

          <div className="model-badge" title="Deep Neural Architecture">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            <span>{systemStatus?.architecture || 'Vision Transformer Architecture'}</span>
          </div>
        </div>
      </div>

      <Oscilloscope />
    </header>
  );
};
