# pp2pgm-cigremv

Pandapower to [Power Grid Model](https://github.com/Alliander/power-grid-model) (PGM) conversion for CIGRE and other benchmark networks, plus helpers for state-estimation experiments (measurement Jacobian **H** and synthetic SE inputs).

## What this repo provides

- **`PandaPowerNetwork2PGM`** — Loads a named Pandapower case, uses `power-grid-model-io`’s `PandaPowerConverter`, and returns a PGM network object. IEEE 14-bus PV generators are converted to PQ before conversion.
- **`HMatrixGenerator`** — Builds a linearized measurement Jacobian **H** (voltage, line currents, transformer currents) from PGM `input_data` for SE-style analysis.
- **`SEInputMaker`** — Constructs PGM state-estimation inputs (measurements, noise, optional switch settings) for CIGRE MV/LV workflows; expects serialized PGM JSON on disk.


## Built-in network names

Pass these as `net_name` to `PandaPowerNetwork2PGM` (`modules/pp_2_pgm.py`):

| `net_name`    | Source                                                 |
| ------------- | ------------------------------------------------------ |
| `ieee14`      | `pandapower.networks.case14()` (PV→PQ replacement)     |
| `cigre_mv`    | `create_cigre_network_mv(with_der=False)`              |
| `cigre_lv`    | `create_cigre_network_lv()`                            |
| `mv_oberhein` | `mv_oberrhein("generation")` (Pandapower MV Oberrhein) |

## Requirements

- Python ≥ 3.12 (see `pyproject.toml`)
- [uv](https://github.com/astral-sh/uv) recommended, or install from `requirements.txt` with pip

## Installation

```bash
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
```

Optional dev tools (pytest, ruff):

```bash
uv sync --all-extras
```

Equivalent with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"   # if you use the project as an editable install with extras
```

## Usage

### Pandapower → PGM

```python
from modules.pp_2_pgm import PandaPowerNetwork2PGM

converter = PandaPowerNetwork2PGM(net_name="cigre_mv")
pgm_net = converter.to_pgm()
# converter.input_data / converter.extra_info are available after init (same as PandaPowerConverter.load_input_data)
```

### State-estimation experiments

- **`experiments/cigre_mv_conversion.ipynb`** — Full flow: load network, validate PGM input, serialize JSON, power flow.
- **`experiments/cigre_mv_se.ipynb`** — PF → synthetic measurements → PGM state estimation; uses `HMatrixGenerator` and `SEInputMaker`.

`SEInputMaker` reads `cigre_mv_in_pgm.json` or `cigre_lv_in_pgm.json` from the **current working directory**. The repo includes `experiments/cigre_mv_in_pgm.json`; run notebooks from `experiments/` or place the JSON files where your process cwd expects them. For CIGRE LV, export PGM JSON from the conversion notebook (or equivalent) to match the filename `cigre_lv_in_pgm.json`.

## Project layout

```
pp2pgm-cigremv/
├── modules/
│   ├── pp_2_pgm.py        # Pandapower → PGM loader/converter
│   ├── h_matrix_gen.py    # H-matrix generation
│   ├── se_input_maker.py  # SE measurement / input construction
│   └── utils.py           # IDs, indices, plotting helpers
├── experiments/           # Notebooks and example PGM JSON
├── pyproject.toml
├── requirements.txt
└── README.md
```

`pyproject.toml` configures pytest and Ruff for `modules/` and `tests/` when you add tests.
