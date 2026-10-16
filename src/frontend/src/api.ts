// Purpose: Share API requests. Local UI uses /api; hosted Pages talks to loopback.
import config from '../config.json';

/**
 * Resolve the orchestrator URL for a path like `/runs`.
 * Localhost keeps the same-origin `/api` proxy; hosted Pages uses loopback.
 */
export function apiUrl(path: string): string {
  const host = window.location.hostname;
  const local = host === 'localhost' || host === '127.0.0.1';
  return (local ? '/api' : config.localApiBase) + path;
}

function errorDetail(value: unknown, fallback: string): string {
  if (typeof value === 'object' && value !== null && 'detail' in value) {
    const detail = (value as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const timeout = AbortSignal.timeout(config.requestTimeoutSeconds * 1000);
  const response = await fetch(apiUrl(path), {
    ...options,
    signal: options?.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
  });
  if (!response.ok) {
    const fallback =
      response.status === 413 ? 'Request exceeds the size limit.' : 'Service unavailable.';
    const value: unknown = await response.json().catch(() => ({ detail: fallback }));
    throw new Error(errorDetail(value, 'Request failed.'));
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

export function jsonBody(value: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  };
}
