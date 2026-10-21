import { useState, useEffect } from 'react';
import type { DiagnosticResult, SystemStatus } from './types';
import { Header } from './components/Header';
import { UploadPanel } from './components/UploadPanel';
import { ResultsPanel } from './components/ResultsPanel';

export function App() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState<string>('');
  const [seconds, setSeconds] = useState<number>(10.0);
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<DiagnosticResult | null>(null);

  // Fetch system status
  useEffect(() => {
    fetch('/api/system-status')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setSystemStatus(data);
      })
      .catch((err) => console.warn('Status check notice:', err));
  }, []);

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
    if (!selectedFile) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('seconds', seconds.toString());
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
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

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="app-root">
      {/* Institutional Clinical Header */}
      <Header systemStatus={systemStatus} />

      {/* Main Dual-Panel Clinical Layout */}
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
        />

        <ResultsPanel results={results} onPrint={handlePrint} seconds={seconds} />
      </main>
    </div>
  );
}

export default App;
