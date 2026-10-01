import type { Alert, ComfortResponse, Observation } from '@/types/domain';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000').replace(
  /\/$/,
  '',
);

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
  }
}

async function request<T>(path: string): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      throw new ApiError(`Le serveur a répondu avec le statut ${response.status}.`, response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('Impossible de joindre le backend GRIDD.');
  }
}

export const api = {
  getLatestObservations: () => request<Observation[]>('/api/observations/latest'),
  getObservations: () => request<Observation[]>('/api/observations'),
  getComfort: () => request<ComfortResponse>('/api/comfort'),
  getAlerts: (status: 'active' | 'history' | 'all') =>
    request<Alert[]>(`/api/alerts?status=${status}`),
};
