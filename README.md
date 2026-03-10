# pp2pgm-cigremv

Pandapower to Power Grid Model conversion for CIGRE MV and other benchmark networks.

## Overview

This project converts [Pandapower](https://www.pandapower.org/) networks into [Power Grid Model](https://github.com/Alliander/power-grid-model) (PGM) input data and provides utilities for building the measurement Jacobian (H matrix) used in state estimation.

Supported networks include:

- IEEE 14-bus
- CIGRE MV (with or without DER)
- CIGRE LV
- MV Oberrhein

## Requirements

- Python ≥3.12
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

Create a virtual environment and install dependencies with uv:

```bash
uv venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
uv sync
```

To include dev dependencies (pytest, ruff):

```bash
uv sync --all-extras
```

## Usage

Convert a Pandapower network to PGM and run power flow:

```python
from modules.pp_2_pgm import PandaPowerNetwork2PGM

converter = PandaPowerNetwork2PGM(net_name="cigre_mv")
pgm_net = converter.to_pgm()
```

See `experiments/cigre_mv_conversion.ipynb` for a full workflow.

## Project layout

```
pp2pgm-cigremv/
├── modules/           # Source package (Pandapower→PGM, H-matrix)
├── experiments/       # Jupyter notebooks
├── tests/             # Pytest tests
├── pyproject.toml
└── README.md
```

