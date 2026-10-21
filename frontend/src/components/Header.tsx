import React from 'react';
import type { SystemStatus, User } from '../types';

interface HeaderProps {
  systemStatus: SystemStatus | null;
  currentUser: User | null;
  onOpenAuth: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({ systemStatus, currentUser, onOpenAuth, onLogout }) => {
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

          {/* User Account / Role Badge */}
          {currentUser ? (
            <div className="user-profile-widget">
              <div className={`user-badge ${currentUser.role === 'doctor' ? 'doctor-badge' : 'patient-badge'}`}>
                <span className="user-avatar-icon">{currentUser.role === 'doctor' ? '👨‍⚕️' : '👤'}</span>
                <div className="user-text-info">
                  <strong>{currentUser.name}</strong>
                  <span className="user-role-label">
                    {currentUser.role === 'doctor' ? 'ATTENDING DOCTOR' : 'VERIFIED PATIENT'}
                  </span>
                </div>
              </div>
              <button className="auth-btn-header logout-btn" onClick={onLogout} title="Sign Out">
                Sign Out
              </button>
            </div>
          ) : (
            <button className="auth-btn-header login-btn" onClick={onOpenAuth}>
              <span className="login-icon">🔒</span>
              Sign In / Register
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
