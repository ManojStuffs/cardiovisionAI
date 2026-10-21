import React from 'react';
import type { DiagnosticResult } from '../types';
import { WaveformCanvas } from './WaveformCanvas';

interface ResultsPanelProps {
  results: DiagnosticResult | null;
  onPrint: () => void;
  seconds?: number;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({ results, onPrint, seconds = 10.0 }) => {
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
            <h2>Diagnostic Report</h2>
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
          <h3>Awaiting ECG Input</h3>
          <p>
            Upload a rhythm strip or paper ECG image on the left, then click <strong>Analyze ECG & Generate Report</strong> to produce a full clinical diagnostic evaluation.
          </p>
        </div>
      </section>
    );
  }

  const isAfib = results.is_afib;
  const afibProb = results.afib_percentage;
  const topPred = results.predictions && results.predictions[0] ? results.predictions[0] : null;

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
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            )}
          </div>
          <div className="verdict-details">
            <span className="verdict-eyebrow">DIAGNOSTIC VERDICT</span>
            <h3 className="verdict-title">{results.verdict}</h3>
            <p className="verdict-subtitle">
              {isAfib
                ? `Electrographic characteristics indicate high baseline irregularity and AFib risk index (${afibProb}%).`
                : `Electrophysiological waveform contours exhibit regular sinus rhythm morphology.`}
            </p>
          </div>
          <div className="verdict-badge-box">
            <span className={`verdict-badge ${isAfib ? 'badge-urgent' : 'badge-routine'}`}>
              {isAfib ? 'URGENT REVIEW' : 'PHYSIOLOGICAL SINUS'}
            </span>
          </div>
        </div>

        {/* Core Findings Grid */}
        <div className="metrics-grid">
          {/* AFib Probability Card */}
          <div className="metric-card">
            <div className="card-header-clean">
              <span className="card-title">AFib Risk Index</span>
              <span className={`risk-pill ${riskClass}`}>{riskLevel}</span>
            </div>
            <div className="score-display">
              <span className="score-num">{afibProb}%</span>
              <span className="score-label">Probability</span>
            </div>
            <div className="score-bar-track">
              <div
                className={`score-bar-fill ${riskClass}`}
                style={{ width: `${Math.min(100, Math.max(4, afibProb))}%` }}
              />
            </div>
            <div className="score-scale">
              <span>0% Normal</span>
              <span>40% Borderline</span>
              <span>100% High Risk</span>
            </div>
          </div>

          {/* Clinical Findings Card */}
          <div className="metric-card">
            <div className="card-header-clean">
              <span className="card-title">Diagnostic Assessment</span>
              <span className="confidence-pill">Confidence: {results.confidence}%</span>
            </div>
            <div className="findings-table">
              <div className="finding-row">
                <span className="f-label">Primary Pattern:</span>
                <span className="f-val">
                  {topPred ? topPred.title : isAfib ? 'Atrial Fibrillation' : 'Normal Sinus Rhythm'}
                </span>
              </div>
              <div className="finding-row">
                <span className="f-label">Rhythm Regularity:</span>
                <span className="f-val">
                  {isAfib ? 'Irregularly Irregular' : 'Regular Periodic'}
                </span>
              </div>
              <div className="finding-row">
                <span className="f-label">Clinical Triage:</span>
                <span className={`f-val ${isAfib ? 'text-urgent' : 'text-normal'}`}>
                  {isAfib ? 'Priority Clinical Review' : 'Routine Baseline Observation'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Multi-Condition Differential Table */}
        <div className="condition-section">
          <div className="section-heading">
            <h4>Cardiac Rhythm Differential Classification</h4>
            <span className="subhead-note">Normalized probabilities across multi-label classes</span>
          </div>
          <div className="condition-table-wrapper">
            <table className="condition-table">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Cardiac Condition</th>
                  <th>Probability</th>
                  <th>Distribution</th>
                  <th>Clinical Urgency</th>
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
            <strong>Clinical Decision Support Advisory:</strong> This automated interpretation is provided as diagnostic assistance for trained healthcare providers. It is not an autonomous diagnostic determination. Suspected arrhythmias or conduction disturbances must be corroborated with full 12-lead electrocardiography, patient symptoms, and expert clinical judgment.
          </div>
        </div>
      </div>
    </section>
  );
};
