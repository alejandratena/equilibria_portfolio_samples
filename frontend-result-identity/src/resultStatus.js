// Whether the result on screen still describes the inputs on screen.

export const RESULT_STATUS = Object.freeze({
  NONE: 'none', // no result yet
  CURRENT: 'current', // the result was produced by exactly these inputs
  STALE: 'stale', // the inputs changed (or are invalid) since the result was produced
  LAST_RUN_FAILED: 'last-run-failed', // same inputs, but the latest attempt to run them failed
})

export function getResultStatus({ result, resultIdentity, currentIdentity, failedIdentity }) {
  if (!result) return RESULT_STATUS.NONE
  if (currentIdentity === null || currentIdentity !== resultIdentity) return RESULT_STATUS.STALE
  // A failure of *other* inputs says nothing about this result.
  if (failedIdentity !== null && failedIdentity === currentIdentity) return RESULT_STATUS.LAST_RUN_FAILED
  return RESULT_STATUS.CURRENT
}
