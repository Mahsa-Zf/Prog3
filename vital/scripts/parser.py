"""
Vital Signs Data Processing Module

This module provides classes and functions for loading, cleaning, and preprocessing
vital signs data from VitalDB files. It implements a modular design with separate
classes for data loading, preprocessing, and outlier detection.

Classes:
    - VitalSignsDataLoader: Handles data loading and configuration
    - VitalSignsPreprocessor: Handles data preprocessing and cleaning
    - OutlierDetector: Handles outlier detection using various methods
    - DataQualityAnalyzer: Provides data quality analysis and reporting

Functions:
    - create_time_index: Creates time index for vital signs data
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
import vitaldb
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Enumeration for supported vital sign types."""
    HR = "hr"
    SBP = "sbp"
    DBP = "dbp"


@dataclass
class PhysiologicalLimits:
    """Data class to store physiological limits for vital signs."""
    lower_limit: float
    upper_limit: float
    
    @classmethod
    def get_limits(cls, signal_type: SignalType) -> 'PhysiologicalLimits':
        """Get physiological limits for a given signal type."""
        limits_map = {
            SignalType.HR: cls(30, 180),    # Heart rate limits
            SignalType.SBP: cls(50, 250),   # Systolic BP limits
            SignalType.DBP: cls(30, 150),   # Diastolic BP limits
        }
        return limits_map[signal_type]


@dataclass
class PreprocessingConfig:
    """Configuration class for preprocessing parameters."""
    interpolate_limit: int = 10
    fill_limit: int = 5
    ewm_span: int = 30
    exclude_iqr_outliers: bool = False
    smoothing: bool = False
    smooth_window: int = 5


