import React, { useState, useEffect } from 'react';
import type { User, ClinicalReport, DoctorOption } from '../types';
import { WaveformCanvas } from './WaveformCanvas';

interface PatientPortalProps {
  user: User;
  token: string;
}

export const PatientPortal: React.FC<PatientPortalProps> = ({ user, token }) => {
  const [reports, setReports] = useState<ClinicalReport[]>([]);
  const [availableDoctors, setAvailableDoctors] = useState<DoctorOption[]>([]);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>(
    user.doctor_id ? user.doctor_id.toString() : 'all'
  );
  const [selectedReport, setSelectedReport] = useState<ClinicalReport | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchReports = async (doctorFilterId?: string) => {
    setLoading(true);
    setError('');

    let url = '/api/patient/reports';
    if (doctorFilterId && doctorFilterId !== 'all') {
      url += `?doctor_id=${doctorFilterId}`;
    }

    try {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to retrieve clinical patient reports.');

      setReports(data.reports || []);
      setAvailableDoctors(data.available_doctors || []);

      if (data.reports && data.reports.length > 0) {
        setSelectedReport(data.reports[0]);
      } else {
        setSelectedReport(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error fetching clinical records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports(selectedDoctorId);
  }, [user.id, token, selectedDoctorId]);

  const handleDoctorFilterChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedDoctorId(val);
    if (val && val !== 'all') {
      try {
        await fetch('/api/patient/select-doctor', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ doctor_id: parseInt(val, 10) })
        });
      } catch {
        // non-blocking
      }
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="clinical-patient-portal">
      {/* Institutional Top Bar */}
      <div className="patient-hospital-header">
        <div className="patient-identity-block">
          <div className="patient-avatar-badge">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <div>
            <h2>Patient Diagnostic Record: {user.name}</h2>
            <div className="patient-submeta">
              <span>Record ID: {user.title || user.email}</span>
              <span>•</span>
              <span>Hospital ID: #{user.id.toString().padStart(6, '0')}</span>
            </div>
          </div>
        </div>

        {/* Which Doctor to Show Selector */}
        <div className="doctor-filter-container no-print">
          <label htmlFor="doctorSelectFilter">
            <span className="doctor-filter-label">Which Doctor to Show:</span>
          </label>
          <select
            id="doctorSelectFilter"
            className="clinical-select-sm"
            value={selectedDoctorId}
            onChange={handleDoctorFilterChange}
          >
            <option value="all">All Attending Doctors</option>
            {availableDoctors.map((doc) => (
              <option key={doc.id} value={doc.id.toString()}>
                {doc.name} {doc.license_number ? `(Lic: ${doc.license_number})` : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Clinical Advisory Notice */}
      <div className="clinical-info-banner no-print">
        <div className="banner-icon">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <div className="banner-text">
          <strong>Authorized Patient Access:</strong> You are viewing certified electrocardiographic diagnostic reports released to your medical record. Only your licensed attending physician can upload and evaluate raw clinical traces.
        </div>
      </div>

      {error && <div className="clinical-alert-error">{error}</div>}

      {loading ? (
        <div className="clinical-loading-box">
          <span className="spinner" />
          <p>Retrieving verified cardiac records from attending physician...</p>
        </div>
      ) : reports.length === 0 ? (
        <div className="clinical-empty-state">
          <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <h3>No Diagnostic Reports on File</h3>
          <p>
            There are currently no finalized ECG reports released by this physician.
            When your attending cardiologist completes an analysis and signs off on your rhythm strip, it will appear here.
          </p>
        </div>
      ) : (
        <div className="patient-reports-grid">
          {/* Historical Reports Timeline */}
          <div className="patient-reports-sidebar no-print">
            <div className="sidebar-header">
              <h3>Released Examinations ({reports.length})</h3>
            </div>
            <div className="report-items-list">
              {reports.map((rep) => {
                const isAfib = Boolean(rep.is_afib);
                const isSelected = selectedReport?.id === rep.id;
                return (
                  <div
                    key={rep.id}
                    className={`patient-report-item ${isSelected ? 'active' : ''}`}
                    onClick={() => setSelectedReport(rep)}
                  >
                    <div className="item-row">
                      <span className={`status-tag ${isAfib ? 'tag-afib' : 'tag-normal'}`}>
                        {isAfib ? 'AFib Positive' : 'Normal Sinus'}
                      </span>
                      <span className="item-date">
                        {new Date(rep.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric'
                        })}
                      </span>
                    </div>

                    <div className="item-physician">
                      <strong>{rep.doctor_name}</strong>
                      <small>{rep.doctor_title || 'Attending Cardiologist'}</small>
                    </div>

                    <div className="item-metrics">
                      <span>Confidence: <b>{rep.confidence?.toFixed(1) || '0.0'}%</b></span>
                      <span>AFib Score: <b>{rep.afib_percentage?.toFixed(1) || '0.0'}%</b></span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Institutional Detailed Examination Record */}
          {selectedReport && (
            <div className="clinical-report-sheet printable-report">
              <div className="sheet-top-header">
                <div>
                  <div className="sheet-institution">CardioVision Healthcare System</div>
                  <h1 className="sheet-title">Electrocardiographic Examination Record</h1>
                  <span className="sheet-department">Division of Cardiology & Electrophysiology</span>
                </div>
                <div className="sheet-actions no-print">
                  <button type="button" className="clinical-print-btn" onClick={handlePrint}>
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="6 9 6 2 18 2 18 9" />
                      <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                      <rect x="6" y="14" width="12" height="8" />
                    </svg>
                    Print Institutional Report (PDF)
                  </button>
                </div>
              </div>

              {/* Patient & Physician Institutional Record Header */}
              <div className="clinical-meta-table">
                <div className="meta-col">
                  <span className="col-label">Patient Name:</span>
                  <strong className="col-value">{selectedReport.patient_name}</strong>
                  <span className="col-sub">{user.title || user.email}</span>
                </div>
                <div className="meta-col">
                  <span className="col-label">Attending Physician:</span>
                  <strong className="col-value">{selectedReport.doctor_name}</strong>
                  <span className="col-sub">{selectedReport.doctor_title}</span>
                </div>
                <div className="meta-col">
                  <span className="col-label">Examination ID & Date:</span>
                  <strong className="col-value">ECG-{selectedReport.id.toString().padStart(6, '0')}</strong>
                  <span className="col-sub">{new Date(selectedReport.created_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Primary Diagnostic Finding Banner */}
              <div className={`clinical-verdict-box ${selectedReport.is_afib ? 'verdict-box-afib' : 'verdict-box-normal'}`}>
                <div className="verdict-box-title">
                  {selectedReport.is_afib ? 'CRITICAL FINDING: ATRIAL FIBRILLATION DETECTED' : 'DIAGNOSTIC FINDING: NORMAL SINUS RHYTHM'}
                </div>
                <div className="verdict-box-sub">
                  {selectedReport.is_afib
                    ? `Atrial Fibrillation probability assessed at ${selectedReport.afib_percentage.toFixed(1)}%. Differential pattern indicates absent discrete P waves with irregular QRS intervals.`
                    : `Normal physiological rhythm verified with uniform P-wave axis and regular conduction. AFib risk index is minimal (${selectedReport.afib_percentage.toFixed(1)}%).`}
                </div>
              </div>

              {/* Attending Physician's Clinical Review & Plan */}
              <div className="physician-review-section">
                <div className="review-card">
                  <h4 className="review-title">Attending Physician Clinical Notes</h4>
                  <p className="review-content">
                    {selectedReport.doctor_notes || 'Rhythm strip evaluated. Ventricular rate and morphological contours consistent with diagnostic reading.'}
                  </p>
                </div>

                <div className="review-card plan-card">
                  <h4 className="review-title">Clinical Management & Action Plan</h4>
                  <p className="review-content">
                    {selectedReport.clinical_recommendation || 'Continue routine medical therapy as prescribed. Maintain scheduled follow-up with attending cardiologist.'}
                  </p>
                </div>
              </div>

              {/* Digitized ECG Waveform Record */}
              {selectedReport.telemetry?.waveform_preview && (
                <div className="waveform-record-box">
                  <h4 className="section-header-title">Digitized Rhythm Strip & Pan-Tompkins Peak Alignment</h4>
                  <WaveformCanvas waveform={selectedReport.telemetry.waveform_preview} />
                  <div className="waveform-record-legend">
                    <span>Trace: Filtered Single-Lead Surface ECG</span>
                    <span>•</span>
                    <span>Sampling Frequency: {selectedReport.telemetry.sampling_rate || 250} Hz</span>
                    <span>•</span>
                    <span>Markers: Detected R-Wave QRS Peaks</span>
                  </div>
                </div>
              )}

              {/* Objective Electrophysiological Parameters Table */}
              <div className="telemetry-record-table">
                <h4 className="section-header-title">Objective Electrophysiological Parameters</h4>
                <table className="record-table">
                  <tbody>
                    <tr>
                      <th>Evaluated Beats</th>
                      <td>{selectedReport.telemetry?.n_beats || '--'} beats</td>
                      <th>RR Interval Variability (CV)</th>
                      <td>{selectedReport.telemetry?.rr_cv !== undefined && selectedReport.telemetry?.rr_cv !== null ? selectedReport.telemetry.rr_cv.toFixed(3) : '--'}</td>
                    </tr>
                    <tr>
                      <th>Recording Duration</th>
                      <td>{selectedReport.telemetry?.signal_duration_sec || 10.0} seconds</td>
                      <th>Evaluation Core</th>
                      <td>{selectedReport.engine || 'Vision Transformer (ViT)'}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Digital Certification Sign-Off Block */}
              <div className="report-signoff-row">
                <div className="signature-block">
                  <div className="signature-rule" />
                  <span className="signature-label">Certified Electrophysiology Sign-Off</span>
                  <strong className="signature-name">{selectedReport.doctor_name}</strong>
                  <span className="signature-title">{selectedReport.doctor_title}</span>
                </div>

                <div className="hospital-seal">
                  <div className="seal-border">
                    <span className="seal-text-top">CARDIOVISION CLINICAL</span>
                    <span className="seal-text-mid">VERIFIED RECORD</span>
                    <span className="seal-text-bot">OFFICIALLY RELEASED</span>
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
