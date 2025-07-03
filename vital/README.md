# Vital Signs Analysis Toolkit

This project provides a modular, extensible Python framework for loading, preprocessing, analyzing, and visualizing intraoperative vital signs data, with support for the open-access **VitalDB** dataset.

---

## 📦 Modules Overview

### 1. `parser.py`: Data Loading and Preprocessing
- Load data from `vital` files using paths from `config.yaml`.
- Handle missing data using interpolation, EWMA, and smoothing.
- Detect and remove physiological and statistical outliers.
- Analyze data quality and consecutive NaN segments.
- Provides convenience functions like `load_data()`, `data_info()`, and `preprocess_vital_signs()`.

### 2. `analysis.py`: Statistical and Clinical Signal Analysis
- Window-based signal segmentation and statistical feature extraction (mean, IQR, skew, etc.).
- Cross-signal analysis: calculates correlations, pulse pressure, and rate-pressure product.
- Clinical risk tagging (low, normal, high) for PP and RPP.
- Central class: `VitalSignsAnalyzer`.
- Configuration managed via `AnalysisConfig`.

### 3. `visualization.py`: Static and Interactive Plotting
- Static plots using Matplotlib.
- Interactive plots using Bokeh + Panel.
- Visual styling for signals and events.
- Dashboard generation with `VisualizationManager`.
- Functions: `static_plot_vitals()` and `create_dynamic_time_series_plot()`.

---

## 📁 Directory Structure

```
.
├── parser.py
├── analysis.py
├── visualization.py
├── __init__.py
├── config.yaml
├── logbook/
│   └── logbook.ipynb      # Full pipeline walkthrough
├── results/               # Auto-generated plots
├── README.md              # This file
├── Report.md              # Summary of findings
└── requirements.txt       # Dependencies
```

---

## 🚀 Getting Started

### 1. Set up environment
```bash
git clone <repo-url>
cd <project-folder>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Load and explore data
Update `config.yaml` with the absolute path to your `.vital` file.

```python
from scripts.parser import load_data, data_info, preprocess_vital_signs
df = load_data("4649")  # assuming '4649' maps to your file in config
data_info(df)
```

### 3. Preprocess and analyze
```python
from scripts.analysis import analyze_vital_signs
preprocessed, nan_info = preprocess_vital_signs(df["Solar8000/HR"], "hr")
styled_results = analyze_vital_signs(df, start_time="00:00:00", end_time="01:00:00")
```

### 4. Visualize
```python
from scripts.visualization import static_plot_vitals, create_dynamic_time_series_plot
static_plot_vitals(df)
create_dynamic_time_series_plot(df, "Solar8000/HR")
```

---

## 📖 Acknowledgments

This toolkit builds on the VitalDB dataset, developed by Seoul National University Hospital. 
- VitalDB: https://physionet.org/content/vitaldb/

---

## 🧪 Note

This package is designed for **exploratory physiological signal analysis** in a surgical context, with support for time-windowed statistical summaries and clinical interpretation heuristics.
