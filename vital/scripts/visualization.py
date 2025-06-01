"""
Vital Signs Visualization Module

This module provides classes and functions for creating static and interactive
visualizations of vital signs data. It implements a modular design with separate
classes for different visualization types and configuration management.

Classes:
    - VitalSignsVisualizer: Base class for vital signs visualization
    - StaticPlotVisualizer: Handles static matplotlib-based plots
    - InteractivePlotVisualizer: Handles interactive Bokeh-based plots
    - VisualizationConfig: Configuration management for plots

Functions:
    - create_static_plot: Convenience function for static plots
    - create_interactive_plot: Convenience function for interactive plots
"""

import matplotlib.pyplot as plt
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool
from bokeh.io import output_file, save
import panel as pn
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging
import warnings
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')

class PlotType(Enum):
    """Enumeration for supported plot types."""
    STATIC = "static"
    INTERACTIVE = "interactive"


class SignalColumn(Enum):
    """
    Enumeration for vital sign column names.
    Purpose:
    Avoid typos: Instead of writing the string "Solar8000/ART_DBP" everywhere, you use SignalColumn.DBP.
    Improve readability and maintainability: It’s clear what each constant represents.
    Type safety: You can type-check or autocomplete these values in your code.
    
    """
    DBP = "Solar8000/ART_DBP"
    SBP = "Solar8000/ART_SBP"
    HR = "Solar8000/HR"
    EVENT = "EVENT"


@dataclass
class PlotMetadata:
    """Metadata for vital signs plots."""
    title: str
    y_label: str
    color: str = "navy"
    line_width: float = 2.0
    
    @classmethod
    def get_metadata(cls, column: SignalColumn) -> 'PlotMetadata':
        """Get plot metadata for a given signal column."""
        metadata_map = {
            SignalColumn.DBP: cls(
                title="Arterial Diastolic Blood Pressure During Surgery",
                y_label="Arterial Diastolic Blood Pressure (mmHg)",
                color="blue"
            ),
            SignalColumn.SBP: cls(
                title="Arterial Systolic Blood Pressure During Surgery",
                y_label="Arterial Systolic Blood Pressure (mmHg)",
                color="red"
            ),
            SignalColumn.HR: cls(
                title="Heart Rate During Surgery",
                y_label="Heart Rate (bpm)",
                color="green"
            )
        }
        return metadata_map[column]


@dataclass
class StaticPlotConfig:
    """Configuration for static plots."""
    figure_size: Tuple[int, int] = (15, 5)
    title_fontsize: int = 16
    label_fontsize: int = 12
    event_line_color: str = 'red'
    event_line_style: str = '--'
    event_line_width: float = 1.0
    event_text_fontsize: int = 10
    event_text_weight: str = 'bold'
    save_dpi: int = 300
    save_format: str = 'png'


@dataclass
class InteractivePlotConfig:
    """Configuration for interactive plots."""
    plot_height: int = 350
    plot_width: int = 800
    line_width: float = 2.0
    nan_line_color: str = "red"
    nan_line_width: float = 2.0
    hover_mode: str = "vline"
    tools: str = "pan,wheel_zoom,box_zoom,reset"


@dataclass
class VisualizationConfig:
    """Master configuration for all visualization settings."""
    static_config: StaticPlotConfig = None
    interactive_config: InteractivePlotConfig = None
    
    def __post_init__(self):
        if self.static_config is None:
            self.static_config = StaticPlotConfig()
        if self.interactive_config is None:
            self.interactive_config = InteractivePlotConfig()