class VitalSignsDataLoader:
    """Handles loading and initial formatting of vital signs data."""
    
    DEFAULT_TRACKS = [
        'Solar8000/ART_SBP',
        'Solar8000/ART_DBP', 
        'Solar8000/HR',
        'EVENT'
    ]
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the data loader.
        
        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> Path:
        """Get the default configuration file path."""
        base_dir = Path(__file__).resolve().parent.parent
        return base_dir / "config.yaml"
    
    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as config_file:
                return yaml.safe_load(config_file)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
    
    def load_data(self, filename: str, tracks: Optional[List[str]] = None, 
                  interval: int = 2, get_track_names: bool = False) -> Union[pd.DataFrame, Tuple[pd.DataFrame, List[str]]]:
        """
        Load vital signs data from VitalDB file.
        
        Args:
            filename: Key for the dataset path in config file
            tracks: List of track names to load. Uses default if None.
            interval: Sampling interval in seconds
            get_track_names: Whether to return available track names
            
        Returns:
            DataFrame with vital signs data, optionally with track names
        """
        try:
            file_path = self.config["Data"][filename]
            vf = vitaldb.VitalFile(file_path)
            
            tracks = tracks or self.DEFAULT_TRACKS
            df = vf.to_pandas(tracks, interval=interval)
            
            # Create time index
            df = self._create_time_index(df, interval)
            
            # Convert numeric columns to float
            df = self._convert_numeric_columns(df)
            
            logger.info(f"Successfully loaded data with shape: {df.shape}")
            
            if get_track_names:
                track_names = vf.get_track_names()
                return df, track_names
            return df
            
        except KeyError:
            logger.error(f"Filename '{filename}' not found in configuration")
            raise
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _create_time_index(self, df: pd.DataFrame, interval: int) -> pd.DataFrame:
        """Create time index for the DataFrame."""
        time_freq = pd.date_range(
            start=datetime.today().date(),
            periods=df.shape[0],
            freq=f'{interval}s'
        )
        df.set_index(time_freq.time, inplace=True)
        return df
    
    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert numeric columns to float type."""
        for col in df.columns:
            if col != 'EVENT':
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df


class OutlierDetector:
    """Handles outlier detection using various methods."""
    
    @staticmethod
    def detect_iqr_outliers(data: pd.Series, auto_adjust: bool = True) -> pd.Series:
        """
        Detect outliers using IQR method with adaptive multipliers.
        
        Args:
            data: Input data series
            auto_adjust: Whether to adjust multipliers based on skewness
            
        Returns:
            Boolean mask where True indicates outliers
        """
        if not isinstance(data, pd.Series):
            data = pd.Series(data)
        
        skew = data.skew()
        
        if auto_adjust:
            lower_mult, upper_mult = OutlierDetector._get_multipliers(skew)
            logger.info(f"Skewness: {skew:.4f} → Lower Mult: {lower_mult}, Upper Mult: {upper_mult}")
        else:
            lower_mult = upper_mult = 1.5
        
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - lower_mult * iqr
        upper_bound = q3 + upper_mult * iqr
        
        return (data < lower_bound) | (data > upper_bound)
    
    @staticmethod
    def _get_multipliers(skew: float) -> Tuple[float, float]:
        """Get IQR multipliers based on data skewness."""
        if -0.5 <= skew <= 0.5:
            return 1.5, 1.5
        elif 0.5 < skew <= 1.0:
            return 1.5, 2.0
        elif skew > 1.0:
            return 1.5, 2.5
        elif -1.0 <= skew < -0.5:
            return 2.0, 1.5
        else:  # skew < -1.0
            return 2.5, 1.5


class DataQualityAnalyzer:
    """Provides data quality analysis and reporting."""
    
    @staticmethod
    def analyze_data_quality(df: pd.DataFrame) -> Dict:
        """
        Analyze data quality metrics.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dictionary with quality metrics
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        metrics = {
            'shape': df.shape,
            'duplicate_indices': df.index.duplicated().sum(),
            'duplicate_rows': df.duplicated().sum(),
            'nan_counts': df[numeric_cols].isna().sum().to_dict(),
            'total_nans': df[numeric_cols].isna().sum().sum(),
            'nan_percentage': (df[numeric_cols].isna().sum().sum() / 
                             (df.shape[0] * len(numeric_cols)) * 100)
        }
        
        return metrics
    
    @staticmethod
    def print_data_info(df: pd.DataFrame) -> None:
        """Print comprehensive data information."""
        metrics = DataQualityAnalyzer.analyze_data_quality(df)
        
        print(f"Data Shape: {metrics['shape']}")
        print(f"Duplicate Indices: {metrics['duplicate_indices']}")
        print(f"Duplicate Rows: {metrics['duplicate_rows']}")
        print(f"Total NaN Values: {metrics['total_nans']}")
        print(f"NaN Percentage: {metrics['nan_percentage']:.2f}%")
        print("\nNaN counts by column:")
        for col, count in metrics['nan_counts'].items():
            print(f"  {col}: {count}")
        print()
        df.info()
    
    @staticmethod
    def analyze_consecutive_nans(data: pd.Series) -> pd.DataFrame:
        """
        Analyze consecutive NaN segments in data.
        
        Args:
            data: Input data series
            
        Returns:
            DataFrame with information about consecutive NaN segments
        """
        # Convert index to timedelta for duration calculation
        data_copy = data.copy()
        data_copy.index = pd.to_timedelta(
            data_copy.index.map(lambda t: f"{t.hour}:{t.minute}:{t.second}")
        )
        
        nan_mask = data_copy.isna()
        if not nan_mask.any():
            return pd.DataFrame()
        
        # Create group IDs for consecutive NaN segments
        consecutive_groups = (~nan_mask).cumsum()[nan_mask]
        
        nan_df = pd.DataFrame({
            'group': consecutive_groups,
            'time': data_copy.index[nan_mask]
        })
        
        # Calculate start/end times and duration
        duration_df = nan_df.groupby('group').agg(
            start_time=('time', 'first'),
            end_time=('time', 'last')
        ).assign(
            duration=lambda x: x['end_time'] - x['start_time'] + pd.Timedelta(seconds=1)
        )
        
        # Combine counts with durations
        nan_info = (
            nan_df.groupby('group').size()
            .to_frame('count')
            .join(duration_df)
            .reset_index(drop=True)
        )
        
        return nan_info


