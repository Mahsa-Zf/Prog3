import matplotlib.pyplot as plt
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool
from bokeh.io import output_file, save
import panel as pn
import pandas as pd
from datetime import datetime

titles = {'Solar8000/ART_DBP':'Arterial Diastolic Blood Pressure During the surgery',
            'Solar8000/ART_SBP':'Arterial Systolic Blood Pressure During the surgery', 
            'Solar8000/HR':'Heart Rate During the surgery'}
y_labels = {'Solar8000/ART_DBP':'Arterial Diastolic Blood Pressure (mmHg)',
                'Solar8000/ART_SBP':'Arterial Systolic Blood Pressure (mmHg)',
                'Solar8000/HR':'Heart Rate (bpm)'}

def static_plot_vitals(df, save_file=False):
    """
    Generates static plots for the Solar8000 dataset, including heart rate and blood pressure.
    Each plot includes vertical lines for non-null EVENT values, with the EVENT value displayed next to the line.
    Optionally saves the plot to a file.

    Args:
        df (pd.DataFrame): DataFrame containing the Solar8000 dataset with a DatetimeIndex.
        save_file (bool): Whether to save the plot to a file.
        file_name (str or None): File name or path to save the plot. If None and save_file is True,
                                 a default name will be generated for each plot.
    """

    for col in ['Solar8000/ART_DBP', 'Solar8000/ART_SBP', 'Solar8000/HR']:
        fig, ax = plt.subplots(figsize=(15, 5))
        df.plot(y=col, ax=ax)

        # Add vertical lines and labels for non-null EVENT values
        condition = df['EVENT'].notna()
        for index in df[condition].index:
            ax.axvline(x=index, color='r', linestyle='--', linewidth=1)
            y_pos = ax.get_ylim()[1]
            event_value = df.loc[index, 'EVENT']
            ax.text(index, y_pos, str(event_value), 
                    rotation=90, va='top', ha='left', color='k', fontsize=10, fontweight='bold')

        ax.set_title(f'{titles[col]}', fontsize=16)
        ax.set_xlabel('Time(Hour)', fontsize=12)
        ax.set_ylabel(f'{y_labels[col]}', fontsize=12)
        plt.tight_layout()

        if save_file:
            file_name = f"{col.replace('/', '_')}_plot.png"
            fig.savefig(file_name)
            print(f"Plot saved as {file_name}")

        plt.show()


def create_dynamic_time_series_plot(df, column_name, *, show_nans= False, file_save = False):
    """
    Generates an interactive time series plot for a specified column in a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with a DatetimeIndex and the column to plot.
        column_name (str): Name of the column to plot.
        show_nans (bool): If True, show vertical lines for NaN regions.
        file_save (bool): If True, save the plot to an HTML file.
        output_filename (str): Name of the HTML file to save the plot to.
    """

    # Create ColumnDataSource
    source = ColumnDataSource(df)

    # DatetimeTickFormatter for time display only
    formatter = DatetimeTickFormatter(
        milliseconds="%H:%M:%S.%3N",
        seconds="%H:%M:%S",
        minutes="%H:%M:%S",
        hours="%H:%M:%S",
        days="%H:%M:%S",
        months="%H:%M:%S",
        years="%H:%M:%S"
    )

    # Main plot
    p = figure(x_axis_type="datetime",
               height=350, width=800,
               title=f"{column_name} Time Series",
               tools="pan,wheel_zoom,box_zoom,reset")

    # Add HoverTool with time-only format
    hover = HoverTool(
        tooltips=[
            ("Time", "@index{%H:%M:%S}"),
            (column_name, f"@{{{column_name}}}{{0.000}}")
        ],
        formatters={
            "@index": "datetime",
            f"@{column_name}": "printf"
        },
        mode="vline"
    )
    
    p.add_tools(hover)

    # Add line plot
    p.line(x='index', y=column_name, source=source, color="navy", line_width=2, legend_label=column_name)

    # Draw vertical lines for NaN regions
    if show_nans:
        # Identify NaN regions and calculate vertical line positions
        nan_regions = df[column_name].isna()
        vertical_lines = []
        for i in range(1, len(nan_regions)):
            if nan_regions.iloc[i] and not nan_regions.iloc[i - 1]:  # Start of NaN region
                vertical_lines.append(df.index[i])
            elif not nan_regions.iloc[i] and nan_regions.iloc[i - 1]:  # End of NaN region
                vertical_lines.append(df.index[i - 1])
        for x in vertical_lines:
            p.line([x, x], [df[column_name].min(), df[column_name].max()], color="red", line_width=2)

    # Axis labels
    p.xaxis.axis_label = 'Time'
    p.yaxis.axis_label = f'{y_labels[column_name]}'
    p.title = f'{titles[column_name]}'
    p.legend.location = "top_left"
    p.xaxis.formatter = formatter

    # Show the plot
    if file_save:
        file_name = f"{column_name.replace('/', '_')}_plot.html"
        output_file(file_name)  # Output to an HTML file
        save(p)
    pn.serve(p, show=True)  # Serve the plot in a Panel app

if __name__ == "__main__":
    print(__doc__) #__doc__ is the docstring
else:
    print(f"Module {repr(__name__)} is imported successfully!")