class VitalSignsVisualizer(ABC):
    """
    Abstract base class for vital signs visualizers.
    By using ABC and abstractmethod, the code ensures that all 
    visualization classes (StaticPlotVisualizer, InteractivePlotVisualizer) 
    implement the necessary methods and adhere to the same interface, 
    making the code more maintainable, consistent, and robust
    Consistency:
    All visualizers (like StaticPlotVisualizer and InteractivePlotVisualizer) must have the same core methods.
    Maintainability:
    If you add a new visualizer, you know exactly what methods it needs.
    Robustness:
    Python will not let you forget to implement required methods.
    """
    
    def __init__(self, config: VisualizationConfig = None):
        """
        Initialize the visualizer.
        
        Args:
            config: Visualization configuration. Uses default if None.
        """
        self.config = config or VisualizationConfig()
        self._validate_data_requirements()
    
    @abstractmethod
    def _validate_data_requirements(self) -> None:
        """Validate that required dependencies are available."""
        pass
    
    @abstractmethod
    def create_plot(self, df: pd.DataFrame, column: Union[str, SignalColumn], 
                   **kwargs) -> None:
        """Create a plot for the specified data and column."""
        pass
    
    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate DataFrame requirements."""
        if df.empty:
            raise ValueError("DataFrame cannot be empty")
        
        if not isinstance(df.index, pd.DatetimeIndex) and not hasattr(df.index, 'time'):
            logger.warning("DataFrame index is not datetime-based. Some features may not work correctly.")
    
    def _normalize_column_name(self, column: Union[str, SignalColumn]) -> SignalColumn:
        """Normalize column name to SignalColumn enum."""
        if isinstance(column, str):
            try:
                return SignalColumn(column)
            except ValueError:
                # Try to find matching enum by value
                for signal_col in SignalColumn:
                    if signal_col.value == column:
                        return signal_col
                raise ValueError(f"Unknown column: {column}")
        return column


class StaticPlotVisualizer(VitalSignsVisualizer):
    """Handles creation of static matplotlib-based plots."""
    
    def _validate_data_requirements(self) -> None:
        """Validate matplotlib availability."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib is required for static plots")
    
    def create_plot(self, df: pd.DataFrame, column: Union[str, SignalColumn], 
                   save_file: bool = False, output_dir: Optional[Path] = None,
                   show_events: bool = True) -> plt.Figure:
        """
        Create a static plot for vital signs data.
        
        Args:
            df: DataFrame containing vital signs data
            column: Column to plot
            save_file: Whether to save the plot to file
            output_dir: Directory to save plots (uses current dir if None)
            show_events: Whether to show event markers
            
        Returns:
            matplotlib Figure object
        """
        self._validate_dataframe(df)
        column_enum = self._normalize_column_name(column)
        
        if column_enum.value not in df.columns:
            raise ValueError(f"Column {column_enum.value} not found in DataFrame")
        
        metadata = PlotMetadata.get_metadata(column_enum)
        config = self.config.static_config
        
        # Create the plot
        fig, ax = plt.subplots(figsize=config.figure_size)
        
        # Plot the main data
        df.plot(y=column_enum.value, ax=ax, color=metadata.color, 
                linewidth=metadata.line_width)
        
        # Add event markers if requested and EVENT column exists
        if show_events and SignalColumn.EVENT.value in df.columns:
            self._add_event_markers(ax, df, config)
        
        # Customize the plot
        ax.set_title(metadata.title, fontsize=config.title_fontsize)
        ax.set_xlabel('Time', fontsize=config.label_fontsize)
        ax.set_ylabel(metadata.y_label, fontsize=config.label_fontsize)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save if requested
        if save_file:
            self._save_static_plot(fig, column_enum, output_dir, config)
        
        logger.info(f"Static plot created for {column_enum.value}")
        return fig
    
    def create_multiple_plots(self, df: pd.DataFrame, 
                            columns: Optional[List[Union[str, SignalColumn]]] = None,
                            save_file: bool = False, output_dir: Optional[Path] = None,
                            show_plots: bool = True) -> List[plt.Figure]:
        """
        Create multiple static plots.
        
        Args:
            df: DataFrame containing vital signs data
            columns: List of columns to plot. Uses all vital sign columns if None.
            save_file: Whether to save plots to files
            output_dir: Directory to save plots
            show_plots: Whether to display plots
            
        Returns:
            List of matplotlib Figure objects
        """
        if columns is None:
            columns = [SignalColumn.DBP, SignalColumn.SBP, SignalColumn.HR]
        
        figures = []
        for column in columns:
            try:
                fig = self.create_plot(df, column, save_file=save_file, 
                                     output_dir=output_dir, show_events=True)
                figures.append(fig)
                
                if show_plots:
                    plt.show()
                    
            except Exception as e:
                logger.error(f"Failed to create plot for {column}: {e}")
                continue
        
        return figures
    
    def _add_event_markers(self, ax: plt.Axes, df: pd.DataFrame, 
                          config: StaticPlotConfig) -> None:
        """Add event markers to the plot."""
        event_condition = df[SignalColumn.EVENT.value].notna()
        
        for index in df[event_condition].index:
            ax.axvline(x=index, color=config.event_line_color, 
                      linestyle=config.event_line_style, 
                      linewidth=config.event_line_width)
            
            y_pos = ax.get_ylim()[1] * 0.95  # Position text slightly below top
            event_value = df.loc[index, SignalColumn.EVENT.value]
            
            ax.text(index, y_pos, str(event_value), 
                   rotation=90, va='top', ha='left', color='black', 
                   fontsize=config.event_text_fontsize, 
                   fontweight=config.event_text_weight,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    def _save_static_plot(self, fig: plt.Figure, column: SignalColumn, 
                         output_dir: Optional[Path], config: StaticPlotConfig) -> None:
        """Save static plot to file."""
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{column.value.replace('/', '_')}_plot.{config.save_format}"
        filepath = output_dir / filename
        
        fig.savefig(filepath, dpi=config.save_dpi, bbox_inches='tight')
        logger.info(f"Plot saved as {filepath}")


class InteractivePlotVisualizer(VitalSignsVisualizer):
    """Handles creation of interactive Bokeh-based plots."""
    
    def _validate_data_requirements(self) -> None:
        """Validate Bokeh and Panel availability."""
        try:
            import bokeh
            import panel as pn
        except ImportError:
            raise ImportError("bokeh and panel are required for interactive plots")
    
    def create_plot(self, df: pd.DataFrame, column: Union[str, SignalColumn],
                   show_nans: bool = False, save_file: bool = False,
                   output_dir: Optional[Path] = None, serve_plot: bool = True) -> figure:
        """
        Create an interactive plot for vital signs data.
        
        Args:
            df: DataFrame containing vital signs data
            column: Column to plot
            show_nans: Whether to show NaN regions as vertical lines
            save_file: Whether to save plot as HTML file
            output_dir: Directory to save files
            serve_plot: Whether to serve the plot with Panel
            
        Returns:
            Bokeh figure object
        """
        self._validate_dataframe(df)
        column_enum = self._normalize_column_name(column)
        
        if column_enum.value not in df.columns:
            raise ValueError(f"Column {column_enum.value} not found in DataFrame")
        
        metadata = PlotMetadata.get_metadata(column_enum)
        config = self.config.interactive_config
        
        # Prepare data
        df_clean = self._prepare_data_for_bokeh(df)
        source = ColumnDataSource(df_clean)
        
        # Create plot
        p = self._create_bokeh_figure(metadata, config)
        
        # Add main line plot
        p.line(x='index', y=column_enum.value, source=source, 
               color=metadata.color, line_width=config.line_width, 
               legend_label=column_enum.value)
        
        # Add hover tool
        self._add_hover_tool(p, column_enum, config)
        
        # Add NaN indicators if requested
        if show_nans:
            self._add_nan_indicators(p, df, column_enum, config)
        
        # Customize plot
        self._customize_bokeh_plot(p, metadata)
        
        # Save if requested
        if save_file:
            self._save_interactive_plot(p, column_enum, output_dir)
        
        # Serve plot if requested
        if serve_plot:
            pn.serve(p, show=True)
        
        logger.info(f"Interactive plot created for {column_enum.value}")
        return p
    
    def _prepare_data_for_bokeh(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame for Bokeh plotting."""
        df_clean = df.copy()
        
        # Ensure index is datetime-like for Bokeh
        if not isinstance(df_clean.index, pd.DatetimeIndex):
            if hasattr(df_clean.index, 'time'):
                # Convert time index to datetime
                df_clean.index = pd.to_datetime(df_clean.index, format='%H:%M:%S')
            else:
                # Create a datetime index
                df_clean.index = pd.date_range(
                    start=datetime.now().date(),
                    periods=len(df_clean),
                    freq='2s'
                )
        
        # Reset index to make it a column for Bokeh
        df_clean = df_clean.reset_index()
        return df_clean
    
    def _create_bokeh_figure(self, metadata: PlotMetadata, 
                           config: InteractivePlotConfig) -> figure:
        """Create base Bokeh figure."""
        return figure(
            x_axis_type="datetime",
            height=config.plot_height,
            width=config.plot_width,
            title=metadata.title,
            tools=config.tools
        )
    
    def _add_hover_tool(self, p: figure, column: SignalColumn, 
                       config: InteractivePlotConfig) -> None:
        """Add hover tool to the plot."""
        hover = HoverTool(
            tooltips=[
                ("Time", "@index{%H:%M:%S}"),
                (column.value, f"@{{{column.value}}}{{0.000}}")
            ],
            formatters={
                "@index": "datetime",
                f"@{column.value}": "printf"
            },
            mode=config.hover_mode
        )
        p.add_tools(hover)
    
    def _add_nan_indicators(self, p: figure, df: pd.DataFrame, 
                          column: SignalColumn, config: InteractivePlotConfig) -> None:
        """Add vertical lines to indicate NaN regions."""
        nan_regions = df[column.value].isna()
        vertical_lines = []
        
        # Find start and end of NaN regions
        for i in range(1, len(nan_regions)):
            if nan_regions.iloc[i] and not nan_regions.iloc[i - 1]:
                vertical_lines.append(df.index[i])
            elif not nan_regions.iloc[i] and nan_regions.iloc[i - 1]:
                vertical_lines.append(df.index[i - 1])
        
        # Add vertical lines
        y_min = df[column.value].min()
        y_max = df[column.value].max()
        
        for x in vertical_lines:
            p.line([x, x], [y_min, y_max], 
                  color=config.nan_line_color, 
                  line_width=config.nan_line_width,
                  alpha=0.7)
    
    def _customize_bokeh_plot(self, p: figure, metadata: PlotMetadata) -> None:
        """Apply final customizations to Bokeh plot."""
        # Set up time formatter
        formatter = DatetimeTickFormatter(
            milliseconds="%H:%M:%S.%3N",
            seconds="%H:%M:%S",
            minutes="%H:%M:%S",
            hours="%H:%M:%S",
            days="%H:%M:%S",
            months="%H:%M:%S",
            years="%H:%M:%S"
        )
        
        p.xaxis.formatter = formatter
        p.xaxis.axis_label = 'Time'
        p.yaxis.axis_label = metadata.y_label
        p.legend.location = "top_left"
        p.legend.click_policy = "hide"
    
    def _save_interactive_plot(self, p: figure, column: SignalColumn, 
                             output_dir: Optional[Path]) -> None:
        """Save interactive plot as HTML file."""
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{column.value.replace('/', '_')}_interactive_plot.html"
        filepath = output_dir / filename
        
        output_file(str(filepath))
        save(p)
        logger.info(f"Interactive plot saved as {filepath}")


class VisualizationManager:
    """High-level manager for creating various types of visualizations."""
    
    def __init__(self, config: VisualizationConfig = None):
        """
        Initialize the visualization manager.
        
        Args:
            config: Visualization configuration
        """
        self.config = config or VisualizationConfig()
        self.static_visualizer = StaticPlotVisualizer(self.config)
        self.interactive_visualizer = InteractivePlotVisualizer(self.config)
    
    def create_dashboard(self, df: pd.DataFrame, 
                        columns: Optional[List[Union[str, SignalColumn]]] = None,
                        plot_type: PlotType = PlotType.STATIC,
                        save_files: bool = False,
                        output_dir: Optional[Path] = None) -> List:
        """
        Create a dashboard with multiple plots.
        
        Args:
            df: DataFrame containing vital signs data
            columns: Columns to plot
            plot_type: Type of plots to create
            save_files: Whether to save plots
            output_dir: Output directory for saved files
            
        Returns:
            List of plot objects
        """
        if columns is None:
            columns = [SignalColumn.DBP, SignalColumn.SBP, SignalColumn.HR]
        
        plots = []
        
        for column in columns:
            try:
                if plot_type == PlotType.STATIC:
                    plot = self.static_visualizer.create_plot(
                        df, column, save_file=save_files, output_dir=output_dir
                    )
                else:  # INTERACTIVE
                    plot = self.interactive_visualizer.create_plot(
                        df, column, save_file=save_files, output_dir=output_dir,
                        serve_plot=False
                    )
                
                plots.append(plot)
                
            except Exception as e:
                logger.error(f"Failed to create {plot_type.value} plot for {column}: {e}")
                continue
        
        logger.info(f"Dashboard created with {len(plots)} plots")
        return plots


# Convenience functions for backward compatibility
def static_plot_vitals(df: pd.DataFrame, save_file: bool = False) -> None:
    """
    Create static plots for vital signs data (backward compatibility).
    
    Args:
        df: DataFrame containing vital signs data
        save_file: Whether to save plots to files
    """
    visualizer = StaticPlotVisualizer()
    visualizer.create_multiple_plots(df, save_file=save_file, show_plots=True)


def create_dynamic_time_series_plot(df: pd.DataFrame, column_name: str, *,
                                   show_nans: bool = False, 
                                   file_save: bool = False) -> None:
    """
    Create interactive time series plot (backward compatibility).
    
    Args:
        df: DataFrame containing vital signs data
        column_name: Name of column to plot
        show_nans: Whether to show NaN regions
        file_save: Whether to save plot to HTML file
    """
    visualizer = InteractivePlotVisualizer()
    visualizer.create_plot(df, column_name, show_nans=show_nans, 
                          save_file=file_save, serve_plot=True)


if __name__ == "__main__":
    print(__doc__)
else:
    logger.info(f"Module {repr(__name__)} imported successfully!")