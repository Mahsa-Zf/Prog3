import numpy as np
import pandas as pd
from scipy.stats import skew
from datetime import datetime, time, timedelta
import warnings
warnings.filterwarnings('ignore')

def _extract_basic_stats(data_series, prefix=''):
    """
    Extract basic statistical features from a time series
    
    Parameters:
    ----------
    - data_series: pandas Series containing the signal
    - prefix: string prefix for feature names
    
    Returns:
    ----------
    - Dictionary of extracted features
    """  
    # Calculate basic statistics
    features = {
            f"{prefix}mean": data_series.mean(),
            f"{prefix}median": data_series.median(),
            f"{prefix}min": data_series.min(),
            f"{prefix}max": data_series.max(),
            f"{prefix}std": data_series.std(),
            f"{prefix}var": data_series.var(),
            f"{prefix}range": data_series.max() - data_series.min(),
            f"{prefix}iqr": data_series.quantile(0.75) - data_series.quantile(0.25),
            f"{prefix}skew": data_series.skew(),
            f"{prefix}kurtosis": data_series.kurtosis(),
            f"{prefix}p25": data_series.quantile(0.25),
            f"{prefix}p75": data_series.quantile(0.75),
        }
        
    # Coefficient of variation (normalized measure of dispersion)
    # The coefficient of variation (CV) is a statistical measure of 
    # relative variability, expressing the standard deviation as a percentage of the mean. 
    # It is used to compare the degree of dispersion between datasets with different units or widely differing means.
    if features[f"{prefix}mean"] != 0:
        features[f"{prefix}cv"] = features[f"{prefix}std"] / abs(features[f"{prefix}mean"])
    else:
        features[f"{prefix}cv"] = np.nan
            
    return features



# Function to choose correlation method
def _select_corr_method(series1, series2):
    # Define skewness threshold (absolute value)
    SKEW_THRESHOLD = 1.0  # Common threshold for "moderate" skewness
    skew1 = abs(skew(series1))
    skew2 = abs(skew(series2))
    return 'spearman' if max(skew1, skew2) > SKEW_THRESHOLD else 'pearson'


def _extract_cross_signal_features(hr_series, sbp_series, dbp_series):
    """
    Extract features that analyze relationships between different vital signs
    SBP - DBP: Difference between systolic and diastolic blood pressure
        - Critical Thresholds:

            - <25 mmHg: May indicate low stroke volume (e.g., hypovolemia)

            - >60 mmHg: Suggests arterial stiffness or high cardiac output

    HR × SBP: Rate-pressure product (RPP) Directly correlates with cardiac workload
        - Stable Anesthesia: Typically 12,000–20,000 mmHg·bpm(varies by procedure)
        - Critical Threshold:
            - RPP <12,000: Associated with myocardial ischemia risk in vulnerable patients
            - RPP >20,000: May occur during surgical stress (e.g., intubation, incision)
    
    Parameters:
    ----------
    - hr_series, sbp_series, dbp_series: pandas Series containing the vital signs
    
    Returns:
    ----------
    - Dictionary of extracted features
    """
    result = {
        "pulse_pressure_mean": np.nan,
        "pulse_pressure_std": np.nan,
        "rate_pressure_product_mean": np.nan,
        "hr_sbp_corr": np.nan,
        "hr_dbp_corr": np.nan,
        "sbp_dbp_corr": np.nan
    }
    
    # Calculate pulse pressure (SBP - DBP)
    if not sbp_series.empty and not dbp_series.empty:
        pulse_pressure = sbp_series - dbp_series
        result["pulse_pressure_mean"] = pulse_pressure.mean()
        result["pulse_pressure_std"] = pulse_pressure.std()
    
    # Calculate rate-pressure product (HR × SBP)
    rate_pressure_product = hr_series* sbp_series
    result["rate_pressure_product_mean"] = rate_pressure_product.mean()
    
        # Calculate correlations between vital signs
        # Align indexes for correlation
        # Apply to each pair
    result["hr_sbp_corr"] = hr_series.corr(
        sbp_series, 
        method=_select_corr_method(hr_series, sbp_series)
        )

    result["hr_dbp_corr"] = hr_series.corr(
        dbp_series, 
        method=_select_corr_method(hr_series, dbp_series)
        )

    result["sbp_dbp_corr"] = sbp_series.corr(
        dbp_series, 
        method=_select_corr_method(sbp_series, dbp_series)
        )
    
    return result


def _parse_time(time_str):
    """Convert 'H:M:S' string to datetime.time object."""
    # Handle single-digit hours without leading zero
    if len(time_str.split(':')[0]) == 1:
        time_str = f'0{time_str}'  # Convert "1:07:40" → "01:07:40"
    
    # Parse with flexible format
    return datetime.strptime(time_str, '%H:%M:%S').time()

