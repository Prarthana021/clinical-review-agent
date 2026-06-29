export type CaseSummary = {
  id: string;
  patient_id: string;
  patient_name: string;
  review_year: number;
  submitted_diagnosis: string;
  title: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function fetchCases(): Promise<CaseSummary[]> {
  const response = await fetch(`${API_BASE_URL}/cases`);
  if (!response.ok) {
    throw new Error(`Failed to load cases: ${response.status}`);
  }
  return response.json();
}

export function apiBaseUrl(): string {
  return API_BASE_URL;
}
