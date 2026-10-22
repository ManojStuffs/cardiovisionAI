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
  analyzing_doctor?: {
    name: string;
    title: string;
    license_number?: string;
  };
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

export interface User {
  id: number;
  name: string;
  email: string;
  role: 'doctor' | 'patient';
  title?: string;
  license_number?: string;
  doctor_id?: number | null;
}

export interface DoctorOption {
  id: number;
  name: string;
  email: string;
  title?: string;
  license_number?: string;
}

export interface PatientOption {
  id: number;
  name: string;
  email: string;
  title?: string;
  doctor_id?: number | null;
}

export interface ClinicalReport {
  id: number;
  patient_id: number;
  patient_name: string;
  patient_email: string;
  doctor_id: number;
  doctor_name: string;
  doctor_title: string;
  verdict: string;
  is_afib: boolean | number;
  afib_percentage: number;
  top_condition: string;
  confidence: number;
  engine: string;
  doctor_notes: string;
  clinical_recommendation: string;
  telemetry?: TelemetryData;
  predictions?: PredictionCondition[];
  image_preview_url?: string;
  created_at: string;
}
