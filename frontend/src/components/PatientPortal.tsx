import React, { useState, useEffect } from 'react';
import type { User, ClinicalReport } from '../types';
import { WaveformCanvas } from './WaveformCanvas';

interface PatientPortalProps {
  user: User;
  token: string;
}

export const PatientPortal: React.FC<PatientPortalProps> = ({ user, token }) => {
  const [reports, setReports] = useState<ClinicalReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedReport, setSelectedReport] = useState<ClinicalReport | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/patient/reports', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to load patient reports.');

      setReports(data.reports || []);
      if (data.reports && data.reports.length > 0) {
        setSelectedReport(data.reports[0]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error fetching reports.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [user.id, token]);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="patient-portal">
      {/* Patient Welcome Banner */}
      <div className="patient-banner">
        <div className="patient-banner-content">
          <div className="patient-avatar">👤</div>
          <div>
            <h2>Welcome to Your Cardiac Health Portal, {user.name}</h2>
            <p className="patient-banner-sub">
              {user.title || 'Verified Patient'} • Connected to Hospital Electrophysiology Network
            </p>
          </div>
        </div>
        <button className="refresh-reports-btn" onClick={fetchReports} disabled={loading}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          {loading ? 'Refreshing...' : 'Refresh Records'}
        </button>
      </div>

      {/* Role Notice */}
      <div className="patient-role-notice">
        <div className="notice-icon">🔒</div>
        <div className="notice-text">
          <strong>Patient Access Mode:</strong> Diagnostic ECG uploads and raw neural telemetry analyses are
          strictly restricted to your attending medical physicians. Only official reports verified and released by your
          doctor are displayed here.
        </div>
      </div>

      {error && <div className="auth-error-banner">{error}</div>}

      {loading ? (
        <div className="patient-loading">
          <div className="spinner" />
          <p>Retrieving your verified cardiac reports from your doctor...</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="patient-empty-state">
          <div className="empty-icon">📋</div>
          <h3>No Diagnostic Reports Released Yet</h3>
          <p>
            Your attending cardiologist has not published a finalized ECG diagnostic report for your account yet.
            Once your doctor completes the rhythm analysis and signs off, your report will appear here automatically.
          </p>
        </div>
      ) : (
        <div className="patient-reports-layout">
          {/* Reports History Sidebar */}
          <div className="patient-reports-list">
            <h3>Diagnostic History ({reports.length})</h3>
            <div className="report-cards-scroll">
              {reports.map((rep) => {
                const isAfib = Boolean(rep.is_afib);
                const isSelected = selectedReport?.id === rep.id;
                return (
                  <div
                    key={rep.id}
                    className={`patient-report-card ${isSelected ? 'selected' : ''} ${isAfib ? 'afib-card' : 'normal-card'}`}
                    onClick={() => setSelectedReport(rep)}
                  >
                    <div className="card-top">
                      <span className={`verdict-pill ${isAfib ? 'danger' : 'success'}`}>
                        {isAfib ? '🚨 AFib Detected' : '✅ Normal Sinus'}
                      </span>
                      <small className="report-date">
                        {new Date(rep.created_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        })}
                      </small>
                    </div>

                    <div className="card-doctor">
                      <strong>👨‍⚕️ {rep.doctor_name}</strong>
                      <small>{rep.doctor_title || 'Attending Physician'}</small>
                    </div>

                    <div className="card-metrics">
                      <span>Confidence: <b>{rep.confidence?.toFixed(1) || '0.0'}%</b></span>
                      <span>AFib Risk: <b>{rep.afib_percentage?.toFixed(1) || '0.0'}%</b></span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Detailed Selected Report View */}
          {selectedReport && (
            <div className="patient-report-detail printable-report">
              <div className="report-header-institutional">
                <div className="inst-brand">
                  <div className="inst-logo">🫀 CardioVision AI</div>
                  <div className="inst-sub">Official Cardiac Electrophysiology Report</div>
                </div>
                <div className="inst-actions no-print">
                  <button className="print-report-btn" onClick={handlePrint}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="6 9 6 2 18 2 18 9" />
                      <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                      <rect x="6" y="14" width="12" height="8" />
                    </svg>
                    Print / Download PDF
                  </button>
                </div>
              </div>

              {/* Patient and Doctor Metadata Bar */}
              <div className="report-meta-grid">
                <div className="meta-box">
                  <span className="meta-lbl">Patient Name</span>
                  <strong className="meta-val">{selectedReport.patient_name}</strong>
                  <span className="meta-sub">{user.title || user.email}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-lbl">Attending Physician</span>
                  <strong className="meta-val">{selectedReport.doctor_name}</strong>
                  <span className="meta-sub">{selectedReport.doctor_title}</span>
                </div>
                <div className="meta-box">
                  <span className="meta-lbl">Report ID & Date</span>
                  <strong className="meta-val">CV-RPT-#{selectedReport.id.toString().padStart(5, '0')}</strong>
                  <span className="meta-sub">{new Date(selectedReport.created_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Verdict Announcement */}
              <div className={`patient-verdict-banner ${selectedReport.is_afib ? 'danger' : 'success'}`}>
                <div className="verdict-icon">{selectedReport.is_afib ? '🚨' : '✅'}</div>
                <div>
                  <h3 className="verdict-title">{selectedReport.verdict}</h3>
                  <p className="verdict-desc">
                    {selectedReport.is_afib
                      ? `Atrial Fibrillation probability evaluated at ${selectedReport.afib_percentage.toFixed(1)}%. Primary arrhythmia classification: ${selectedReport.top_condition}.`
                      : `Normal physiological rhythm verified. Atrial Fibrillation risk minimal (${selectedReport.afib_percentage.toFixed(1)}%).`}
                  </p>
                </div>
              </div>

              {/* Doctor's Remarks and Clinical Recommendations */}
              <div className="doctor-remarks-section">
                <div className="doctor-notes-card">
                  <h4>
                    <span>👨‍⚕️</span> Attending Physician Clinical Observations
                  </h4>
                  <p className="doctor-notes-text">
                    {selectedReport.doctor_notes || 'Patient trace reviewed in clinic. R-peak variability and rhythm morphology consistent with diagnostic reading.'}
                  </p>
                </div>

                <div className="doctor-notes-card recommendation-card">
                  <h4>
                    <span>💊</span> Prescribed Clinical Plan & Recommendation
                  </h4>
                  <p className="doctor-notes-text">
                    {selectedReport.clinical_recommendation || 'Continue routine cardiac monitoring. Contact hospital if palpitations, shortness of breath, or dizziness occur.'}
                  </p>
                </div>
              </div>

              {/* Waveform Visualization if available */}
              {selectedReport.telemetry?.waveform_preview && (
                <div className="report-waveform-box">
                  <h4>Digitized Lead Waveform & QRS Alignment</h4>
                  <WaveformCanvas waveform={selectedReport.telemetry.waveform_preview} />
                  <div className="waveform-legend">
                    <span className="legend-item"><span className="legend-dot cyan" /> Filtered ECG Trace</span>
                    <span className="legend-item"><span className="legend-dot pink" /> Pan-Tompkins R-Peaks</span>
                  </div>
                </div>
              )}

              {/* Telemetry Summary Table */}
              <div className="patient-telemetry-table">
                <h4>Verified Rhythm Metrics</h4>
                <table>
                  <tbody>
                    <tr>
                      <td>Total Detected Beats</td>
                      <td><b>{selectedReport.telemetry?.n_beats || '--'} beats</b></td>
                      <td>RR Variability (CV)</td>
                      <td><b>{selectedReport.telemetry?.rr_cv !== undefined && selectedReport.telemetry?.rr_cv !== null ? selectedReport.telemetry.rr_cv.toFixed(3) : '--'}</b></td>
                    </tr>
                    <tr>
                      <td>Signal Duration</td>
                      <td><b>{selectedReport.telemetry?.signal_duration_sec || 10.0} s</b></td>
                      <td>Diagnostic Engine</td>
                      <td><b>{selectedReport.engine || 'CardioVision DeepNet ViT'}</b></td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="report-footer-signoff">
                <div className="signoff-signature">
                  <div className="signature-line" />
                  <p>Digitally Signed & Certified</p>
                  <strong>{selectedReport.doctor_name}</strong>
                  <small>{selectedReport.doctor_title}</small>
                </div>
                <div className="signoff-stamp">
                  <div className="stamp-box">
                    <span>OFFICIAL CLINICAL RECORD</span>
                    <small>VERIFIED BY CARDIOLOGY</small>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
