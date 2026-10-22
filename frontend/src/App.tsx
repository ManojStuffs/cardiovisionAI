import { useState, useEffect } from 'react';
import type { DiagnosticResult, SystemStatus, User, PatientOption } from './types';
import { Header } from './components/Header';
import { AuthScreen } from './components/AuthScreen';
import { UploadPanel } from './components/UploadPanel';
import { ResultsPanel } from './components/ResultsPanel';
import { PatientPortal } from './components/PatientPortal';

export function App() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  // Authentication state - Strictly gated, no auto-login
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);

  // Doctor Workspace state
  const [patients, setPatients] = useState<PatientOption[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<PatientOption | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState<string>('');
  const [seconds, setSeconds] = useState<number>(10.0);
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<DiagnosticResult | null>(null);

  // Session verification: Ensure token is actively validated before granting access
  useEffect(() => {
    const savedToken = sessionStorage.getItem('cv_token') || localStorage.getItem('cv_token');

    if (savedToken) {
      fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${savedToken}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((userData: User | null) => {
          if (userData && userData.id) {
            setAuthToken(savedToken);
            setCurrentUser(userData);
          } else {
            handleLogout();
          }
        })
        .catch(() => handleLogout());
    }

    // Fetch system status
    fetch('/api/system-status')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setSystemStatus(data);
      })
      .catch((err) => console.warn('Status check notice:', err));
  }, []);

  // When Doctor is logged in, fetch registered patients for clinical assignment
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
    setSelectedFile(null);
    setPreviewUrl(null);
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

      alert(`Official diagnostic report certified and released to ${selectedPatient.name}'s medical record.`);
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

  // GATEKEEPER: If user is not authenticated, show the clinical Login/Sign-in portal
  if (!currentUser) {
    return <AuthScreen onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="app-root">
      {/* Institutional Top Navigation */}
      <Header
        systemStatus={systemStatus}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      {/* Main Workstation based on Authorized Role */}
      {currentUser.role === 'doctor' ? (
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
        /* PATIENT PORTAL: Viewing certified reports from chosen Attending Doctor */
        <main className="patient-container">
          <PatientPortal user={currentUser} token={authToken || ''} />
        </main>
      )}
    </div>
  );
}

export default App;
