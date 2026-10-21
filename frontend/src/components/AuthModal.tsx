import React, { useState } from 'react';
import type { User } from '../types';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess: (token: string, user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onAuthSuccess }) => {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [role, setRole] = useState<'doctor' | 'patient'>('doctor');
  const [step, setStep] = useState<'input' | 'otp'>('input');

  // Form Fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [title, setTitle] = useState('');
  const [otp, setOtp] = useState('');

  // States
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      if (mode === 'signup') {
        const res = await fetch('/api/auth/register-request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            email,
            password,
            role,
            title: title || (role === 'doctor' ? 'Attending Cardiologist' : 'Patient')
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to send verification code.');

        if (data.dev_otp) setDevOtpHint(data.dev_otp);
        setStep('otp');
      } else {
        const res = await fetch('/api/auth/login-request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to authenticate credentials.');

        if (data.dev_otp) setDevOtpHint(data.dev_otp);
        setStep('otp');
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Authentication request failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setLoading(true);

    try {
      if (mode === 'signup') {
        const res = await fetch('/api/auth/verify-and-register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            email,
            password,
            role,
            title: title || (role === 'doctor' ? 'Attending Cardiologist' : 'Patient'),
            otp
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Verification code failed.');

        onAuthSuccess(data.token, data.user);
        onClose();
      } else {
        const res = await fetch('/api/auth/verify-login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, otp })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Invalid verification code.');

        onAuthSuccess(data.token, data.user);
        onClose();
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Verification failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (demoRole: 'doctor' | 'patient') => {
    setErrorMessage('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/demo-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: demoRole })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Demo login failed.');

      onAuthSuccess(data.token, data.user);
      onClose();
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Demo sign-in failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <div className="auth-modal">
        <button className="auth-close-btn" onClick={onClose} title="Close">
          &times;
        </button>

        <div className="auth-header">
          <div className="auth-icon">🫀</div>
          <h2>CardioVision Security Portal</h2>
          <p>Clinical authentication with verified email delivery</p>
        </div>

        {/* Mode Tabs */}
        {step === 'input' && (
          <div className="auth-tabs">
            <button
              className={`auth-tab ${mode === 'signin' ? 'active' : ''}`}
              onClick={() => {
                setMode('signin');
                setErrorMessage('');
              }}
            >
              Sign In
            </button>
            <button
              className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => {
                setMode('signup');
                setErrorMessage('');
              }}
            >
              Create Account
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="auth-error-banner">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        {devOtpHint && step === 'otp' && (
          <div className="auth-dev-hint">
            <span>✉️ Verification code sent to {email}!</span>
            <span className="dev-code-chip">
              Demo Code: <b>{devOtpHint}</b>
            </span>
          </div>
        )}

        {step === 'input' ? (
          <form onSubmit={handleRequestOtp} className="auth-form">
            {mode === 'signup' && (
              <>
                <div className="form-group">
                  <label>Select Your Institutional Role</label>
                  <div className="role-selector">
                    <button
                      type="button"
                      className={`role-btn ${role === 'doctor' ? 'selected' : ''}`}
                      onClick={() => setRole('doctor')}
                    >
                      <span className="role-icon">🩺</span>
                      <div className="role-info">
                        <strong>Medical Doctor</strong>
                        <small>Full analysis & diagnostic upload</small>
                      </div>
                    </button>
                    <button
                      type="button"
                      className={`role-btn ${role === 'patient' ? 'selected' : ''}`}
                      onClick={() => setRole('patient')}
                    >
                      <span className="role-icon">👤</span>
                      <div className="role-info">
                        <strong>Patient</strong>
                        <small>Access doctor-released reports</small>
                      </div>
                    </button>
                  </div>
                </div>

                <div className="form-group">
                  <label>Full Legal Name</label>
                  <input
                    type="text"
                    required
                    placeholder={role === 'doctor' ? 'e.g. Dr. Alex Mercer, MD' : 'e.g. Robert Johnson'}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>{role === 'doctor' ? 'Medical Specialty / Title' : 'Age & Clinical ID (Optional)'}</label>
                  <input
                    type="text"
                    placeholder={role === 'doctor' ? 'e.g. Cardiac Electrophysiology, Dept. Head' : 'e.g. Age: 54 | MRN-4081'}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>
              </>
            )}

            <div className="form-group">
              <label>Institutional / Personal Email</label>
              <input
                type="email"
                required
                placeholder="name@organization.org"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                required
                placeholder="Minimum 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? 'Sending Code...' : mode === 'signin' ? 'Verify via Email Code →' : 'Proceed to Email Verification →'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp} className="auth-form">
            <div className="otp-prompt">
              <p>
                We have generated a 6-digit verification code for:
                <br />
                <strong>{email}</strong>
              </p>
              <p className="otp-subtext">Check your inbox or use the instant demo code shown above.</p>
            </div>

            <div className="form-group">
              <label>Enter 6-Digit Email Code</label>
              <input
                type="text"
                required
                maxLength={6}
                placeholder="123456"
                className="otp-input"
                autoFocus
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              />
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading || otp.length < 6}>
              {loading ? 'Verifying...' : 'Authenticate & Enter Portal'}
            </button>

            <button
              type="button"
              className="auth-back-btn"
              onClick={() => {
                setStep('input');
                setDevOtpHint(null);
                setOtp('');
              }}
            >
              ← Back / Edit Email
            </button>
          </form>
        )}

        {/* 1-Click Demo Logins for Evaluators */}
        <div className="auth-demo-divider">
          <span>Or Quick 1-Click Evaluation</span>
        </div>

        <div className="auth-demo-buttons">
          <button
            type="button"
            className="demo-btn demo-doctor"
            onClick={() => handleDemoLogin('doctor')}
            disabled={loading}
          >
            <span className="demo-icon">👨‍⚕️</span>
            <div>
              <strong>Quick Doctor Login</strong>
              <small>Dr. Sarah Smith (Electrophysiologist)</small>
            </div>
          </button>

          <button
            type="button"
            className="demo-btn demo-patient"
            onClick={() => handleDemoLogin('patient')}
            disabled={loading}
          >
            <span className="demo-icon">👤</span>
            <div>
              <strong>Quick Patient Login</strong>
              <small>John Doe (View Assigned Reports)</small>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
};
