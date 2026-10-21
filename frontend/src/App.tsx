import { useState, useEffect } from 'react';
import type { DiagnosticResult, SystemStatus, User, PatientOption } from './types';
import { Header } from './components/Header';
import { UploadPanel } from './components/UploadPanel';
import { ResultsPanel } from './components/ResultsPanel';
import { PatientPortal } from './components/PatientPortal';
import { AuthModal } from './components/AuthModal';

export function App() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  // Authentication state
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);

  // Doctor Workspace state
  const [patients, setPatients] = useState<PatientOption[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<PatientOption | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState<string>('');
  const [seconds, setSeconds] = useState<number>(10.0);
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<DiagnosticResult | null>(null);

  // Load stored auth or auto-login default Doctor on first visit
  useEffect(() => {
    const savedToken = localStorage.getItem('cv_token');
    const savedUser = localStorage.getItem('cv_user');

    if (savedToken && savedUser) {
      try {
        setAuthToken(savedToken);
        setCurrentUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('cv_token');
        localStorage.removeItem('cv_user');
      }
    } else {
      // Auto-login default Doctor for frictionless initial experience
      fetch('/api/auth/demo-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'doctor' }),
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data?.token && data?.user) {
            setAuthToken(data.token);
            setCurrentUser(data.user);
            localStorage.setItem('cv_token', data.token);
            localStorage.setItem('cv_user', JSON.stringify(data.user));
          }
        })
        .catch((err) => console.warn('Demo login notice:', err));
    }

    // Fetch system status
    fetch('/api/system-status')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setSystemStatus(data);
      })
      .catch((err) => console.warn('Status check notice:', err));
  }, []);

  // Fetch registered patients for Doctor
  useEffect(() => {
    if (currentUser?.role === 'doctor' && authToken) {
      fetch('/api/doctor/patients', {
        headers: { Authorization: `Bearer ${authToken}` },
      })
        .then((res) => (res.ok ? res.json() : []))
        .then((data: PatientOption[]) => {
          setPatients(data);
          if (data.length > 0 && !selectedPatient) {
            setSelectedPatient(data[0]);
          }
        })
        .catch((err) => console.warn('Error fetching patients:', err));
    }
  }, [currentUser?.role, authToken]);

  const handleAuthSuccess = (token: string, user: User) => {
    setAuthToken(token);
    setCurrentUser(user);
    localStorage.setItem('cv_token', token);
    localStorage.setItem('cv_user', JSON.stringify(user));
  };

  const handleLogout = () => {
    setAuthToken(null);
    setCurrentUser(null);
    localStorage.removeItem('cv_token');
    localStorage.removeItem('cv_user');
    setResults(null);
  };

  const handleQuickSwitchRole = async (targetRole: 'doctor' | 'patient') => {
    try {
      const res = await fetch('/api/auth/demo-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: targetRole }),
      });
      const data = await res.json();
      if (res.ok && data.token && data.user) {
        handleAuthSuccess(data.token, data.user);
      }
    } catch (err) {
      console.error('Role switch failed:', err);
    }
  };

  const handleSelectFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      alert('Please upload a valid image file (PNG, JPG, or TIFF).');
      return;
    }
    setSelectedFile(file);
    setPreviewName(file.name);

    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewUrl(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleClearImage = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setPreviewName('');
  };

  const handleAnalyze = async () => {
    if (!selectedFile || !authToken) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('seconds', seconds.toString());
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || 'Diagnostic evaluation failed.');
      }

      setResults(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error during inference';
      alert(`Diagnostic Analysis Failed: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePublishReport = async (notes: string, recommendation: string): Promise<boolean> => {
    if (!authToken || !results || !selectedPatient) {
      alert('Cannot publish report: Doctor session, results, or patient selection missing.');
      return false;
    }

    try {
      const res = await fetch('/api/doctor/save-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          result_data: results,
          doctor_notes: notes,
          clinical_recommendation: recommendation,
          image_url: previewUrl || '',
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to publish report.');

      alert(`Official report certified and published to ${selectedPatient.name}'s Patient Portal!`);
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Publish failed';
      alert(`Report publication failed: ${message}`);
      return false;
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="app-root">
      {/* Institutional Clinical Header */}
      <Header
        systemStatus={systemStatus}
        currentUser={currentUser}
        onOpenAuth={() => setAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Role Navigation & Mode Switcher Bar */}
      {currentUser && (
        <div className="role-switcher-banner no-print">
          <div className="banner-badge">
            <span className="pulse-indicator" />
            <span>
              Active Role: <b>{currentUser.role === 'doctor' ? 'Medical Doctor Console' : 'Patient Records Portal'}</b> (
              {currentUser.name})
            </span>
          </div>

          <div className="role-switch-actions">
            {currentUser.role === 'doctor' ? (
              <button
                className="role-toggle-btn switch-to-patient"
                onClick={() => handleQuickSwitchRole('patient')}
                title="Switch to Patient view to see what your patient sees"
              >
                <span>👤 Switch to Patient Portal (John Doe) →</span>
              </button>
            ) : (
              <button
                className="role-toggle-btn switch-to-doctor"
                onClick={() => handleQuickSwitchRole('doctor')}
                title="Switch back to Doctor Console to analyze ECG traces"
              >
                <span>🩺 Switch to Doctor Console (Dr. Sarah Smith) →</span>
              </button>
            )}

            <button className="change-account-btn" onClick={() => setAuthModalOpen(true)}>
              Switch / Sign In with Another Email
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area based on User Role */}
      {!currentUser ? (
        <div className="unauth-landing">
          <div className="unauth-card">
            <div className="unauth-icon">🫀</div>
            <h2>CardioVision Clinical Portal</h2>
            <p>
              Please sign in with your email verification code to access the diagnostic workstation or your patient
              records.
            </p>
            <div className="unauth-actions">
              <button className="btn btn-primary" onClick={() => setAuthModalOpen(true)}>
                Sign In / Register with Email Verification →
              </button>
            </div>
          </div>
        </div>
      ) : currentUser.role === 'doctor' ? (
        /* DOCTOR WORKSPACE: Dual-Panel Side-by-Side Analysis */
        <main className="main-container">
          <UploadPanel
            selectedFile={selectedFile}
            onSelectFile={handleSelectFile}
            previewUrl={previewUrl}
            previewName={previewName}
            onClearImage={handleClearImage}
            seconds={seconds}
            onSecondsChange={setSeconds}
            onAnalyze={handleAnalyze}
            loading={loading}
            patients={patients}
            selectedPatient={selectedPatient}
            onSelectPatient={setSelectedPatient}
          />

          <ResultsPanel
            results={results}
            onPrint={handlePrint}
            seconds={seconds}
            selectedPatient={selectedPatient}
            onPublishReport={handlePublishReport}
          />
        </main>
      ) : (
        /* PATIENT PORTAL: View only doctor-released reports for their name */
        <main className="patient-container">
          <PatientPortal user={currentUser} token={authToken || ''} />
        </main>
      )}

      {/* Authentication & Verification Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </div>
  );
}

export default App;
