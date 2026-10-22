import React from 'react';
import type { SystemStatus, User } from '../types';

interface HeaderProps {
  systemStatus: SystemStatus | null;
  currentUser: User | null;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({ systemStatus, currentUser, onLogout }) => {
  return (
    <header className="clinical-top-nav">
      <div className="nav-inner-container">
        {/* Hospital Branding */}
        <div className="nav-brand-section">
          <div className="hospital-mark">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="hospital-titles">
            <span className="system-name">CardioVision Healthcare System</span>
            <span className="system-sub">Clinical Cardiology & Arrhythmia Workstation</span>
          </div>
        </div>

        {/* Status & User Credentials */}
        <div className="nav-controls-section">
          <div className="system-health-indicator">
            <span className="health-dot" />
            <span className="health-text">
              {systemStatus?.torch_available ? 'Neural Core Active' : 'Diagnostic Core Ready'}
            </span>
          </div>

          {currentUser && (
            <div className="clinician-session-box">
              <div className="clinician-details">
                <span className="clinician-name">{currentUser.name}</span>
                <span className="clinician-role">
                  {currentUser.role === 'doctor'
                    ? `Physician ${currentUser.license_number ? `• Lic: ${currentUser.license_number}` : ''}`
                    : 'Verified Patient'}
                </span>
              </div>
              <button
                type="button"
                className="clinical-signout-btn"
                onClick={onLogout}
                title="Sign out of clinical session"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
