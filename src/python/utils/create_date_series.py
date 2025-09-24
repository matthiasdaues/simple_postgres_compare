from datetime import datetime, timedelta

# Function to generate a list of date strings from start_date to end_date (inclusive)
def create_date_series(start_date: str, end_date: str):
    """
    Args:
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        a list of str: List of date strings from start_date to end_date (inclusive) in 'YYYY-MM-DD' format.

    Example:
        * create_date_series("2025-01-01", "2025-01-10")
        * Returns: ['2025-01-01', '2025-01-02', ..., '2025-01-10']
    """
    dates = []
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    while current_date <= end:
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    return dates

