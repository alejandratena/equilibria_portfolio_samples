"""Minimal HTTP API around laminar_pipe.solve.

Run:   uvicorn api:app --port 8001
Then:  curl -s localhost:8001/pipe/pressure-drop -H 'content-type: application/json' \
         -d @example_request.json

Invalid inputs (missing, zero, negative, non-finite or unknown fields, or a
value that is not a JSON number) are rejected with HTTP 422 before any
calculation runs. Inputs that are valid but make a derived quantity underflow
or overflow (diameter_m = 1e-100, say) also get a 422 rather than a server
error. That message names the affected quantities when they could be computed
(an infinite or zero result); when the arithmetic itself fails first, as D**4
underflowing to zero does, it reports only the arithmetic error.
"""

import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from laminar_pipe import NotRepresentable, PipeFlowRequest, PipeFlowResult, solve

app = FastAPI(title="Laminar pipe pressure drop (portfolio example)")


def _json_safe(value):
    """Replace NaN and infinities, which strict JSON cannot carry, with their string form."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


@app.exception_handler(RequestValidationError)
def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default handler echoes the rejected input back. Python's JSON parser accepts NaN,
    # Infinity and 1e400 (read as inf), and echoing those would make the error response itself
    # unserializable and turn a 422 into a 500.
    return JSONResponse(status_code=422, content={"detail": _json_safe(jsonable_encoder(exc.errors()))})


@app.exception_handler(NotRepresentable)
def not_representable(_: Request, exc: NotRepresentable) -> JSONResponse:
    # Same shape as FastAPI's own validation errors, so clients handle both alike.
    detail = [{"loc": ["body"], "msg": str(exc), "type": "not_representable"}]
    return JSONResponse(status_code=422, content={"detail": detail})


@app.post("/pipe/pressure-drop", response_model=PipeFlowResult)
def pressure_drop(request: PipeFlowRequest) -> PipeFlowResult:
    return solve(request)
