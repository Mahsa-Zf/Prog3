import pandas as pd
import numpy as np
import yaml
from pathlib import Path
import vitaldb
from datetime import datetime

"""
python scripts that load, clean and reformat the data
This module provides functions to load and preprocess vital signs data from a YAML configuration file.
The main functions include:
- load_data: loads the data from the config.yaml file
- data_info: prints the data information
- _detect_outliers_iqr: detects outliers using the IQR method, used in preprocess_vital_signs
- preprocess_vital_signs: preprocess the vital signs data

"""

def load_data(filename, get_track_names=False):
    """
    Load a dataset based on a filename key from a configuration file.

    This function reads the `config.yaml` file located in the parent directory,
    retrieves the corresponding file path from the "Data" section, and loads the dataset as a Pandas DataFrame.
    Then formats the data by setting a time index and converting the data types of the columns.

    Parameters:
    -----------
    filename : str
        The key corresponding to the dataset's path in the "Data" section of `config.yaml`.
    get_track_names : bool, optional
        If True, returns the track names along with the DataFrame. Default is False.

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing the loaded dataset.
    
    """
    track_names = None
    # Get the absolute path to the parent folder directory
    base_dir = Path(__file__).resolve().parent.parent  # Moves up from 'scripts' to parent directory.

    # Construct the full path to config.yaml
    config_path = base_dir / "config.yaml"

    # Load the config file
    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)

    # Get the data path from config
    Data = config["Data"]
    path = Data[filename]

    # Load the data
    vf = vitaldb.VitalFile(path)
    # Selected Tracks:

    # Heart Rate (HR) and Blood Pressure (BP) These vital signs are clinically correlated:

    #Heart Rate: Available as 'Solar8000/HR'.

    #Blood Pressure: Available as 'Solar8000/ART_SBP' (systolic) and 'Solar8000/ART_DBP' (diastolic).

    # EVENT, contains the phases of the surgery

    selected_tracks = ['Solar8000/ART_SBP', 'Solar8000/ART_DBP', 'Solar8000/HR','EVENT']
        
    # for solar8000 devices the Acquisition interval (sec) is 2.
    df = vf.to_pandas(selected_tracks, interval=2)

    # Create a time index, indicating the time stamps of each data point
    # The start time can be set to any datetime format
    timefreq = pd.date_range(start= datetime.today().date(), periods = df.shape[0], freq='2s')
    df.set_index(timefreq.time, inplace=True)

    # Cast the float data type to columns other than EVENT
    for col in df.columns:
        if col != 'EVENT':
            df[col] = df[col].astype(float)

    # Get track names if requested
    if get_track_names:
        track_names = vf.get_track_names()
        return df, track_names
    else:
        return df

def data_info(df):
    """
    Prints information about the DataFrame, including duplicate indices, duplicate rows, and NaN values.

        Parameters:
        -----------
        df : pd.DataFrame
            The input DataFrame containing a 'Device Timestamp' column.

        Returns:
        --------
            prints the number of duplicate indices, duplicate rows, and NaN values in the DataFrame.
            along with the DataFrame info.
    """

    # Count duplicate indices
    num_duplicates = df.index.duplicated(keep='first').sum()
    print(f"Number of duplicate indices: {num_duplicates}")

    # If you want to count duplicate ROWS (all columns)
    num_duplicate_rows = df.duplicated(keep='first').sum()
    print(f"Number of duplicate rows: {num_duplicate_rows}")


    # Find the number of NaN values in the DataFrame
    # Exclude the 'EVENT' column from the NaN count
    nan_count = df.loc[:, df.columns != 'EVENT'].isna().sum().sum()
    print(f"Number of NaN values in the DataFrame: {nan_count}\n")
    
    df.info()


