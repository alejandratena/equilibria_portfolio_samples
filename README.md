# Equilibria engineering samples

**Author:** Alejandra Tena · B.S. Chemical Engineering  
[LinkedIn](https://www.linkedin.com/in/alejandra-tena)

Equilibria is a process-simulation platform for chemical engineering. The application repositories are private. This repository contains three standalone samples adapted from the platform's engineering work, with tests and documented limitations.

| Sample | Scope | Technical focus |
|---|---|---|
| [Pipe-flow API](pipe-flow-api/) | Laminar pressure drop in a circular pipe, exposed through FastAPI | Physical assumptions, typed input, numerical error handling, model-applicability flags |
| [Frontend result identity](frontend-result-identity/) | Run state for a binary distillation simulation | Request identity, stale results, failed runs, out-of-order responses |
| [Testing and CI](testing-ci/) | Regression checks with a documented model defect | Strict expected failures, exception checking, CI enforcement |

Each directory contains its implementation, tests, execution instructions, and a description of what is excluded from the sample. Comparisons with the private application are described where available; the production code is not part of this repository.

## Run the tests

The samples are independent. GitHub Actions runs all three on pull requests and pushes to `main`, using Python 3.12 and Node.js 24.

```bash
(cd pipe-flow-api && pip install -r requirements.txt && python -m pytest -q)
(cd frontend-result-identity && npm ci && npm test)
(cd testing-ci && pip install -r requirements.txt && python -m pytest -q)
```

The [CI workflow](.github/workflows/ci.yml) also runs a separate known-failure verification step for the testing sample.
