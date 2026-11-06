import { describe, expect, it } from 'vitest'
import { currentIdentity } from '../src/requestIdentity.js'
import { RESULT_STATUS } from '../src/resultStatus.js'
import { createRunStore, runSimulation, selectResultStatus } from '../src/runStore.js'

const INPUTS = {
  feed_mole_fraction: '0.3',
  distillate_mole_fraction: '0.6',
  bottoms_mole_fraction: '0.05',
  reflux_ratio: '2.0',
  feed_quality: '1.0',
  pressure_kpa: '101.3',
}

function storeWith(inputs = INPUTS) {
  const store = createRunStore()
  for (const [k, v] of Object.entries(inputs)) store.getState().setInput(k, v)
  return store
}
const status = (store) => selectResultStatus(store.getState())
const ok = async () => ({ stages: 8.29 })

// A send() whose responses the test resolves by hand, in any order.
function manualSend() {
  const pending = []
  const send = (request) => new Promise((resolve, reject) => pending.push({ request, resolve, reject }))
  return { send, pending }
}

describe('request identity', () => {
  it('treats equal numbers as the same run, whatever their text', () => {
    expect(currentIdentity({ ...INPUTS, distillate_mole_fraction: '0.60' }, 'foundational'))
      .toBe(currentIdentity(INPUTS, 'foundational'))
  })

  it('returns null for inputs that cannot form a request', () => {
    expect(currentIdentity({ ...INPUTS, reflux_ratio: '' }, 'foundational')).toBeNull()
    expect(currentIdentity({ ...INPUTS, reflux_ratio: '2abc' }, 'foundational')).toBeNull()
    expect(currentIdentity({ ...INPUTS, reflux_ratio: 'Infinity' }, 'foundational')).toBeNull()
  })
})

describe('result status', () => {
  it('is none before any run, current after one', async () => {
    const store = storeWith()
    expect(status(store)).toBe(RESULT_STATUS.NONE)
    await runSimulation(store, ok)
    expect(status(store)).toBe(RESULT_STATUS.CURRENT)
  })

  it('goes stale when an input changes, and current again when it is restored', async () => {
    const store = storeWith()
    await runSimulation(store, ok)
    store.getState().setInput('reflux_ratio', '2.5')
    expect(status(store)).toBe(RESULT_STATUS.STALE)
    store.getState().setInput('reflux_ratio', '2')
    expect(status(store)).toBe(RESULT_STATUS.CURRENT)
  })

  it('goes stale when the fidelity changes', async () => {
    const store = storeWith()
    await runSimulation(store, ok)
    store.getState().setFidelity('intermediate')
    expect(status(store)).toBe(RESULT_STATUS.STALE)
  })

  it('is never current while an input is blank', async () => {
    const store = storeWith()
    await runSimulation(store, ok)
    store.getState().setInput('pressure_kpa', '')
    expect(status(store)).toBe(RESULT_STATUS.STALE)
  })
})

describe('run lifecycle', () => {
  it('sends nothing and takes no request id when inputs are invalid', async () => {
    const store = storeWith({ ...INPUTS, feed_quality: 'abc' })
    let sent = 0
    await runSimulation(store, async () => { sent += 1 })
    expect(sent).toBe(0)
    expect(store.getState()).toMatchObject({ lastFailure: 'validation', latestRequestId: 0 })
  })

  it('reports last-run-failed only when the failed request had these exact inputs', async () => {
    const store = storeWith()
    await runSimulation(store, ok)
    await runSimulation(store, async () => { throw new Error('network down') })
    expect(status(store)).toBe(RESULT_STATUS.LAST_RUN_FAILED)
    expect(store.getState().result).toEqual({ stages: 8.29 }) // the earlier result is kept

    store.getState().setInput('reflux_ratio', '3')
    await runSimulation(store, async () => { throw new Error('network down') })
    store.getState().setInput('reflux_ratio', '2.0')
    expect(status(store)).toBe(RESULT_STATUS.CURRENT) // a failure of other inputs doesn't count
  })

  it('drops a late response from a superseded request', async () => {
    const store = storeWith()
    const { send, pending } = manualSend()
    const first = runSimulation(store, send)
    store.getState().setInput('reflux_ratio', '3')
    const second = runSimulation(store, send)

    pending[1].resolve({ stages: 5 }) // the newer request answers first
    await second
    pending[0].resolve({ stages: 8.29 }) // then the older one arrives late
    await first

    expect(store.getState().result).toEqual({ stages: 5 })
    expect(status(store)).toBe(RESULT_STATUS.CURRENT)
  })

  it('clears an input error when the request in flight completes', async () => {
    const store = storeWith()
    const { send, pending } = manualSend()
    const run = runSimulation(store, send)
    store.getState().setInput('reflux_ratio', 'abc')
    await runSimulation(store, send) // rejected: nothing sent, the first request stays in flight
    store.getState().setInput('reflux_ratio', '2.0')
    pending[0].resolve({ stages: 8.29 })
    await run
    expect(status(store)).toBe(RESULT_STATUS.CURRENT)
    expect(store.getState()).toMatchObject({ lastFailure: null, error: null })
  })

  it('keeps an input error while the inputs are still invalid when the request in flight completes', async () => {
    const store = storeWith()
    const { send, pending } = manualSend()
    const run = runSimulation(store, send)
    store.getState().setInput('reflux_ratio', 'abc')
    await runSimulation(store, send)
    pending[0].resolve({ stages: 8.29 })
    await run
    expect(status(store)).toBe(RESULT_STATUS.STALE)
    expect(store.getState()).toMatchObject({ lastFailure: 'validation', error: 'reflux_ratio must be a finite number' })
  })

  it('drops a late error from a superseded request', async () => {
    const store = storeWith()
    const { send, pending } = manualSend()
    const first = runSimulation(store, send)
    const second = runSimulation(store, send)
    pending[1].resolve({ stages: 8.29 })
    await second
    pending[0].reject(new Error('timeout'))
    await first
    expect(store.getState()).toMatchObject({ lastFailure: null, error: null, isRunning: false })
  })
})
