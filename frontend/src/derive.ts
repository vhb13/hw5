import type { Activity, AgentMessage, Step } from './types'

const t = (iso: string) => Date.parse(iso)

/** Time of the last "reset" marker the backend wrote, or 0 if none is in the window. */
export function lastResetTime(activity: Activity | null): number {
  if (!activity) return 0
  const resets = activity.steps.filter((s) => s.tool === 'reset')
  return resets.length ? t(resets[resets.length - 1].time) : 0
}

export interface RunView {
  steps: Step[] // what the agents did, oldest first
  messages: AgentMessage[] // what each agent said when it finished, oldest first
  hasRun: boolean
}

/**
 * The activity that belongs to the current (or latest) run of one ticket.
 * While a run is going, that is everything since it started. Afterwards it is
 * everything after the previous run's Boss message. Anything from before the last
 * database reset is ignored, so a reset really does start clean.
 */
export function runView(activity: Activity | null, ticketId: number, runStartedAt: number | null): RunView {
  if (!activity) return { steps: [], messages: [], hasRun: false }
  const reset = lastResetTime(activity)
  const steps = activity.steps.filter((s) => s.ticket_id === ticketId && t(s.time) >= reset)
  const messages = activity.messages.filter((m) => m.ticket_id === ticketId && t(m.time) >= reset)

  let from: number
  if (runStartedAt !== null) {
    from = runStartedAt - 2000 // clocks are on the same machine; allow a little slack
  } else {
    const boss = messages.filter((m) => m.agent === 'boss')
    from = boss.length >= 2 ? t(boss[boss.length - 2].time) : 0
  }
  const inRun = (iso: string) => (from === 0 ? true : runStartedAt !== null ? t(iso) >= from : t(iso) > from)
  const runSteps = steps.filter((s) => inRun(s.time))
  const runMessages = messages.filter((m) => inRun(m.time))
  return { steps: runSteps, messages: runMessages, hasRun: runSteps.length > 0 || runMessages.length > 0 }
}

export type AgentState = 'waiting' | 'working' | 'done' | 'not_needed' | 'error'

/** Where each agent is in the run, derived from the audit steps. */
export function agentStates(view: RunView, running: boolean): Record<string, AgentState> {
  const out: Record<string, AgentState> = {}
  for (const name of ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']) {
    const mine = view.steps.filter((s) => s.agent === name)
    const last = mine[mine.length - 1]
    if (!last) out[name] = running ? 'waiting' : view.hasRun ? 'not_needed' : 'waiting'
    else if (last.status === 'error') out[name] = 'error'
    else if (last.status === 'finished' || last.status === 'needs_human_approval') out[name] = 'done'
    else out[name] = running ? 'working' : 'done'
  }
  return out
}
