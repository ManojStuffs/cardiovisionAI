export interface PredictionCondition {
  label: string;
  title: string;
  score: number;
  percentage: number;
  urgency: 'URGENT' | 'Moderate' | 'Routine' | string;
  color: string;
  description: string;
}

export interface WaveformPreview {
  times: number[];
  values: number[];
  peak_indices: number[];
}

export interface TelemetryData {
  rr_cv?: number | null;
  n_beats?: number;
  sampling_rate?: number;
  signal_duration_sec?: number;
  waveform_preview?: WaveformPreview | null;
}

export interface DiagnosticResult {
  status: string;
  model_name: string;
  engine: string;
  top_condition: string;
  is_afib: boolean;
  afib_probability: number;
  afib_percentage: number;
  verdict: string;
  confidence: number;
  predictions: PredictionCondition[];
  telemetry?: TelemetryData;
}

export interface SampleItem {
  filename: string;
  display_name: string;
  label: string;
  is_afib: boolean;
  url: string;
}

export interface SystemStatus {
  status: string;
  model_name: string;
  architecture: string;
  torch_available: boolean;
  backend: string;
}
