import pandas as pd
import numpy as np
import yaml
from pathlib import Path

"""
python scripts that load, clean and reformat the data

"""

def load_data(filename):
    """
    Load a dataset based on a filename key from a configuration file.

    This function reads the `config.yaml` file located in the parent directory (`glucose/`),
    retrieves the corresponding file path from the "Data" section, and loads the dataset as a Pandas DataFrame.

    Parameters:
    -----------
    filename : str
        The key corresponding to the dataset's path in the "Data" section of `config.yaml`.

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing the loaded dataset.
    
    """
    # Get the absolute path to the 'glucose' directory
    base_dir = Path(__file__).resolve().parent.parent  # Moves up from 'scripts' to parent directory, 'glucose' here.

    # Construct the full path to config.yaml
    config_path = base_dir / "config.yaml"

    # Load the config file
    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)

    # Get the data path from config
    Data = config["Data"]
    path = Data[filename]

    # Load the data
    data = pd.read_csv(path)
    return data

def preprocess(df):
    """
        Preprocess a DataFrame by converting timestamps and removing duplicates.

        This function performs the following preprocessing steps:
        - Converts the 'Device Timestamp' column to a Pandas datetime object using the format "%d-%m-%Y %H:%M".
        - Removes duplicate rows from the DataFrame.

        Parameters:
        -----------
        df : pd.DataFrame
            The input DataFrame containing a 'Device Timestamp' column.

        Returns:
        --------
        pd.DataFrame
            The preprocessed DataFrame with formatted timestamps and no duplicate rows.
    """
    df['Device Timestamp'] = pd.to_datetime(df['Device Timestamp'], format="%d-%m-%Y %H:%M")
    # I want the duplicates to remain in the original df for analysis in logbook
    df_no_dup = df.drop_duplicates()
    return df_no_dup



if __name__ == "__main__":
    print(__doc__) #__doc__ is the docstring
else:
    print(f"Module {repr(__name__)} is imported successfully!")