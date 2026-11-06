// Run state and the run lifecycle.
//
// A Zustand store holds the latest result together with the identity of
// the request that produced it. Every request sent takes an id; only the
// newest request may write its outcome, so a late response can never
// overwrite newer state.

import { createStore } from 'zustand/vanilla'
import { buildRequest, requestIdentity, currentIdentity } from './requestIdentity.js'
import { getResultStatus } from './resultStatus.js'

export function createRunStore() {
  return createStore((set, get) => ({
    inputs: {},
    fidelity: 'foundational',
    result: null,
    resultIdentity: null,
    // 'validation' (nothing was sent) | 'run' (a request failed) | null
    lastFailure: null,
    failedIdentity: null,
    latestRequestId: 0,
    isRunning: false,
    error: null,

    setInput: (key, value) => set((s) => ({ inputs: { ...s.inputs, [key]: value } })),
    setFidelity: (fidelity) => set({ fidelity }),

    startRun: () => {
      const requestId = get().latestRequestId + 1
      set({ latestRequestId: requestId, isRunning: true, error: null, lastFailure: null })
      return requestId
    },
    completeRun: (requestId, result, identity) => {
      if (requestId !== get().latestRequestId) return false
      // A validation error stays while the inputs on screen are still invalid.
      const s = get()
      const keepValidationError = s.lastFailure === 'validation' && currentIdentity(s.inputs, s.fidelity) === null
      const clearError = keepValidationError ? {} : { error: null, lastFailure: null }
      set({ result, resultIdentity: identity, failedIdentity: null, isRunning: false, ...clearError })
      return true
    },
    failRun: (requestId, message, identity) => {
      if (requestId !== get().latestRequestId) return false
      set({ error: message, lastFailure: 'run', failedIdentity: identity, isRunning: false })
      return true
    },
    // Invalid inputs: nothing is sent, no request id is taken, and a request
    // already in flight is left alone.
    rejectInputs: (message) => set({ error: message, lastFailure: 'validation', failedIdentity: null }),
  }))
}

export function selectResultStatus(state) {
  return getResultStatus({
    result: state.result,
    resultIdentity: state.resultIdentity,
    currentIdentity: currentIdentity(state.inputs, state.fidelity),
    failedIdentity: state.failedIdentity,
  })
}

// One run, start to finish. `send` performs the HTTP request.
export async function runSimulation(store, send) {
  const { inputs, fidelity, startRun, completeRun, failRun, rejectInputs } = store.getState()
  let request
  try {
    request = buildRequest(inputs, fidelity)
  } catch (err) {
    rejectInputs(err.message)
    return
  }
  const requestId = startRun()
  const identity = requestIdentity(request)
  try {
    completeRun(requestId, await send(request), identity)
  } catch (err) {
    failRun(requestId, err.message, identity)
  }
}
