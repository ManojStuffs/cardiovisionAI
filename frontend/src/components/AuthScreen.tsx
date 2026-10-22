import React, { useState, useEffect } from 'react';
import type { User, DoctorOption } from '../types';

interface AuthScreenProps {
  onAuthSuccess: (token: string, user: User) => void;
}

type AuthMode = 'signin' | 'signup' | 'signup_otp' | 'forgot_request' | 'forgot_verify';

const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;

export const AuthScreen: React.FC<AuthScreenProps> = ({ onAuthSuccess }) => {
  const [mode, setMode] = useState<AuthMode>('signin');
  const [role, setRole] = useState<'doctor' | 'patient'>('doctor');

  // Input states - strictly clean, non-prefilled
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Role-specific fields
  const [title, setTitle] = useState('');
  const [licenseNumber, setLicenseNumber] = useState('');
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>('');

  // 6-digit verification code & resend cooldown
  const [otp, setOtp] = useState('');
  const [resendCooldown, setResendCooldown] = useState<number>(0);

  // Auxiliary data & UI states
  const [doctors, setDoctors] = useState<DoctorOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Fetch registered hospital doctors for patient assignment & display choice
  useEffect(() => {
    fetch('/api/doctors')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: DoctorOption[]) => {
        setDoctors(data);
        if (data.length > 0 && !selectedDoctorId) {
          setSelectedDoctorId(data[0].id.toString());
        }
      })
      .catch((err) => console.warn('Could not load hospital directory:', err));
  }, []);

  // Countdown timer for Resend Code
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const validateEmailFormat = (emailStr: string): boolean => {
    return EMAIL_REGEX.test(emailStr.trim());
  };

  // =========================================================================
  // Mode Switchers
  // =========================================================================
  const switchToSignIn = () => {
    setMode('signin');
    setErrorMessage('');
    setSuccessMessage('');
    setOtp('');
  };

  const switchToSignUp = () => {
    setMode('signup');
    setErrorMessage('');
    setSuccessMessage('');
    setOtp('');
  };

  const switchToForgotPassword = () => {
    setMode('forgot_request');
    setErrorMessage('');
    setSuccessMessage('');
    setOtp('');
  };

  // =========================================================================
  // 1. Direct Sign-In Handler
  // =========================================================================
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !validateEmailFormat(cleanEmail)) {
      setErrorMessage('Please enter your valid, original registered email address.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter your account password.');
      return;
    }

    if (role === 'doctor' && !licenseNumber.trim()) {
      setErrorMessage('Medical License / Board Registration Number is required for doctor access.');
      return;
    }

    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        email: cleanEmail,
        password,
        role,
      };

      if (role === 'doctor') {
        payload.license_number = licenseNumber.trim();
      } else if (role === 'patient' && selectedDoctorId) {
        payload.doctor_id = parseInt(selectedDoctorId, 10);
      }

      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Sign-in failed. Please verify your credentials.');
      }

      setSuccessMessage('Authentication verified. Welcome to CardioVision.');
      setTimeout(() => {
        onAuthSuccess(data.token, data.user);
      }, 250);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Sign-in failed.');
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // 2. Step 1 of Sign-Up: Request Email Verification Code
  // =========================================================================
  const handleRequestSignUpOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !validateEmailFormat(cleanEmail)) {
      setErrorMessage('Please enter a valid, original email address to receive your 6-digit verification code.');
      return;
    }

    if (!name.trim() || name.trim().length < 2) {
      setErrorMessage('Full legal name is required (minimum 2 characters).');
      return;
    }

    if (role === 'doctor' && !licenseNumber.trim()) {
      setErrorMessage('Medical License / Board Registration Number is mandatory for physician verification.');
      return;
    }

    if (role === 'patient' && doctors.length > 0 && !selectedDoctorId) {
      setErrorMessage('Please select which doctor to show and link your records to.');
      return;
    }

    if (!password || password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        email: cleanEmail,
        name: name.trim(),
        password,
        role,
        title: title.trim() || (role === 'doctor' ? 'Attending Cardiologist' : 'Patient'),
      };

      if (role === 'doctor') {
        payload.license_number = licenseNumber.trim();
      } else if (role === 'patient' && selectedDoctorId) {
        payload.doctor_id = parseInt(selectedDoctorId, 10);
      }

      const res = await fetch('/api/auth/register-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to dispatch email verification code.');
      }



      setResendCooldown(30);
      setSuccessMessage(`A 6-digit verification code has been dispatched to ${cleanEmail}.`);
      setMode('signup_otp');
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Registration request failed.');
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // 3. Step 2 of Sign-Up: Verify Email OTP & Create Account
  // =========================================================================
  const handleVerifySignUpOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    const cleanOtp = otp.trim().replace(/\D/g, '');
    if (cleanOtp.length < 6) {
      setErrorMessage('Please enter the complete 6-digit verification code sent to your original email.');
      return;
    }

    setLoading(true);
    try {
      const payload: Record<string, unknown> = {
        email: email.trim().toLowerCase(),
        name: name.trim(),
        password,
        role,
        title: title.trim() || (role === 'doctor' ? 'Attending Cardiologist' : 'Patient'),
        code: cleanOtp,
      };

      if (role === 'doctor') {
        payload.license_number = licenseNumber.trim();
      } else if (role === 'patient' && selectedDoctorId) {
        payload.doctor_id = parseInt(selectedDoctorId, 10);
      }

      const res = await fetch('/api/auth/verify-and-register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Email verification failed. Please check the 6-digit code.');
      }

      setSuccessMessage('Original email verified successfully! Account created.');
      setTimeout(() => {
        onAuthSuccess(data.token, data.user);
      }, 350);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Verification failed.');
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // 4. Step 1 of Forgot Password: Send Reset OTP to Email
  // =========================================================================
  const handleRequestPasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail || !validateEmailFormat(cleanEmail)) {
      setErrorMessage('Please enter your valid, original registered email address.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/auth/forgot-password-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: cleanEmail }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Could not find account or send reset code.');
      }



      setResendCooldown(30);
      setSuccessMessage(`A 6-digit password reset verification code was dispatched to ${cleanEmail}.`);
      setMode('forgot_verify');
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Password reset request failed.');
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // 5. Step 2 of Forgot Password: Verify Code & Change Password
  // =========================================================================
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    const cleanOtp = otp.trim().replace(/\D/g, '');
    if (cleanOtp.length < 6) {
      setErrorMessage('Please enter the 6-digit verification code received in your email.');
      return;
    }

    if (!newPassword || newPassword.length < 6) {
      setErrorMessage('New password must be at least 6 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage('New password and confirmation password do not match.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          code: cleanOtp,
          new_password: newPassword,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to reset password. Please check your verification code.');
      }

      setSuccessMessage('Password changed successfully! Authenticating you into your portal...');
      setTimeout(() => {
        onAuthSuccess(data.token, data.user);
      }, 400);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  };

  // =========================================================================
  // 6. Resend Verification Code Helper
  // =========================================================================
  const handleResendCode = async () => {
    if (resendCooldown > 0) return;
    setErrorMessage('');
    setSuccessMessage('');
    setLoading(true);

    const cleanEmail = email.trim().toLowerCase();
    const purpose = mode === 'forgot_verify' ? 'password_reset' : 'signup';

    try {
      const res = await fetch('/api/auth/resend-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: cleanEmail,
          purpose,
          name: name.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to resend code.');
      }


      setResendCooldown(30);
      setSuccessMessage(`A fresh 6-digit verification code has been sent to ${cleanEmail}.`);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Could not resend verification code.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="clinical-auth-page">
      <div className="clinical-auth-container">
        {/* Institutional Medical Header */}
        <div className="clinical-auth-header">
          <div className="hospital-badge-top">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>CardioVision Healthcare System</span>
          </div>
          <h1>Clinical Electrocardiography & Arrhythmia Platform</h1>
          <p className="auth-instructions">
            Authorized healthcare access portal with original email address verification and secure password recovery.
          </p>
        </div>

        {/* Authentication Card */}
        <div className="clinical-auth-card">
          {/* Mode Switcher: Sign In vs Create Account (shown only on root steps) */}
          {(mode === 'signin' || mode === 'signup') && (
            <div className="auth-mode-switch">
              <button
                type="button"
                className={`mode-tab ${mode === 'signin' ? 'active' : ''}`}
                onClick={switchToSignIn}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`mode-tab ${mode === 'signup' ? 'active' : ''}`}
                onClick={switchToSignUp}
              >
                Create Account (Verify Email)
              </button>
            </div>
          )}

          {/* Error & Success Alerts */}
          {errorMessage && (
            <div className="clinical-alert-error" role="alert">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="clinical-alert-success" role="status">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>{successMessage}</span>
            </div>
          )}

          {/* ===============================================================
              VIEW 1: SIGN IN
             =============================================================== */}
          {mode === 'signin' && (
            <form onSubmit={handleSignIn} className="clinical-form">
              {/* Account Role Selector */}
              <div className="field-group">
                <label className="field-label">Portal Account Type</label>
                <div className="clinical-role-grid">
                  <button
                    type="button"
                    className={`clinical-role-option ${role === 'doctor' ? 'selected' : ''}`}
                    onClick={() => {
                      setRole('doctor');
                      setErrorMessage('');
                    }}
                  >
                    <div className="role-icon">
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                      </svg>
                    </div>
                    <div>
                      <div className="role-title">Medical Doctor / Clinician</div>
                      <div className="role-desc">ECG upload, AI rhythm analysis & report sign-off</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`clinical-role-option ${role === 'patient' ? 'selected' : ''}`}
                    onClick={() => {
                      setRole('patient');
                      setErrorMessage('');
                    }}
                  >
                    <div className="role-icon">
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>
                    <div>
                      <div className="role-title">Patient Portal</div>
                      <div className="role-desc">View verified ECG records from attending doctor</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Doctor Medical License Number (Mandatory on sign-in) */}
              {role === 'doctor' && (
                <div className="field-group">
                  <label htmlFor="signInLicense" className="field-label">
                    Medical License / Board Registration Number <span className="required-star">*</span>
                  </label>
                  <input
                    id="signInLicense"
                    type="text"
                    required
                    className="clinical-input"
                    placeholder="e.g. MD-CARDIO-882914 or State Board ID"
                    value={licenseNumber}
                    onChange={(e) => setLicenseNumber(e.target.value)}
                    autoComplete="off"
                  />
                  <span className="field-hint">Required to authenticate physician medical credentials.</span>
                </div>
              )}

              {/* Patient: Which Doctor to Show */}
              {role === 'patient' && (
                <div className="field-group">
                  <label htmlFor="signInDoctor" className="field-label">
                    Which Doctor to Show: <span className="required-star">*</span>
                  </label>
                  <select
                    id="signInDoctor"
                    className="clinical-select"
                    value={selectedDoctorId}
                    onChange={(e) => setSelectedDoctorId(e.target.value)}
                  >
                    {doctors.length === 0 ? (
                      <option value="">No doctors registered in hospital directory</option>
                    ) : (
                      doctors.map((doc) => (
                        <option key={doc.id} value={doc.id}>
                          {doc.name} — {doc.title || 'Cardiology'} {doc.license_number ? `(Lic: ${doc.license_number})` : ''}
                        </option>
                      ))
                    )}
                  </select>
                  <span className="field-hint">Select which attending doctor’s certified reports to display upon sign-in.</span>
                </div>
              )}

              {/* Email Address */}
              <div className="field-group">
                <label htmlFor="signInEmail" className="field-label">
                  Original Registered Email Address <span className="required-star">*</span>
                </label>
                <input
                  id="signInEmail"
                  type="email"
                  required
                  className="clinical-input"
                  placeholder={role === 'doctor' ? 'doctor@hospital.org' : 'patient@domain.com'}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>

              {/* Account Password */}
              <div className="field-group">
                <div className="field-header-row">
                  <label htmlFor="signInPassword" className="field-label">
                    Account Password <span className="required-star">*</span>
                  </label>
                  <button
                    type="button"
                    className="forgot-password-link"
                    onClick={switchToForgotPassword}
                  >
                    Forgot Password?
                  </button>
                </div>
                <div className="input-with-toggle">
                  <input
                    id="signInPassword"
                    type={showPassword ? 'text' : 'password'}
                    required
                    className="clinical-input"
                    placeholder="Enter your account password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="toggle-password-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button type="submit" className="clinical-btn-primary" disabled={loading}>
                {loading
                  ? 'Verifying Credentials...'
                  : role === 'doctor'
                  ? 'Sign In to Clinical Workstation →'
                  : 'Sign In to Patient Portal →'}
              </button>

              {/* Notice for new users */}
              <div className="auth-card-footer-tip">
                <span>Need a verified account?</span>{' '}
                <button type="button" className="auth-text-btn" onClick={switchToSignUp}>
                  Register with Email Verification →
                </button>
              </div>
            </form>
          )}

          {/* ===============================================================
              VIEW 2: CREATE ACCOUNT (STEP 1: DETAILS & ORIGINAL EMAIL)
             =============================================================== */}
          {mode === 'signup' && (
            <form onSubmit={handleRequestSignUpOtp} className="clinical-form">
              {/* Account Role Selector */}
              <div className="field-group">
                <label className="field-label">Portal Account Type</label>
                <div className="clinical-role-grid">
                  <button
                    type="button"
                    className={`clinical-role-option ${role === 'doctor' ? 'selected' : ''}`}
                    onClick={() => {
                      setRole('doctor');
                      setErrorMessage('');
                    }}
                  >
                    <div className="role-icon">
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                      </svg>
                    </div>
                    <div>
                      <div className="role-title">Medical Doctor / Clinician</div>
                      <div className="role-desc">Requires medical license verification</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    className={`clinical-role-option ${role === 'patient' ? 'selected' : ''}`}
                    onClick={() => {
                      setRole('patient');
                      setErrorMessage('');
                    }}
                  >
                    <div className="role-icon">
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>
                    <div>
                      <div className="role-title">Patient Portal</div>
                      <div className="role-desc">Access reports from your assigned doctor</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Full Legal Name */}
              <div className="field-group">
                <label htmlFor="regName" className="field-label">
                  Full Legal Name <span className="required-star">*</span>
                </label>
                <input
                  id="regName"
                  type="text"
                  required
                  className="clinical-input"
                  placeholder={role === 'doctor' ? 'Dr. Sarah Jenkins, MD' : 'Robert Johnson'}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                />
              </div>

              {/* DOCTOR: Licence Number (MANDATORY) */}
              {role === 'doctor' && (
                <div className="field-group">
                  <label htmlFor="regLicense" className="field-label">
                    Medical License / Board Registration Number <span className="required-star">*</span>
                  </label>
                  <input
                    id="regLicense"
                    type="text"
                    required
                    className="clinical-input"
                    placeholder="e.g. MD-CARDIO-882914 or State Board ID"
                    value={licenseNumber}
                    onChange={(e) => setLicenseNumber(e.target.value)}
                    autoComplete="off"
                  />
                  <span className="field-hint">Required for official diagnostic signature and legal clinical sign-off.</span>
                </div>
              )}

              {/* PATIENT: Attending Doctor Selection */}
              {role === 'patient' && (
                <div className="field-group">
                  <label htmlFor="regDoctor" className="field-label">
                    Select Attending Cardiologist / Doctor: <span className="required-star">*</span>
                  </label>
                  <select
                    id="regDoctor"
                    className="clinical-select"
                    value={selectedDoctorId}
                    onChange={(e) => setSelectedDoctorId(e.target.value)}
                  >
                    {doctors.length === 0 ? (
                      <option value="">No doctors currently available</option>
                    ) : (
                      doctors.map((doc) => (
                        <option key={doc.id} value={doc.id}>
                          {doc.name} — {doc.title || 'Cardiology'} {doc.license_number ? `(Lic: ${doc.license_number})` : ''}
                        </option>
                      ))
                    )}
                  </select>
                  <span className="field-hint">Your cardiac telemetry and diagnostic records will be linked to this physician.</span>
                </div>
              )}

              {/* Specialty Title or MRN */}
              <div className="field-group">
                <label htmlFor="regTitle" className="field-label">
                  {role === 'doctor' ? 'Department / Medical Specialty' : 'Patient Age / Medical Record Number (Optional)'}
                </label>
                <input
                  id="regTitle"
                  type="text"
                  className="clinical-input"
                  placeholder={role === 'doctor' ? 'e.g. Cardiac Electrophysiology' : 'e.g. Age: 54 | MRN: PT-8021'}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              {/* ORIGINAL EMAIL ADDRESS */}
              <div className="field-group">
                <label htmlFor="regEmail" className="field-label">
                  Original Email Address (For 6-Digit Verification Code) <span className="required-star">*</span>
                </label>
                <input
                  id="regEmail"
                  type="email"
                  required
                  className="clinical-input"
                  placeholder={role === 'doctor' ? 'doctor@hospital.org' : 'patient@gmail.com'}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
                <span className="field-hint">
                  A real verification code will be dispatched to this address to verify your identity.
                </span>
              </div>

              {/* Account Password */}
              <div className="field-group">
                <label htmlFor="regPassword" className="field-label">
                  Account Password <span className="required-star">*</span>
                </label>
                <div className="input-with-toggle">
                  <input
                    id="regPassword"
                    type={showPassword ? 'text' : 'password'}
                    required
                    className="clinical-input"
                    placeholder="Minimum 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="toggle-password-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Step 1 Submit Button */}
              <button type="submit" className="clinical-btn-primary" disabled={loading}>
                {loading ? 'Dispatching Verification Code...' : 'Verify Original Email Address →'}
              </button>

              <div className="auth-card-footer-tip">
                <span>Already have an account?</span>{' '}
                <button type="button" className="auth-text-btn" onClick={switchToSignIn}>
                  Sign in here →
                </button>
              </div>
            </form>
          )}

          {/* ===============================================================
              VIEW 3: CREATE ACCOUNT (STEP 2: ENTER EMAIL OTP)
             =============================================================== */}
          {mode === 'signup_otp' && (
            <form onSubmit={handleVerifySignUpOtp} className="clinical-form">
              <div className="verification-step-header">
                <div className="verification-icon-badge">
                  <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                </div>
                <h3>Verify Your Original Email Address</h3>
                <p className="verification-step-sub">
                  We dispatched a 6-digit verification code to confirm ownership of:
                </p>
                <div className="verified-email-pill">
                  <span>{email}</span>
                  <button
                    type="button"
                    className="email-edit-btn"
                    onClick={() => {
                      setMode('signup');
                      setErrorMessage('');
                    }}
                    title="Change email"
                  >
                    Edit
                  </button>
                </div>
              </div>

              <div className="field-group">
                <label htmlFor="signUpOtpInput" className="field-label text-center">
                  Enter 6-Digit Email Verification Code <span className="required-star">*</span>
                </label>
                <input
                  id="signUpOtpInput"
                  type="text"
                  required
                  maxLength={6}
                  className="clinical-input otp-large-input"
                  placeholder="&bull; &bull; &bull; &bull; &bull; &bull;"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  autoFocus
                  autoComplete="one-time-code"
                />
                <span className="field-hint text-center">Code expires in 10 minutes. Single-use security token.</span>
              </div>

              <button
                type="submit"
                className="clinical-btn-primary"
                disabled={loading || otp.replace(/\D/g, '').length < 6}
              >
                {loading ? 'Verifying Code...' : 'Verify Email & Complete Registration →'}
              </button>

              <div className="verification-actions-row">
                <button
                  type="button"
                  className="auth-link-secondary"
                  disabled={loading || resendCooldown > 0}
                  onClick={handleResendCode}
                >
                  {resendCooldown > 0 ? `Resend Code in ${resendCooldown}s` : 'Resend Verification Code'}
                </button>

                <button
                  type="button"
                  className="auth-link-secondary"
                  onClick={() => {
                    setMode('signup');
                    setErrorMessage('');
                  }}
                >
                  ← Back to Details
                </button>
              </div>
            </form>
          )}

          {/* ===============================================================
              VIEW 4: FORGOT PASSWORD (STEP 1: ENTER REGISTERED EMAIL)
             =============================================================== */}
          {mode === 'forgot_request' && (
            <form onSubmit={handleRequestPasswordReset} className="clinical-form">
              <div className="verification-step-header">
                <div className="verification-icon-badge">
                  <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <h3>Reset Account Password</h3>
                <p className="verification-step-sub">
                  Enter your registered original email address. We will verify your identity by sending a 6-digit confirmation code.
                </p>
              </div>

              <div className="field-group">
                <label htmlFor="forgotEmail" className="field-label">
                  Original Registered Email Address <span className="required-star">*</span>
                </label>
                <input
                  id="forgotEmail"
                  type="email"
                  required
                  className="clinical-input"
                  placeholder="e.g. dr.smith@cardiovision.org or patient@domain.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                  autoComplete="email"
                />
                <span className="field-hint">
                  The password change code will be sent to this original email address.
                </span>
              </div>

              <button type="submit" className="clinical-btn-primary" disabled={loading}>
                {loading ? 'Dispatching Verification Code...' : 'Send Password Reset Code →'}
              </button>

              <div className="auth-card-footer-tip">
                <button type="button" className="auth-link-secondary" onClick={switchToSignIn}>
                  ← Back to Sign In
                </button>
              </div>
            </form>
          )}

          {/* ===============================================================
              VIEW 5: FORGOT PASSWORD (STEP 2: ENTER OTP & NEW PASSWORD)
             =============================================================== */}
          {mode === 'forgot_verify' && (
            <form onSubmit={handleResetPassword} className="clinical-form">
              <div className="verification-step-header">
                <div className="verification-icon-badge">
                  <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 2l-2 2m-1.5 6.5l3-3m-6 3l-3 3-3-3m-4 4L2 22l6.5-2.5 9-9-4-4-9 9z" />
                  </svg>
                </div>
                <h3>Set New Account Password</h3>
                <p className="verification-step-sub">
                  Enter the 6-digit verification code sent to:
                </p>
                <div className="verified-email-pill">
                  <span>{email}</span>
                </div>
              </div>

              {/* 6-Digit Verification Code */}
              <div className="field-group">
                <label htmlFor="resetOtpInput" className="field-label text-center">
                  6-Digit Email Verification Code <span className="required-star">*</span>
                </label>
                <input
                  id="resetOtpInput"
                  type="text"
                  required
                  maxLength={6}
                  className="clinical-input otp-large-input"
                  placeholder="&bull; &bull; &bull; &bull; &bull; &bull;"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  autoFocus
                  autoComplete="one-time-code"
                />
              </div>

              {/* New Password */}
              <div className="field-group">
                <label htmlFor="newPasswordInput" className="field-label">
                  New Password <span className="required-star">*</span>
                </label>
                <div className="input-with-toggle">
                  <input
                    id="newPasswordInput"
                    type={showNewPassword ? 'text' : 'password'}
                    required
                    className="clinical-input"
                    placeholder="Minimum 6 characters"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="toggle-password-btn"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    title={showNewPassword ? 'Hide password' : 'Show password'}
                  >
                    {showNewPassword ? (
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Confirm New Password */}
              <div className="field-group">
                <label htmlFor="confirmPasswordInput" className="field-label">
                  Confirm New Password <span className="required-star">*</span>
                </label>
                <input
                  id="confirmPasswordInput"
                  type={showNewPassword ? 'text' : 'password'}
                  required
                  className="clinical-input"
                  placeholder="Re-enter your new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                />
                {confirmPassword && newPassword !== confirmPassword && (
                  <span className="field-error-hint">Passwords do not match.</span>
                )}
              </div>

              <button
                type="submit"
                className="clinical-btn-primary"
                disabled={loading || otp.replace(/\D/g, '').length < 6 || newPassword.length < 6}
              >
                {loading ? 'Updating Password...' : 'Verify Email & Change Password →'}
              </button>

              <div className="verification-actions-row">
                <button
                  type="button"
                  className="auth-link-secondary"
                  disabled={loading || resendCooldown > 0}
                  onClick={handleResendCode}
                >
                  {resendCooldown > 0 ? `Resend Code in ${resendCooldown}s` : 'Resend Verification Code'}
                </button>

                <button type="button" className="auth-link-secondary" onClick={switchToSignIn}>
                  ← Cancel & Back to Sign In
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Institutional Regulatory Footer */}
        <div className="clinical-auth-footer">
          <span>CardioVision Healthcare System • Clinical Arrhythmia Workstation • HL7 & HIPAA Compliant</span>
        </div>
      </div>
    </div>
  );
};
