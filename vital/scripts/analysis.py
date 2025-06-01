import numpy as np
import pandas as pd
from scipy.stats import skew
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import warnings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')


@dataclass
class AnalysisConfig:
    """Configuration parameters for vital signs analysis"""
    window_size: int = 300  # seconds (5 minutes with ts=2)
    overlap: float = 0.0    # fraction of overlap between windows
    skew_threshold: float = 1.0  # threshold for correlation method selection
    min_data_points: int = 10    # minimum data points required per window
    
    # Clinical thresholds
    pulse_pressure_low: float = 25.0   # mmHg
    pulse_pressure_high: float = 60.0  # mmHg
    rpp_low: float = 12000.0          # mmHg·bpm
    rpp_high: float = 20000.0         # mmHg·bpm


class VitalSignsError(Exception):
    """Custom exception for vital signs analysis errors"""
    pass


class TimeParser:
    """Utility class for time parsing operations"""
    
    @staticmethod
    def parse_time(time_input: Union[str, time]) -> time:
        """
        Convert time input to datetime.time object
        
        Args:
            time_input: Time as string ('H:M:S') or datetime.time object
            
        Returns:
            datetime.time object
            
        Raises:
            VitalSignsError: If time parsing fails
        """
        if isinstance(time_input, time):
            return time_input
            
        if isinstance(time_input, str):
            try:
                # Handle single-digit hours without leading zero
                if len(time_input.split(':')[0]) == 1:
                    time_input = f'0{time_input}'
                return datetime.strptime(time_input, '%H:%M:%S').time()
            except ValueError as e:
                raise VitalSignsError(f"Invalid time format: {time_input}. Expected 'H:M:S' format") from e
        
        raise VitalSignsError(f"Invalid time input type: {type(time_input)}")


class DataValidator:
    """Validates input data for analysis"""
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
        """
        Validate DataFrame structure and content
        
        Args:
            df: Input DataFrame
            required_columns: List of required column names
            
        Raises:
            VitalSignsError: If validation fails
        """
        if df is None or df.empty:
            raise VitalSignsError("DataFrame is None or empty")
            
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            raise VitalSignsError(f"Missing required columns: {missing_cols}")
            
        if not isinstance(df.index, pd.DatetimeIndex) and df.index.dtype != 'object':
            raise VitalSignsError("DataFrame index must be DatetimeIndex or time objects")
    
    @staticmethod
    def validate_config(config: AnalysisConfig) -> None:
        """
        Validate analysis configuration
        
        Args:
            config: Analysis configuration object
            
        Raises:
            VitalSignsError: If configuration is invalid
        """
        if config.window_size <= 0:
            raise VitalSignsError("Window size must be positive")
            
        if not 0 <= config.overlap < 1:
            raise VitalSignsError("Overlap must be between 0 and 1 (exclusive)")
            
        if config.min_data_points <= 0:
            raise VitalSignsError("Minimum data points must be positive")


class FeatureExtractor:
    """Extracts statistical features from time series data"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
    
    def extract_basic_stats(self, data_series: pd.Series, prefix: str = '') -> Dict[str, float]:
        """
        Extract basic statistical features from a time series
        
        Args:
            data_series: pandas Series containing the signal
            prefix: string prefix for feature names
            
        Returns:
            Dictionary of extracted features
        """
        if data_series.empty:
            return self._empty_stats_dict(prefix)
            
        try:
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
            mean_val = features[f"{prefix}mean"]
            if mean_val != 0 and not np.isnan(mean_val):
                features[f"{prefix}cv"] = features[f"{prefix}std"] / abs(mean_val)
            else:
                features[f"{prefix}cv"] = np.nan
                
            return features
            
        except Exception as e:
            logger.warning(f"Error extracting basic stats: {e}")
            return self._empty_stats_dict(prefix)
    
    def _empty_stats_dict(self, prefix: str) -> Dict[str, float]:
        """Return dictionary with NaN values for empty data"""
        return {f"{prefix}{stat}": np.nan for stat in 
                ['mean', 'median', 'min', 'max', 'std', 'var', 'range', 
                 'iqr', 'skew', 'kurtosis', 'p25', 'p75', 'cv']}


class CorrelationAnalyzer:
    """Handles correlation analysis between time series"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
    
    def select_correlation_method(self, series1: pd.Series, series2: pd.Series) -> str:
        """
        Select appropriate correlation method based on data distribution
        
        Args:
            series1, series2: Time series for correlation analysis
            
        Returns:
            Correlation method ('pearson' or 'spearman')
        """
        try:
            skew1 = abs(skew(series1.dropna()))
            skew2 = abs(skew(series2.dropna()))
            return 'spearman' if max(skew1, skew2) > self.config.skew_threshold else 'pearson'
        except Exception:
            return 'pearson'  # Default fallback
    
    def calculate_correlation(self, series1: pd.Series, series2: pd.Series) -> float:
        """
        Calculate correlation between two series
        
        Args:
            series1, series2: Time series for correlation
            
        Returns:
            Correlation coefficient
        """
        if series1.empty or series2.empty:
            return np.nan
            
        try:
            method = self.select_correlation_method(series1, series2)
            return series1.corr(series2, method=method)
        except Exception as e:
            logger.warning(f"Error calculating correlation: {e}")
            return np.nan