class VitalSignsPreprocessor:
    """Handles preprocessing of vital signs data."""
    
    def __init__(self, config: PreprocessingConfig = None):
        """
        Initialize preprocessor with configuration.
        
        Args:
            config: Preprocessing configuration. Uses default if None.
        """
        self.config = config or PreprocessingConfig()
        self.outlier_detector = OutlierDetector()
        self.quality_analyzer = DataQualityAnalyzer()
    
    def preprocess_signal(self, data: Union[pd.Series, np.ndarray], 
                         signal_type: SignalType) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Comprehensive preprocessing for vital signs data.
        
        Args:
            data: Input vital signs data
            signal_type: Type of vital sign (HR, SBP, DBP)
            
        Returns:
            Tuple of (preprocessed_data, nan_info_dataframe)
        """
        # Convert to pandas Series
        if not isinstance(data, pd.Series):
            data = pd.Series(data)
        
        data = data.copy()
        
        # Get physiological limits
        limits = PhysiologicalLimits.get_limits(signal_type)
        
        # Apply outlier detection and physiological limits
        data = self._apply_outlier_filtering(data, limits)
        
        # Analyze consecutive NaNs before processing
        nan_info = self.quality_analyzer.analyze_consecutive_nans(data)
        
        # Handle missing values
        data = self._handle_missing_values(data)
        
        # Apply smoothing if requested
        if self.config.smoothing:
            data = self._apply_smoothing(data)
        
        logger.info("Preprocessing completed successfully")
        return data.values, nan_info
    
    def _apply_outlier_filtering(self, data: pd.Series, 
                               limits: PhysiologicalLimits) -> pd.Series:
        """Apply outlier filtering based on configuration."""
        # Mark physiologically impossible values as NaN
        physiological_outliers = (data < limits.lower_limit) | (data > limits.upper_limit)
        
        if self.config.exclude_iqr_outliers:
            iqr_outliers = self.outlier_detector.detect_iqr_outliers(data)
            outliers = physiological_outliers | iqr_outliers
        else:
            outliers = physiological_outliers
        
        data[outliers] = np.nan
        logger.info(f"Marked {outliers.sum()} values as outliers")
        
        return data
    
    def _handle_missing_values(self, data: pd.Series) -> pd.Series:
        """Handle missing values using multiple strategies."""
        initial_nans = data.isna().sum()
        logger.info(f"Initial NaN count: {initial_nans} ({initial_nans/len(data)*100:.2f}%)")
        
        # Step 1: Linear interpolation for small gaps
        data = data.interpolate(
            method='linear', 
            limit=self.config.interpolate_limit, 
            limit_direction='both'
        )
        
        after_interp_nans = data.isna().sum()
        logger.info(f"After linear interpolation: {after_interp_nans} NaNs remaining")
        
        if after_interp_nans == 0:
            return data
        
        # Step 2: Forward/backward fill for medium gaps
        data = data.ffill(limit=self.config.fill_limit).bfill(limit=self.config.fill_limit)
        
        after_fill_nans = data.isna().sum()
        logger.info(f"After forward/backward fill: {after_fill_nans} NaNs remaining")
        
        if after_fill_nans == 0:
            return data
        
        # Step 3: Exponentially weighted moving average for remaining gaps
        data = data.fillna(data.ewm(span=self.config.ewm_span).mean())
        
        final_nans = data.isna().sum()
        logger.info(f"After EWMA fill: {final_nans} NaNs remaining")
        
        return data
    
    def _apply_smoothing(self, data: pd.Series) -> pd.Series:
        """Apply smoothing to the data."""
        smoothed = data.rolling(
            window=self.config.smooth_window, 
            min_periods=1
        ).median()
        
        logger.info(f"Applied smoothing with window size: {self.config.smooth_window}")
        return smoothed


# Convenience functions for backward compatibility
def load_data(filename: str, get_track_names: bool = False) -> Union[pd.DataFrame, Tuple[pd.DataFrame, List[str]]]:
    """
    Load data using the default data loader.
    
    Args:
        filename: Key for dataset path in config
        get_track_names: Whether to return track names
        
    Returns:
        DataFrame or tuple with DataFrame and track names
    """
    loader = VitalSignsDataLoader()
    return loader.load_data(filename, get_track_names=get_track_names)


def data_info(df: pd.DataFrame) -> None:
    """Print data information using the quality analyzer."""
    DataQualityAnalyzer.print_data_info(df)


def preprocess_vital_signs(data_series: Union[pd.Series, np.ndarray], 
                          signal_type: str, **kwargs) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Preprocess vital signs data using the default preprocessor.
    
    Args:
        data_series: Input data
        signal_type: Type of signal ('hr', 'sbp', 'dbp')
        **kwargs: Additional preprocessing parameters
        
    Returns:
        Tuple of (preprocessed_data, nan_info_dataframe)
    """
    # Convert string signal type to enum
    signal_enum = SignalType(signal_type.lower())
    
    # Create config from kwargs
    config = PreprocessingConfig(**{k: v for k, v in kwargs.items() 
                                  if k in PreprocessingConfig.__dataclass_fields__})
    
    preprocessor = VitalSignsPreprocessor(config)
    return preprocessor.preprocess_signal(data_series, signal_enum)


if __name__ == "__main__":
    print(__doc__)
else:
    logger.info(f"Module {repr(__name__)} imported successfully!")