def _detect_outliers_iqr(data_series, auto_adjust=True):
    """
    Identifies outliers using the IQR method with adaptive multipliers based on skewness (no transformation).

    Parameters:
    ----------
        data_series (pd.Series or np.array): Input data
        auto_adjust (bool): Adjust lower/upper multipliers based on skewness

    Returns:
    ----------
        pd.Series: Boolean mask where True = outlier
    """
    import numpy as np
    import pandas as pd

    if not isinstance(data_series, pd.Series):
        data_series = pd.Series(data_series)


    # Calculate skewness
    skew = data_series.skew()
    
    # Determine multipliers
    # By increasing the multiplier on the side with the longer tail for skewed data
    # the code avoids flagging too many natural values as outliers.
    # The values 1.5, 2.0 and 2.5 are common choices for skewed data.
    if auto_adjust:
        if -0.5 <= skew <= 0.5:
            lower_mult, upper_mult = 1.5, 1.5
        elif 0.5 < skew <= 1.0:
            lower_mult, upper_mult = 1.5, 2.0
        elif skew > 1.0:
            lower_mult, upper_mult = 1.5, 2.5
        elif -1.0 <= skew < -0.5:
            lower_mult, upper_mult = 2.0, 1.5
        elif skew < -1.0:
            lower_mult, upper_mult = 2.5, 1.5
        print(f"Skewness: {skew:.4f} → Lower Mult: {lower_mult}, Upper Mult: {upper_mult}")
    else:
        lower_mult = upper_mult = 1.5

    # IQR calculation
    q1 = data_series.quantile(0.25)
    q3 = data_series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - lower_mult * iqr
    upper = q3 + upper_mult * iqr

    # Find outliers
    outliers = (data_series < lower) | (data_series > upper)

    return outliers


def _consecutive_nans(data_series):
    """
    Identifies consecutive NaN values in a pandas Series.

    Parameters:
    ----------
        data_series (pd.Series): Input data

    Returns:
    ----------
        pd.DataFrame: DataFrame with start/end times and duration of consecutive NaN segments
    """
        # Let's see how many consecutive NaN values we have and for what duration  

    # This is to make the duration calculation possible
    data_series.index = pd.to_timedelta(
        data_series.index.map(lambda t: f"{t.hour}:{t.minute}:{t.second}")
    )

    # Create NaN mask and group IDs
    nan_mask = data_series.isna()
    # Cumsum is used to create a unique group ID for each consecutive NaN segment
    # This is done by taking the cumulative sum of the boolean mask, which increments the group ID for each consecutive NaN
    # This way, all consecutive NaNs will have the same group ID
    consecutive_groups = (~nan_mask).cumsum()[nan_mask]

    # Create DataFrame for calculations
    nan_df = pd.DataFrame({
        'group': consecutive_groups,
        'time': data_series.index[nan_mask]
    })

    # Calculate start/end times and duration
    duration_df = nan_df.groupby('group').agg(
        start_time=('time', 'first'),
        end_time=('time', 'last')
    ).assign(
        duration=lambda x: x['end_time'] - x['start_time'] + pd.Timedelta(seconds=1) # +1 second to include the last point
    )

    # Combine counts with durations
    nan_info = (
        nan_df.groupby('group').size()
        .to_frame('count')
        .join(duration_df)
        .reset_index(drop=True)
    )
    return nan_info

def _nan_values(data_series):
    nanvls = data_series.isna().sum()
    print (f"Number of NaN values : {nanvls}\
    This is {nanvls/len(data_series)*100:.2f}% of the data")

