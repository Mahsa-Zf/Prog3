# README

## Project: Vital Signs Time Series Analysis using VitalDB

This repository contains Python code and documentation for analyzing intraoperative vital sign signals using the open-access VitalDB dataset.

### Repository Structure
- `scripts/parser.py`: Handles downloading, loading, and cleaning of the data.
- `scripts/visualization.py`: Includes functions for plotting and inspecting time series signals.
- `scripts/analysis.py`: Contains logic for imputation, statistical summarization, and analysis.
- `logbook/logbook.ipynb`: Main notebook for step-by-step execution, combining all modules.
- `results`: Includes the plots created in the notebook
- `Report.md`: Summarizes findings and process.
- `README.md`: Project overview and usage instructions.
- `config.yaml`: Config file with data paths and configurable parameters


### How to Run
1. Clone this repo.
2. Create a virtual environment and install dependencies listed in `requirements.txt`.
**NOTE**: If you have access to the path listed in config.yaml, skip steps 3, 4.
3. To download the data, you can look for `4649.vital` in this [source](https://physionet.org/content/vitaldb/1.0.0/vital_files/#files-panel)
4. Create your own config.yaml based on where you store the file.
5. Execute the `logbook.ipynb` for full data pipeline and visualizations.


### Acknowledgments
We acknowledge the use of VitalDB and relevant academic publications.