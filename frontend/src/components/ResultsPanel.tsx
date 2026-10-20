import React from 'react';
import type { DiagnosticResult } from '../types';
import { WaveformCanvas } from './WaveformCanvas';

interface ResultsPanelProps {
  results: DiagnosticResult | null;
  onPrint: () => void;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({ results, onPrint }) => {
  if (!results) {
    return (
      <section className="panel results-panel">
        <div className="panel-header">
          <div className="panel-title">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3v18h18M9 9l3 3 5-5" />
            </svg>
            <h2>Diagnostic Intelligence</h2>
          </div>
        </div>

        <div className="empty-state">
          <div className="empty-illustration">
            <div className="pulse-ring" />
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h3>Awaiting ECG Input</h3>
          <p>
            Select a reference case on the left or upload an ECG image to generate a comprehensive
            cardiac evaluation.
          </p>
        </div>
      </section>
    );
  }

  const isAfib = results.is_afib;
  const afibProb = results.afib_percentage;
  const topPred = results.predictions && results.predictions[0] ? results.predictions[0] : null;

  // Gauge calculations (r = 50 -> circumference = 314.15)
  const circumference = 2 * Math.PI * 50;
  const offset = circumference - (afibProb / 100) * circumference;

  let gaugeColor = 'var(--emerald)';
  let gaugeStatus = 'Normal Rhythm Profile';
  if (afibProb >= 70) {
    gaugeColor = 'var(--crimson)';
    gaugeStatus = 'Severe Arrhythmia Risk';
  } else if (afibProb >= 40) {
    gaugeColor = 'var(--amber)';
    gaugeStatus = 'Borderline / Elevated';
  }

  return (
    <section className="panel results-panel">
      <div className="panel-header">
        <div className="panel-title">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 3v18h18M9 9l3 3 5-5" />
          </svg>
          <h2>Diagnostic Intelligence</h2>
        </div>
        <div className="header-actions">
          <button type="button" className="btn-outline" onClick={onPrint} title="Print or Export Diagnostic Report">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
              <path d="M6 14h12v8H6z" />
            </svg>
            Export Report
          </button>
        </div>
      </div>

      <div className="results-content">
        {/* Top Verdict Banner */}
        <div className={`verdict-banner ${isAfib ? 'verdict-afib' : 'verdict-normal'}`}>
          <div className="verdict-icon-container">
            {isAfib ? (
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3" />
              </svg>
            )}
          </div>
          <div className="verdict-details">
            <span className="verdict-eyebrow">DIAGNOSTIC VERDICT</span>
            <h3 className="verdict-title">{results.verdict}</h3>
            <p className="verdict-subtitle">
              {isAfib
                ? `High irregularity in atrial rhythm identified with ${afibProb}% AFib risk index.`
                : `Consistent sinus rhythm morphology and regular baseline electrophysiology observed.`}
            </p>
          </div>
          <div className={`verdict-badge ${isAfib ? 'badge-urgent' : 'badge-routine'}`}>
            {isAfib ? 'URGENT CLINICAL REVIEW' : 'PHYSIOLOGICAL SINUS'}
          </div>
        </div>

        {/* Metrics Row: AFib Risk Meter + Neural Assessment (NO Heart Rate) */}
        <div className="metrics-grid">
          {/* Circular Risk Gauge Card */}
          <div className="metric-card risk-card">
            <div className="card-title">AFib Risk Probability</div>
            <div className="gauge-container">
              <svg className="radial-gauge" viewBox="0 0 120 120">
                <circle className="gauge-bg" cx="60" cy="60" r="50" />
                <circle
                  className="gauge-fill"
                  cx="60"
                  cy="60"
                  r="50"
                  strokeDasharray="314.15"
                  strokeDashoffset={offset}
                  style={{ stroke: gaugeColor }}
                />
              </svg>
              <div className="gauge-center-text">
                <span className="gauge-value">{afibProb}%</span>
                <span className="gauge-label">AFIB INDEX</span>
              </div>
            </div>
            <div className="gauge-status" style={{ color: gaugeColor }}>
              {gaugeStatus}
            </div>
          </div>

          {/* Neural Diagnostic Findings Card (NO Heart Rate) */}
          <div className="metric-card telemetry-card">
            <div className="card-title">Diagnostic Findings</div>
            <div className="telemetry-items">
              <div className="telem-item">
                <div className="telem-icon">🔍</div>
                <div className="telem-info">
                  <span className="telem-value">
                    {topPred ? topPred.title : isAfib ? 'Atrial Fibrillation' : 'Normal Sinus Rhythm'}
                  </span>
                  <span className="telem-label">Primary Rhythm Pattern</span>
                </div>
              </div>

              <div className="telem-item">
                <div className="telem-icon">🎯</div>
                <div className="telem-info">
                  <span className="telem-value">{results.confidence}%</span>
                  <span className="telem-label">Diagnostic Confidence</span>
                </div>
              </div>

              <div className="telem-item">
                <div className="telem-icon">📈</div>
                <div className="telem-info">
                  <span className="telem-value">{isAfib ? 'Marked Irregularity' : 'Regular Periodic'}</span>
                  <span className="telem-label">Rhythm Regularity</span>
                </div>
              </div>

              <div className="telem-item">
                <div className="telem-icon">🛡️</div>
                <div className="telem-info">
                  <span
                    className="telem-value"
                    style={{ color: isAfib ? 'var(--crimson)' : 'var(--emerald)' }}
                  >
                    {isAfib ? 'High Priority' : 'Routine Baseline'}
                  </span>
                  <span className="telem-label">Triage Priority</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Multi-Condition Breakdown */}
        <div className="condition-section">
          <div className="section-heading">
            <h4>Cardiac Rhythm Multi-Class Probabilities</h4>
            <span className="engine-tag">DeepNet Core</span>
          </div>
          <div className="condition-bars">
            {(results.predictions || []).map((p) => (
              <div key={p.label} className="condition-item">
                <div className="condition-top">
                  <span className="condition-name">
                    <span className="condition-code">{p.label}</span>
                    <span>{p.title}</span>
                  </span>
                  <span className="condition-pct" style={{ color: p.color }}>
                    {p.percentage}%
                  </span>
                </div>
                <div className="progress-bar-bg">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${Math.max(2, p.percentage)}%`,
                      backgroundColor: p.color,
                    }}
                  />
                </div>
                <div className="condition-desc">{p.description}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Digitized Waveform Visualizer */}
        {results.telemetry?.waveform_preview && (
          <WaveformCanvas waveform={results.telemetry.waveform_preview} />
        )}

        {/* Clinical Disclaimer */}
        <div className="clinical-notice">
          <div className="notice-icon">📋</div>
          <div className="notice-text">
            <strong>Clinical Decision Support Notice:</strong> This AI system is engineered for rhythm screening
            and diagnostic assistance. Suspected arrhythmias or acute ischemic markers must be evaluated by
            qualified medical professionals in conjunction with complete 12-lead electrocardiography.
          </div>
        </div>
      </div>
    </section>
  );
};
