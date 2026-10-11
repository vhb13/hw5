import type { Activity, ApproveResult, Cash, Draft, Ticket } from './types'

// The backend from Problem 7. Override with VITE_API_URL if it ever moves.
export const API_BASE: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(API_BASE + path, init)
  } catch {
    throw new ApiError(`Can't reach the backend at ${API_BASE}. Is it running?`, 0)
  }
  if (!res.ok) {
    let message = `The backend returned an error (${res.status}).`
    try {
      const body = await res.json()
      // Our routes send {detail: {error, message}}; FastAPI validation sends a list.
      if (typeof body?.detail?.message === 'string') message = body.detail.message
      else if (Array.isArray(body?.detail)) message = 'The request was not valid.'
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(message, res.status)
  }
  return res.json() as Promise<T>
}

const post = (body?: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
})

export const api = {
  tickets: () => request<Ticket[]>('/tickets'),
  cash: () => request<Cash>('/cash'),
  drafts: () => request<Draft[]>('/drafts'),
  activity: (limit = 200) => request<Activity>(`/activity?limit=${limit}`),
  runTicket: (id: number) => request<{ outcome: string; summary: string }>(`/tickets/${id}/run`, post()),
  approve: (proposalId: number, approvedBy: string) =>
    request<ApproveResult>(`/payments/${proposalId}/approve`, post({ approved_by: approvedBy })),
  resolve: (id: number) => request<{ ok: boolean }>(`/tickets/${id}/resolve`, post()),
  reset: () => request<{ ok: boolean }>('/reset', post()),
}
