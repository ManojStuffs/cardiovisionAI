# CardioVision AI — React + TypeScript Frontend

Clinical Atrial Fibrillation and cardiac arrhythmia diagnostic interface built with **React**, **TypeScript**, and **Vite**.

## Architecture & Layout

- **`src/types/index.ts`**: TypeScript definitions for diagnostic results, telemetry, and system status.
- **`src/components/Header.tsx`**: Clinical brand bar with real-time status chips and animated oscilloscope.
- **`src/components/Oscilloscope.tsx`**: Canvas-rendered continuous ECG monitor sweep.
- **`src/components/UploadPanel.tsx`**: Drag & drop ECG image uploader with preview and reference case selector.
- **`src/components/ResultsPanel.tsx`**: Verdict banner, AFib risk probability gauge, diagnostic findings, and condition bars.
- **`src/components/WaveformCanvas.tsx`**: Digitized ECG trace on calibrated medical grid.
- **`src/index.css`**: Design system tokens (glassmorphism, cyber-medical color palette).

## Running the Frontend

```bash
npm install
npm run dev
```

Runs the development server at [http://localhost:3000](http://localhost:3000) and proxies `/api` requests to the backend server at `http://127.0.0.1:5000`.

## Production Build

```bash
npm run build
```