def preprocess_vital_signs(data_series, signal_type, interpolate_limit=10, fill_limit=5, span=30, exclude_iqr_outliers=False, smoothing=False, smooth_window=5):
    """
    Comprehensive preprocessing for vital signs data
    
    Parameters:
    ----------
    - data_series: numpy array or pandas Series containing the vital sign measurements
    - signal_type: string indicating the type of signal ('hr', 'sbp', 'dbp')
    - interpolate_limit: int, maximum number of consecutive NaN values to interpolate
    - fill_limit: int, maximum number of consecutive NaN values to fill using forward/backward fill
    - span: int, span for the ewm used to fill NaN values (EWMA does NOT roll a window; it recursively blends the current value with the previous EWMA.)
    - exclude_iqr_outliers: bool, whether to exclude outliers based on IQR method
    - smoothing: bool, whether to apply smoothing
    - smooth_window: int, window size for rolling mean smoothing

    Returns:
    ----------
    - Preprocessed data as pandas Series
    - DataFrame with information about consecutive NaN values
    """
    # Convert to pandas Series if not already
    if not isinstance(data_series, pd.Series):
        data_series = pd.Series(data_series)

    # To avoid making changes on the actual data, we create a copy
    data_series = data_series.copy()
    
    # 1. Define physiological limits based on signal type
    if signal_type == 'hr':
        lower_limit = 30  # Minimum plausible heart rate during anesthesia
        upper_limit = 180  # Maximum plausible heart rate during surgical stress
    elif signal_type == 'sbp':
        lower_limit = 50  # Minimum plausible systolic BP during anesthesia
        upper_limit = 250  # Maximum plausible systolic BP during surgical stimulation
    elif signal_type == 'dbp':
        lower_limit = 30  # Minimum plausible diastolic BP during anesthesia
        upper_limit = 150  # Maximum plausible diastolic BP during surgical stimulation
    else:
        raise ValueError(f"Unknown signal type: {signal_type}")

    # 2. Mark out-of-range values as NaN
    # Out of range is defined as values outside the physiological limits
    # we can also exclude data outside the IQR range using _detect_outliers_iqr method,
    # but heart rate (HR) and blood pressure (BP) can change rapidly (within minutes or even seconds) 
    # during surgery due to physiological stress, pharmacological interventions, and surgical manipulations. 
    if exclude_iqr_outliers:
        data_series[(_detect_outliers_iqr(data_series)) | (data_series < lower_limit) | (data_series > upper_limit)] = np.nan

    else: 
        data_series[(data_series < lower_limit) | (data_series > upper_limit)] = np.nan

    # 2.1 Identify consecutive NaN values
    nan_info = _consecutive_nans(data_series)
    
    # 3. Handle NaN values
    # 3.1 Linear interpolation is widely used in clinical signal processing unless the gap is too large
    #  (>30 seconds) [Clifford et al., Physionet]
    # First, we interpolate small gaps (up to 15 points)
    # For offline analysis where the entire dataset is available
    # The missing values could reasonably be influenced by both preceding and following data points.
    # So limit_direction='both'
    _nan_values(data_series)
    data_series = data_series.interpolate(method='linear', limit=interpolate_limit, limit_direction='both')
    print(f"Linearly Interpolated with limit:{interpolate_limit}")
    _nan_values(data_series)
    
    if data_series.isna().sum() == 0:
        print("No NaN values found after interpolation")
        if smoothing:
            # Apply a rolling mean to smooth the data
            data_series = data_series.rolling(window=smooth_window, min_periods=1).median()
            print(f"Smoothing with a rolling mean with window size: {smooth_window}\n")
            return data_series.values, nan_info
        if not smoothing:
            print("\n")
            return data_series.values, nan_info
        
    # 3.2 For longer gaps, we use forward/backward fill with limited reach
    # This applies forward filling. then backward filling
    #The limit restricts this filling 
    #This prevents unrealistically long plateaus in the data if there's a very long gap
    # This approach preserves the temporal nature of the data better than, for example, 
    # filling all missing values with a mean or median value. It's particularly appropriate 
    # for vital signs where the immediately preceding or following values are often good
    # estimates for brief periods of missing data.
    else:
        
        data_series = data_series.ffill(limit=fill_limit).bfill(limit=fill_limit)
        print(f"Chained Forward-Backward fill with limit: {fill_limit}")
        _nan_values(data_series)
        if data_series.isna().sum() == 0:
            print("No NaN values found after filling")
            if smoothing:
                # Apply a rolling mean to smooth the data
                data_series = data_series.rolling(window=smooth_window, min_periods=1).median()
                print(f"Smoothing with a rolling mean with window size: {smooth_window}\n")
                return data_series.values, nan_info
            if not smoothing:
                print("\n")
                return data_series.values, nan_info
        else:

            # 4. Fill NaN values with an Exponentially Weighted Mean, missing values are 
            # replaced with a smoothed estimate based on historical trends 
            # these are the values that were empty for more than 40 seconds!
            # Due to either not being in the acceptable general range, or being extreme outliers in the IQR method
            # The span parameter controls how much emphasis is placed on recent data versus older data in an exponentially weighted moving average:
            # Smaller span: More responsive to recent changes.
            # Larger span: Smoother and less sensitive to recent changes. 
            # It is analogous to the window size in a simple moving average, but with exponential weighting
            # span=30 means the EWMA will give more weight to the last ~30 points, 
            # with the weights dropping off exponentially as you move further back in the series.
            data_series = data_series.fillna(
                data_series.ewm(span=span).mean())
            print(f"Filled Nans with Exponentially Weighted Moving Average, with the span of {span} samples")
            _nan_values(data_series)
            if smoothing:
                # Apply a rolling mean to smooth the data
                data_series = data_series.rolling(window=smooth_window, min_periods=1).median()
                print(f"Smoothing with a rolling mean with window size: {smooth_window}\n")
                return data_series.values, nan_info
            if not smoothing:
                print("\n")
                return data_series.values, nan_info
            
if __name__ == "__main__":
    print(__doc__) #__doc__ is the docstring
else:
    print(f"Module {repr(__name__)} is imported successfully!")