def analyze_vital_signs(df, window_size=300, overlap=0, *, start_time=None, end_time=None):
    """
    Comprehensive analyzer for vital sign data
    
    Parameters:
    ----------
    - df: DataFrame containing the vital sign data with a DatetimeIndex
    - start_time: Start time for analysis window (string or datetime.time)
    - end_time: End time for analysis window (string or datetime.time)
    - window_size: Size of analysis window in seconds default=300 which is 10 minutes (ts=2)
    - overlap: Fraction of overlap between consecutive windows
    
    Returns:
    ----------
    - 4 DataFrame: 3 with extracted features for each vital sign, and one cross-signal DataFrame
    """

    # Make sure the times are in the correct format
    if not isinstance(start_time, time) or not isinstance(end_time, time):
        start_time = _parse_time(start_time)
        end_time = _parse_time(end_time)


    # Initialize list to store results
    hr_results = []
    sbp_results = []
    dbp_results = []
    cross_results = []
    # Extract individual series
    hr_series = df['Solar8000/HR']
    sbp_series = df['Solar8000/ART_SBP']
    dbp_series = df['Solar8000/ART_DBP']

    # Convert to datetime with dummy date for arithmetic
    base_date = datetime(2000, 1, 1)  # Arbitrary date
    start_dt = datetime.combine(base_date, start_time)
    end_dt = datetime.combine(base_date, end_time)
    current = start_dt
    seconds = window_size * 2 # because ts=2
    step_size = seconds*(1-overlap) # Step size in seconds

    while current < end_dt: 
        window_start = current.time()        
        # If window exceeds end time, cap it
        if current + timedelta(seconds=seconds) > end_dt:
            window_end = end_dt.time()
        else:
            window_end = (current + timedelta(seconds=seconds)).time()
        
        # Extract data for current window
        hr_window = None if hr_series is None else hr_series[(hr_series.index >= window_start) & (hr_series.index <= window_end)]
        sbp_window = None if sbp_series is None else sbp_series[(sbp_series.index >= window_start) & (sbp_series.index <= window_end)]
        dbp_window = None if dbp_series is None else dbp_series[(dbp_series.index >= window_start) & (dbp_series.index <= window_end)]
        
        # Skip window if all series are empty
        if ((hr_window is None or len(hr_window) == 0) and 
            (sbp_window is None or len(sbp_window) == 0) and 
            (dbp_window is None or len(dbp_window) == 0)):
            continue
        
        # Initialize features dictionary with window metadata
        hr_features = {
            "window_start": window_start,
            "window_end": window_end,
        }
        sbp_features = {
            "window_start": window_start,
            "window_end": window_end,
        }
        dbp_features = {
            "window_start": window_start,
            "window_end": window_end,
        }
        cross_features = {
            "window_start": window_start,
            "window_end": window_end,
        }
        
        # Extract features for each vital sign
        if hr_window is not None and len(hr_window) > 0:
            hr_features.update(_extract_basic_stats(hr_window, prefix="hr_"))
        
        if sbp_window is not None and len(sbp_window) > 0:
            sbp_features.update(_extract_basic_stats(sbp_window, prefix="sbp_"))
        
        if dbp_window is not None and len(dbp_window) > 0:
            dbp_features.update(_extract_basic_stats(dbp_window, prefix="dbp_"))
        
        # Extract cross-signal features
        if (hr_window is not None and len(hr_window) > 0) or \
           (sbp_window is not None and len(sbp_window) > 0) or \
           (dbp_window is not None and len(dbp_window) > 0):
            cross_features.update(_extract_cross_signal_features(
                hr_window if hr_window is not None else pd.Series(),
                sbp_window if sbp_window is not None else pd.Series(),
                dbp_window if dbp_window is not None else pd.Series()
            ))

        current += timedelta(seconds=step_size)
        
        # Add to results
        hr_results.append(hr_features)
        sbp_results.append(sbp_features)
        dbp_results.append(dbp_features)
        cross_results.append(cross_features)

    # Convert results to DataFrames
    hr_df = pd.DataFrame(hr_results)
    sbp_df = pd.DataFrame(sbp_results)
    dbp_df = pd.DataFrame(dbp_results)
    cross_df = pd.DataFrame(cross_results)

    # Apply styling:
    # The styles are applied to the DataFrames to enhance visualization.
    # The background gradient is set to 'RdBu_r' for the columns,
    # indicating a gradient from blue to red, i.e. low to high values respectively in each column.
    # hot_r shows the gradient from hot to red colors, indicating negative to positive values.
    # The precision is set to 2 decimal places for better readability.
    styled_hr = hr_df.style.background_gradient(cmap='RdBu_r', axis=0).format(precision=2)
    styled_sbp = sbp_df.style.background_gradient(cmap='RdBu_r', axis=0).format(precision=2)
    styled_dbp = dbp_df.style.background_gradient(cmap='RdBu_r', axis=0).format(precision=2)
    styled_cross = (cross_df.style
    .background_gradient(cmap='RdBu_r', subset=['hr_sbp_corr', 'hr_dbp_corr',	'sbp_dbp_corr'])  # Red(-) to Blue(+)
    .background_gradient(cmap='Greens', subset=['pulse_pressure_mean'])  # Low to High PP
    .background_gradient(cmap='Oranges', subset=['pulse_pressure_std'])  # Low to High Variability
    .background_gradient(cmap='Purples', subset=['rate_pressure_product_mean'])  # Low to High RPP
    ).format(precision=2)

    

    return styled_hr, styled_sbp, styled_dbp, styled_cross



if __name__ == "__main__":
    print(__doc__) #__doc__ is the docstring
else:
    print(f"Module {repr(__name__)} is imported successfully!")