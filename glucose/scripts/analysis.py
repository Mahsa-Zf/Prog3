from datetime import datetime

"""
python scripts with functions and or methods to analyse the data.

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