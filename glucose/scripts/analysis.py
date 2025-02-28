from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
import warnings
warnings.filterwarnings("ignore")
"""

python scripts with functions and or methods to analyse the data.

Includes:
Interpolator
glucose_smoother_plotter

"""


def interpolator(df, start, end):
    """
    This function linearly interpolates the missing values in the given period
    Input: start and end dates, as strings, formatted Y-M-D
    Output: Interpolated version of the dataset for that period
    """
    start_date = datetime.strptime(start, '%Y-%m-%d').date()
    end_date = datetime.strptime(end, '%Y-%m-%d').date()

    # Create a boolean mask for the date range
    mask = (df['Device Timestamp'].dt.date >= start_date) & (df['Device Timestamp'].dt.date <= end_date)

    # Apply interpolation only to the selected range
    df.loc[mask, 'Historic Glucose mmol/L'] = df.loc[mask, 'Historic Glucose mmol/L'].interpolate(method='linear')

    return df

def glucose_smoother_plotter(df, start, end, window_size, original=True):
    """
    This function cuts the data in the given period, smooths and plots it
    Input: dataframe, start and end dates, as strings, formatted Y-M-D, window size, 
    original=True shows the original unsmoothed data in the plot
    Output: Plot of smoothed data
    """
    start_date = datetime.strptime(start, '%Y-%m-%d').date()
    end_date = datetime.strptime(end, '%Y-%m-%d').date()

    # Create a boolean mask for the date range
    mask = (df['Device Timestamp'].dt.date >= start_date) & (df['Device Timestamp'].dt.date <= end_date)

    # Filter the dataframe
    df_cut = df.loc[mask, :]

    # Rolling average
    df_cut.loc[:, 'Smoothed Glucose'] = df_cut['Historic Glucose mmol/L'].rolling(window=window_size, min_periods=1).mean()

    ####################################### Plotting
    plt.figure(figsize=(18, 6))

    # Plot glucose levels
    plt.plot(df_cut['Device Timestamp'], df_cut['Smoothed Glucose'], color='r', label='Smoothed Glucose')
    if original:
        plt.plot(df_cut['Device Timestamp'], df_cut['Historic Glucose mmol/L'], label='Historic Glucose')

    # Format x-axis to show dates
    ax = plt.gca()
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())  # Major ticks for each day

    # Add vertical dotted lines for each minor tick
    plt.grid(which='major', axis='x', linestyle='--', color='black', alpha=0.8)  

    plt.xlabel('Date')
    plt.ylabel('Glucose Level (mmol/L)')
    plt.title('Glucose Levels over Time')
    plt.legend()

    # Rotate and align the tick labels so they look better
    plt.gcf().autofmt_xdate()

    plt.show()


