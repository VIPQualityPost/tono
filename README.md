[![Build](https://github.com/VIPQualityPost/tono/actions/workflows/build.yml/badge.svg)](https://github.com/VIPQualityPost/tono/actions/workflows/build.yml) [![Tests](https://github.com/VIPQualityPost/tono/actions/workflows/tests.yml/badge.svg)](https://github.com/VIPQualityPost/tono/actions/workflows/tests.yml)

# tono

<img src="resources/icon_1024.png" width="200">

tono is a node-based SPM image processing and analysis tool. The main focus is on topographical measurements.

It is heavily inspired by [Gwyddion](https://gwyddion.net/), one of my favorite scientific FOSS programs on the web.

<img src="frontend/public/default-workflow.png" width="800">

## Quick start
Install a local binary from the Releases section, or run locally: 

```bash
# Installation
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[server,dev]"
npm install

# Running the servers
npm run dev:all   # one terminal — starts the Python backend and the Vite dev server together
```

## Self-hosting

```bash
git clone https://github.com/VIPQualityPost/tono.git && cd tono
python -m venv .venv && source .venv/bin/activate
pip install -e ".[server]"
cd frontend && npm ci && npm run build && cd ..
TONO_HOST=0.0.0.0 python -m backend.main
```

See [Self-Hosting](docs/self-hosting.md) for reverse proxy setup, environment variables, and configuration.

## Python library

tono's processing nodes can also be used as a standalone Python library — no server needed:

```bash
pip install -e .
```

```python
import tono

fields = tono.load("scan.gwy")
leveled = tono.apply("PlaneLevelField", fields[0])
filtered = tono.apply("GaussianFilter", leveled, sigma=2.0)
```

See [Library Usage](docs/library.md) for the full API and more examples.

## Docs

- [Building](docs/building.md) — setup, dev mode, web deployment, and native desktop builds for macOS, Linux, and Windows
- [Self-Hosting](docs/self-hosting.md) — deploying tono on a server
- [Library Usage](docs/library.md) — using tono as a Python signal processing library
- [Plugins](docs/plugins.md) — writing and uploading custom node plugins
- [Testing](docs/testing.md) — running tests and writing new ones

## Project plans

- Please help with providing demo files for validating importers!
- Please try making weird workflows to see what breaks or does not flow nicely

- Adding support for force curves
- Adding general support for spectroscopic data
- Adding general support for spectroscopic volumes

- Adding more generic numerical operations and visualisations