class CrossSignalAnalyzer:
    """Analyzes relationships between different vital signs"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.correlation_analyzer = CorrelationAnalyzer(config)
    
    def extract_cross_signal_features(self, hr_series: pd.Series, 
                                    sbp_series: pd.Series, 
                                    dbp_series: pd.Series) -> Dict[str, float]:
        """
        Extract features analyzing relationships between vital signs
        
        Args:
            hr_series: Heart rate time series
            sbp_series: Systolic blood pressure time series  
            dbp_series: Diastolic blood pressure time series
            
        Returns:
            Dictionary of cross-signal features
        """
        features = {
            "pulse_pressure_mean": np.nan,
            "pulse_pressure_std": np.nan,
            "rate_pressure_product_mean": np.nan,
            "hr_sbp_corr": np.nan,
            "hr_dbp_corr": np.nan,
            "sbp_dbp_corr": np.nan,
            "pulse_pressure_risk": "unknown",
            "rpp_risk": "unknown"
        }
        
        # Calculate pulse pressure (SBP - DBP)
        if not sbp_series.empty and not dbp_series.empty:
            try:
                pulse_pressure = sbp_series - dbp_series
                pp_mean = pulse_pressure.mean()
                features["pulse_pressure_mean"] = pp_mean
                features["pulse_pressure_std"] = pulse_pressure.std()
                
                # Clinical risk assessment
                if pp_mean < self.config.pulse_pressure_low:
                    features["pulse_pressure_risk"] = "low"
                elif pp_mean > self.config.pulse_pressure_high:
                    features["pulse_pressure_risk"] = "high"
                else:
                    features["pulse_pressure_risk"] = "normal"
                    
            except Exception as e:
                logger.warning(f"Error calculating pulse pressure: {e}")
        
        # Calculate rate-pressure product (HR × SBP)
        if not hr_series.empty and not sbp_series.empty:
            try:
                rate_pressure_product = hr_series * sbp_series
                rpp_mean = rate_pressure_product.mean()
                features["rate_pressure_product_mean"] = rpp_mean
                
                # Clinical risk assessment
                if rpp_mean < self.config.rpp_low:
                    features["rpp_risk"] = "low"
                elif rpp_mean > self.config.rpp_high:
                    features["rpp_risk"] = "high"
                else:
                    features["rpp_risk"] = "normal"
                    
            except Exception as e:
                logger.warning(f"Error calculating rate-pressure product: {e}")
        
        # Calculate correlations
        features["hr_sbp_corr"] = self.correlation_analyzer.calculate_correlation(hr_series, sbp_series)
        features["hr_dbp_corr"] = self.correlation_analyzer.calculate_correlation(hr_series, dbp_series)
        features["sbp_dbp_corr"] = self.correlation_analyzer.calculate_correlation(sbp_series, dbp_series)
        
        return features


class WindowManager:
    """Manages analysis windows and data extraction"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.time_parser = TimeParser()
    
    def generate_windows(self, start_time: Union[str, time], 
                        end_time: Union[str, time]) -> List[Tuple[time, time]]:
        """
        Generate analysis windows between start and end times
        
        Args:
            start_time: Analysis start time
            end_time: Analysis end time
            
        Returns:
            List of (window_start, window_end) tuples
        """
        start_time = self.time_parser.parse_time(start_time)
        end_time = self.time_parser.parse_time(end_time)
        
        base_date = datetime(2000, 1, 1)
        start_dt = datetime.combine(base_date, start_time)
        end_dt = datetime.combine(base_date, end_time)
        
        windows = []
        seconds = self.config.window_size * 2  # ts=2
        step_size = seconds * (1 - self.config.overlap)
        current = start_dt
        
        while current < end_dt:
            window_start = current.time()
            window_end_dt = min(current + timedelta(seconds=seconds), end_dt)
            window_end = window_end_dt.time()
            
            windows.append((window_start, window_end))
            current += timedelta(seconds=step_size)
            
        return windows
    
    def extract_window_data(self, df: pd.DataFrame, window_start: time, 
                           window_end: time) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Extract data for a specific time window
        
        Args:
            df: Input DataFrame
            window_start: Window start time
            window_end: Window end time
            
        Returns:
            Tuple of (hr_series, sbp_series, dbp_series)
        """
        mask = (df.index >= window_start) & (df.index <= window_end)
        
        hr_series = df['Solar8000/HR'][mask] if 'Solar8000/HR' in df.columns else pd.Series()
        sbp_series = df['Solar8000/ART_SBP'][mask] if 'Solar8000/ART_SBP' in df.columns else pd.Series()
        dbp_series = df['Solar8000/ART_DBP'][mask] if 'Solar8000/ART_DBP' in df.columns else pd.Series()
        
        return hr_series, sbp_series, dbp_series


class ResultFormatter:
    """Formats and styles analysis results"""
    
    @staticmethod
    def apply_styling(hr_df: pd.DataFrame, sbp_df: pd.DataFrame, 
                     dbp_df: pd.DataFrame, cross_df: pd.DataFrame) -> Tuple:
        """
        Apply visual styling to result DataFrames
        
        Args:
            hr_df, sbp_df, dbp_df, cross_df: Result DataFrames
            
        Returns:
            Tuple of styled DataFrames
        """
        styled_hr = hr_df.style.background_gradient(cmap='RdBu_r', axis=0).format(precision=2)
        styled_sbp = sbp_df.style.background_gradient(cmap='RdBu_r', axis=0).format(precision=2)
        styled_dbp = dbp_df.style.background_gradient(cmap='RdBu_r', axis=0).format(precision=2)
        
        styled_cross = (cross_df.style
            .background_gradient(cmap='RdBu_r', subset=['hr_sbp_corr', 'hr_dbp_corr', 'sbp_dbp_corr'])
            .background_gradient(cmap='Greens', subset=['pulse_pressure_mean'])
            .background_gradient(cmap='Oranges', subset=['pulse_pressure_std'])
            .background_gradient(cmap='Purples', subset=['rate_pressure_product_mean'])
            .format(precision=2)
        )
        
        return styled_hr, styled_sbp, styled_dbp, styled_cross


class VitalSignsAnalyzer:
    """
    Main class for comprehensive vital signs analysis
    
    This class orchestrates the entire analysis pipeline, from data validation
    to feature extraction and result formatting.
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        Initialize the analyzer
        
        Args:
            config: Analysis configuration (uses default if None)
        """
        self.config = config or AnalysisConfig()
        self.validator = DataValidator()
        self.feature_extractor = FeatureExtractor(self.config)
        self.cross_signal_analyzer = CrossSignalAnalyzer(self.config)
        self.window_manager = WindowManager(self.config)
        self.result_formatter = ResultFormatter()
        
        # Required columns for analysis
        self.required_columns = ['Solar8000/HR', 'Solar8000/ART_SBP', 'Solar8000/ART_DBP']
    
    def analyze(self, df: pd.DataFrame, start_time: Union[str, time], 
                end_time: Union[str, time]) -> Tuple:
        """
        Perform comprehensive vital signs analysis
        
        Args:
            df: DataFrame containing vital sign data with DatetimeIndex
            start_time: Analysis start time
            end_time: Analysis end time
            
        Returns:
            Tuple of styled DataFrames (hr_results, sbp_results, dbp_results, cross_results)
            
        Raises:
            VitalSignsError: If analysis fails
        """
        try:
            # Validate inputs
            self.validator.validate_dataframe(df, self.required_columns)
            self.validator.validate_config(self.config)
            
            # Generate analysis windows
            windows = self.window_manager.generate_windows(start_time, end_time)
            
            if not windows:
                raise VitalSignsError("No valid analysis windows generated")
            
            # Initialize results storage
            results = {
                'hr': [],
                'sbp': [],
                'dbp': [],
                'cross': []
            }
            
            # Process each window
            valid_windows = 0
            for window_start, window_end in windows:
                window_results = self._process_window(df, window_start, window_end)
                
                if window_results:
                    for key, result in window_results.items():
                        results[key].append(result)
                    valid_windows += 1
            
            if valid_windows == 0:
                raise VitalSignsError("No valid data found in any analysis window")
            
            logger.info(f"Successfully processed {valid_windows} windows")
            
            # Convert to DataFrames and apply styling
            result_dfs = {
                key: pd.DataFrame(data) for key, data in results.items()
            }
            
            return self.result_formatter.apply_styling(
                result_dfs['hr'], result_dfs['sbp'], 
                result_dfs['dbp'], result_dfs['cross']
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise VitalSignsError(f"Analysis failed: {e}") from e
    
    def _process_window(self, df: pd.DataFrame, window_start: time, 
                       window_end: time) -> Optional[Dict]:
        """
        Process a single analysis window
        
        Args:
            df: Input DataFrame
            window_start: Window start time
            window_end: Window end time
            
        Returns:
            Dictionary of results for this window, or None if insufficient data
        """
        try:
            # Extract window data
            hr_window, sbp_window, dbp_window = self.window_manager.extract_window_data(
                df, window_start, window_end
            )
            
            # Check if we have sufficient data
            total_points = len(hr_window) + len(sbp_window) + len(dbp_window)
            if total_points < self.config.min_data_points:
                logger.debug(f"Insufficient data in window {window_start}-{window_end}")
                return None
            
            # Initialize feature dictionaries
            base_features = {
                "window_start": window_start,
                "window_end": window_end,
            }
            
            # Extract features for each vital sign
            hr_features = base_features.copy()
            hr_features.update(self.feature_extractor.extract_basic_stats(hr_window, "hr_"))
            
            sbp_features = base_features.copy()
            sbp_features.update(self.feature_extractor.extract_basic_stats(sbp_window, "sbp_"))
            
            dbp_features = base_features.copy()
            dbp_features.update(self.feature_extractor.extract_basic_stats(dbp_window, "dbp_"))
            
            # Extract cross-signal features
            cross_features = base_features.copy()
            cross_features.update(self.cross_signal_analyzer.extract_cross_signal_features(
                hr_window, sbp_window, dbp_window
            ))
            
            return {
                'hr': hr_features,
                'sbp': sbp_features, 
                'dbp': dbp_features,
                'cross': cross_features
            }
            
        except Exception as e:
            logger.warning(f"Error processing window {window_start}-{window_end}: {e}")
            return None


# Convenience function for backward compatibility
def analyze_vital_signs(df: pd.DataFrame, window_size: int = 300, overlap: float = 0, 
                       *, start_time: Union[str, time], end_time: Union[str, time],
                       config: Optional[AnalysisConfig] = None) -> Tuple:
    """
    Convenience function for vital signs analysis (backward compatibility)
    
    Args:
        df: DataFrame containing vital sign data
        window_size: Analysis window size in seconds
        overlap: Overlap fraction between windows
        start_time: Analysis start time
        end_time: Analysis end time
        config: Optional analysis configuration
        
    Returns:
        Tuple of styled analysis results
    """
    if config is None:
        config = AnalysisConfig(window_size=window_size, overlap=overlap)
    
    analyzer = VitalSignsAnalyzer(config)
    return analyzer.analyze(df, start_time, end_time)


if __name__ == "__main__":
    print(__doc__)
else:
    logger.info(f"Module {repr(__name__)} imported successfully!")
