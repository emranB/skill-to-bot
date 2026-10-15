// Purpose: Share same-origin API requests and readable service errors.
import config from '../config.json';

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const timeout = AbortSignal.timeout(config.requestTimeoutSeconds * 1000);
  const response = await fetch('/api' + path, {
    ...options,
    signal: options?.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
  });
  if (!response.ok) {
    const fallback =
      response.status === 413 ? 'Request exceeds the size limit.' : 'Service unavailable.';
    const value = await response.json().catch(() => ({ detail: fallback }));
    throw new Error(typeof value?.detail === 'string' ? value.detail : 'Request failed.');
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function jsonBody(value: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(value),
  };
}
