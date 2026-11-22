# Luxious 💡

**Real-Room Illuminance Survey, Spatial Reconstruction & Photometric Analysis**

Luxious is a precision engineering desktop application designed for physical lighting audits, spatial illuminance field reconstruction, and EN 12464 compliance verification.

---

## 🌟 Key Features

- **2D Illuminance Field Reconstruction**: Reconstruct continuous 2D illuminance maps and isolux contour lines from physical grid readings using SciPy spatial algorithms (Linear, Cubic Spline, Thin-Plate RBF).
- **Interactive Measurement Survey Workflow**: Fast walkthrough data entry with consecutive top-to-bottom serpentine traversal and in-place point editing tags.
- **Custom Sensor Placement & Symmetry Assist**: Interactive placement mode with real-world room dimension guides and automatic symmetry snapping assist (room centerlines & mirror axes).
- **Photometric KPI Analytics**: Real-time computation of average illuminance ($E_{\text{avg}}$), minimum ($E_{\text{min}}$), maximum ($E_{\text{max}}$), and uniformity ratios ($U_0 = E_{\text{min}} / E_{\text{avg}}$, $U_1 = E_{\text{min}} / E_{\text{max}}$).
- **Multi-Language Support**: Full runtime localization in **English (EN)**, **Romanian (RO)**, and **German (DE)**.
- **Reporting & Export**: Export high-resolution map images (PNG/PDF), CSV measurement schedules, and comprehensive PDF audit reports.
- **Multi-Level Undo/Redo**: Full state history for all edits, measurements, additions, and deletions (`Ctrl+Z`, `Ctrl+Y`, `Ctrl+X`).

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Dependencies: `PySide6`, `numpy`, `scipy`, `matplotlib`, `reportlab`

### Installation

```bash
git clone https://github.com/Deppner-Hanelore/Luxious.git
cd Luxious
pip install -r requirements.txt
```

*(Or install core dependencies directly)*:
```bash
pip install PySide6 numpy scipy matplotlib reportlab pytest
```

### Running the Application

```bash
python main.py
```

### Running Automated Tests

```bash
python -m pytest -v tests/
```

---

## Development Skills

Project-local agent skills for planning, architecture, Python, interfaces, APIs,
and agent pipelines are documented in [the skill catalog](docs/skills.md).
See [AGENTS.md](AGENTS.md) for project-specific usage and verification guidance.

## 📄 License
This project is open source and available under the [MIT License](LICENSE).
