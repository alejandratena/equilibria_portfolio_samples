// Builds the request a Run click would send, and its identity.
//
// The request is the client-side identity of a run: the model fidelity plus
// every numeric input. Layout, labels and selection are not part of it.

const FIELDS = [
  'feed_mole_fraction',
  'distillate_mole_fraction',
  'bottoms_mole_fraction',
  'reflux_ratio',
  'feed_quality',
  'pressure_kpa',
]

// Throws when the inputs cannot form a request. Only transport validity is
// checked here (present, numeric, finite); scientific ranges are the
// backend's job.
export function buildRequest(inputs, fidelity) {
  const spec = {}
  for (const key of FIELDS) {
    const raw = typeof inputs[key] === 'string' ? inputs[key].trim() : inputs[key]
    // Number(), not parseFloat(): "1abc" must be rejected, not read as 1.
    const value = raw === '' || raw == null ? NaN : Number(raw)
    if (!Number.isFinite(value)) throw new Error(`${key} must be a finite number`)
    spec[key] = value
  }
  return { fidelity, spec }
}

// Keys are always written in FIELDS order and values are numbers, so
// "0.6" and "0.60" give the same identity.
export function requestIdentity(request) {
  return JSON.stringify(request)
}

// Identity of what a Run click would send now, or null if nothing valid
// would be sent. A null identity never matches a result.
export function currentIdentity(inputs, fidelity) {
  try {
    return requestIdentity(buildRequest(inputs, fidelity))
  } catch {
    return null
  }
}
