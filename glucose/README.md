# Glucose Data Analysis Project

This project provides scripts for loading, preprocessing, analyzing, and visualizing glucose data. The goal is to process glucose readings, interpolate missing values, smooth the data, and generate plots for analysis.

## Project Structure

The project consists of the following files:

### 1. `parser.py`
**Purpose:** Loads, cleans, and preprocesses the glucose dataset.

**Main Functions:**
- `load_data(filename)`: Loads the dataset from a configuration file (`config.yaml`).
- `preprocess(df)`: Converts timestamps and removes duplicate rows from the dataset.

**Usage:**
```python
from parser import load_data, preprocess

df = load_data("glucose_data")
df_clean = preprocess(df)
```

### 2. `analysis.py`
**Purpose:** Provides functions to interpolate missing values and visualize glucose data.

**Main Functions:**
- `interpolator(df, start, end)`: Linearly interpolates missing values between a given date range.
- `glucose_smoother_plotter(df, start, end, window_size, original=True)`: Smooths glucose data using a rolling mean and plots it.

**Usage:**
```python
from analysis import interpolator, glucose_smoother_plotter

# Interpolate missing values
df = interpolator(df, "2024-01-01", "2024-01-07")

# Smooth and plot data
glucose_smoother_plotter(df, "2024-01-01", "2024-01-07", window_size=5)
```

### 3. `logbook.ipynb`
**Purpose:** Jupyter Notebook used for exploratory data analysis (EDA), testing functions, and visualizing trends.

**Usage:**
Run the notebook in Jupyter to interactively process and visualize glucose data:
```sh
jupyter notebook logbook.ipynb
```

## Requirements
This project requires the following Python libraries:
```sh
pip install pandas numpy matplotlib pyyaml
```

## How to Run
1. Ensure you have `config.yaml` in the project directory with correct dataset paths.
2. Load and preprocess the data using `parser.py`.
3. Use `analysis.py` to interpolate and visualize glucose data.
4. Explore results in `logbook.ipynb`.

## License
This project is licensed under the MIT License.

