import React, { useState, useEffect } from 'react';
import type { DiagnosticResult, PatientOption } from '../types';
import { WaveformCanvas } from './WaveformCanvas';

interface ResultsPanelProps {
  results: DiagnosticResult | null;
  onPrint: () => void;
  seconds?: number;
  selectedPatient?: PatientOption | null;
  onPublishReport?: (notes: string, recommendation: string) => Promise<boolean>;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({
  results,
  onPrint,
  seconds = 10.0,
  selectedPatient,
  onPublishReport,
}) => {
  const [doctorNotes, setDoctorNotes] = useState('');
  const [recommendation, setRecommendation] = useState('');
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState(false);

  // Initialize doctor observations based on results
  useEffect(() => {
    if (results) {
      setPublished(false);
      if (results.is_afib) {
        setDoctorNotes(
          `Electrocardiographic rhythm strip demonstrates irregular RR intervals with fibrillation waves (CV: ${results.telemetry?.rr_cv || 0.21}). Findings confirm Atrial Fibrillation.`
        );
        setRecommendation(
          `Initiate oral anticoagulation (NOAC) therapy pending CHA2DS2-VASc score. Recommend outpatient 24-48h Holter monitoring and comprehensive echocardiogram evaluation.`
        );
      } else {
        setDoctorNotes(
          `Normal sinus rhythm confirmed with uniform P-wave morphology and regular RR progression. No evidence of atrial fibrillation or ectopic rhythm.`
        );
        setRecommendation(
          `Continue standard routine cardiac care. Follow up in clinic in 6-12 months or sooner if cardiac symptoms recur.`
        );
      }
    }
  }, [results]);

  if (!results) {
    return (
      <section className="panel results-panel empty-container">
        <div className="panel-header">
          <div className="panel-title">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <h2>Diagnostic Evaluation & Clinical Report</h2>
          </div>
        </div>

        <div className="empty-state">
          <div className="empty-illustration">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <line x1="7" y1="12" x2="9" y2="12" />
              <line x1="11" y1="8" x2="13" y2="16" />
              <line x1="15" y1="10" x2="17" y2="14" />
            </svg>
          </div>
          <h3>Awaiting Doctor Analysis</h3>
          <p>
            Upload a rhythm strip or select a reference ECG on the left, then click{' '}
            <strong>Analyze ECG & Generate Report</strong> to inspect the side-by-side diagnostic findings and release
            the report to your patient.
          </p>
        </div>
      </section>
    );
  }

  const isAfib = results.is_afib;
  const afibProb = results.afib_percentage;

  // Determine risk category
  let riskLevel = 'Low Risk';
  let riskClass = 'risk-low';
  if (afibProb >= 70) {
    riskLevel = 'High Risk';
    riskClass = 'risk-high';
  } else if (afibProb >= 40) {
    riskLevel = 'Moderate / Borderline';
    riskClass = 'risk-mod';
  }

  const formattedDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const handlePublish = async () => {
    if (!onPublishReport) return;
    setPublishing(true);
    try {
      const ok = await onPublishReport(doctorNotes, recommendation);
      if (ok) setPublished(true);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <section className="panel results-panel report-mode">
      {/* Report Header Bar */}
      <div className="report-header">
        <div className="report-meta">
          <span className="report-tag">CLINICAL EVALUATION REPORT</span>
          <h2 className="report-title">Electrocardiographic Rhythm Analysis</h2>
          <div className="report-submeta">
            <span>Generated: {formattedDate}</span>
            <span>•</span>
            <span>Recording Window: {seconds.toFixed(1)}s</span>
            <span>•</span>
            <span>Engine: {results.engine || 'Vision Transformer (ViT)'}</span>
          </div>
        </div>
        <div className="report-actions">
          <button type="button" className="btn btn-outline print-btn" onClick={onPrint} title="Print or save as PDF">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
              <path d="M6 14h12v8H6z" />
            </svg>
            Export / Print Report
          </button>
        </div>
      </div>

      <div className="results-content">
        {/* Top Verdict Banner */}
        <div className={`verdict-banner ${isAfib ? 'verdict-afib' : 'verdict-normal'}`}>
          <div className="verdict-icon-container">
            {isAfib ? (
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2.2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            )}
          </div>
          <div className="verdict-text-block">
            <span className="verdict-label">PRIMARY CLINICAL DETERMINATION</span>
            <h3 className="verdict-headline">{results.verdict}</h3>
            <p className="verdict-detail">
              {isAfib
                ? `Significant electrophysiological irregularity detected with high-frequency fibrillatory activity and absence of distinct P-waves. Confidence: ${afibProb.toFixed(1)}%.`
                : `Normal cardiac conduction pattern identified with regular sinoatrial activation. Diagnostic probability of Atrial Fibrillation is minimal (${afibProb.toFixed(1)}%).`}
            </p>
          </div>
        </div>

        {/* Doctor Publish to Patient Card */}
        {onPublishReport && selectedPatient && (
          <div className="publish-report-card">
            <div className="publish-header">
              <div className="publish-title">
                <span className="publish-icon">📋</span>
                <div>
                  <h4>Certify & Release Report to Patient</h4>
                  <p>Assign this verified diagnosis to: <b>{selectedPatient.name}</b> ({selectedPatient.title || selectedPatient.email})</p>
                </div>
              </div>
              {published && (
                <span className="published-badge">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Released to Patient Portal
                </span>
              )}
            </div>

            <div className="publish-form">
              <div className="publish-field">
                <label>Doctor's Clinical Observations</label>
                <textarea
                  rows={2}
                  value={doctorNotes}
                  onChange={(e) => setDoctorNotes(e.target.value)}
                  placeholder="Enter physician observations..."
                />
              </div>

              <div className="publish-field">
                <label>Clinical Action / Prescription Recommendation</label>
                <textarea
                  rows={2}
                  value={recommendation}
                  onChange={(e) => setRecommendation(e.target.value)}
                  placeholder="Enter patient recommendations, medications, follow-up..."
                />
              </div>

              <button
                type="button"
                className="btn-publish-patient"
                disabled={publishing}
                onClick={handlePublish}
              >
                {publishing ? (
                  <span>Saving & Signing Report...</span>
                ) : published ? (
                  <span>✓ Update & Re-release Report to {selectedPatient.name}</span>
                ) : (
                  <span>Publish Report to {selectedPatient.name}'s Portal →</span>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Key Diagnostic Metrics Grid */}
        <div className="metrics-summary-grid">
          <div className="metric-cell">
            <span className="cell-label">AFib Probability</span>
            <span className={`cell-val ${isAfib ? 'text-danger' : 'text-success'}`}>
              {afibProb.toFixed(1)}%
            </span>
            <div className="clean-progress-track">
              <div
                className="clean-progress-fill"
                style={{
                  width: `${Math.max(2, afibProb)}%`,
                  backgroundColor: isAfib ? '#dc2626' : '#16a34a',
                }}
              />
            </div>
          </div>

          <div className="metric-cell">
            <span className="cell-label">Clinical Risk Tier</span>
            <span className={`cell-val badge-val ${riskClass}`}>
              {riskLevel}
            </span>
            <span className="cell-sub">Based on ViT & R-peak entropy</span>
          </div>

          <div className="metric-cell">
            <span className="cell-label">Detected R-Peaks</span>
            <span className="cell-val">
              {results.telemetry?.n_beats !== undefined ? `${results.telemetry.n_beats} beats` : '--'}
            </span>
            <span className="cell-sub">
              Sampling Rate: {results.telemetry?.sampling_rate || 250} Hz
            </span>
          </div>

          <div className="metric-cell">
            <span className="cell-label">RR Variability (CV)</span>
            <span className="cell-val">
              {results.telemetry?.rr_cv !== undefined && results.telemetry?.rr_cv !== null
                ? results.telemetry.rr_cv.toFixed(3)
                : '--'}
            </span>
            <span className="cell-sub">
              {results.telemetry?.rr_cv && results.telemetry.rr_cv > 0.15 ? 'Irregular (High CV)' : 'Regular (Normal CV)'}
            </span>
          </div>
        </div>

        {/* Comprehensive Multilabel Arrhythmia Spectrum Table */}
        <div className="section-block">
          <div className="section-title-bar">
            <h4>Arrhythmia Multi-Label Differential</h4>
            <span className="section-badge">Vision Transformer (ViT)</span>
          </div>

          <div className="table-responsive">
            <table className="clinical-table">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Clinical Condition</th>
                  <th>Probability</th>
                  <th style={{ width: '35%' }}>Distribution</th>
                  <th>Urgency</th>
                </tr>
              </thead>
              <tbody>
                {(results.predictions || []).map((p) => {
                  let badgeUrgency = 'badge-routine';
                  if (p.urgency === 'URGENT') badgeUrgency = 'badge-urgent';
                  else if (p.urgency === 'Moderate') badgeUrgency = 'badge-moderate';

                  return (
                    <tr key={p.label}>
                      <td className="code-col">
                        <code>{p.label}</code>
                      </td>
                      <td className="name-col">
                        <span className="cond-title">{p.title}</span>
                        <span className="cond-desc">{p.description}</span>
                      </td>
                      <td className="pct-col">
                        <strong>{p.percentage}%</strong>
                      </td>
                      <td className="bar-col">
                        <div className="clean-progress-track">
                          <div
                            className="clean-progress-fill"
                            style={{
                              width: `${Math.max(2, p.percentage)}%`,
                              backgroundColor: p.label === 'AFIB' ? '#dc2626' : p.label === 'NORM' ? '#16a34a' : '#475569',
                            }}
                          />
                        </div>
                      </td>
                      <td className="urgency-col">
                        <span className={`urgency-badge ${badgeUrgency}`}>
                          {p.urgency}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Digitized Waveform Visualizer on Calibrated Paper */}
        {results.telemetry?.waveform_preview && (
          <WaveformCanvas waveform={results.telemetry.waveform_preview} />
        )}

        {/* Formal Medical Advisory Notice */}
        <div className="clinical-notice">
          <div className="notice-icon">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div className="notice-text">
            <strong>Clinical Decision Support Advisory:</strong> This automated interpretation is provided as diagnostic assistance for licensed healthcare providers. Suspected arrhythmias or conduction disturbances must be corroborated with patient symptoms and expert clinical judgment.
          </div>
        </div>
      </div>
    </section>
  );
};
