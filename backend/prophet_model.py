import pandas as pd
import logging
from datetime import datetime, timedelta
import database as db

# Attempt to import prophet. If it fails (e.g., due to C++ build tools missing), fallback to a mock.
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not installed. Using mock forecasting.")

logger = logging.getLogger(__name__)

def forecast_attendance(days_ahead: int = 7) -> list[dict]:
    """
    Uses Facebook Prophet machine learning model to forecast gym facility usage 
    based on historical attendance data.
    """
    attendance = db.get_attendance(limit=10000)
    if not attendance:
        return []

    # Prepare data for Prophet: needs 'ds' (datestamp) and 'y' (metric) columns
    date_counts = {}
    for record in attendance:
        date_str = record["date"]
        date_counts[date_str] = date_counts.get(date_str, 0) + 1

    df = pd.DataFrame(list(date_counts.items()), columns=["ds", "y"])
    df['ds'] = pd.to_datetime(df['ds'])
    
    if len(df) < 2:
        logger.warning("Not enough historical data to train Prophet. Returning fallback.")
        return [
            {"date": (datetime.today() + timedelta(days=i)).strftime("%Y-%m-%d"), "predicted_attendance": 10} 
            for i in range(1, days_ahead + 1)
        ]

    if PROPHET_AVAILABLE:
        m = Prophet(daily_seasonality=True, yearly_seasonality=False)
        m.fit(df)
        
        future = m.make_future_dataframe(periods=days_ahead)
        forecast = m.predict(future)
        
        # Get only the future predictions
        future_forecast = forecast.tail(days_ahead)
        
        results = []
        for _, row in future_forecast.iterrows():
            results.append({
                "date": row['ds'].strftime("%Y-%m-%d"),
                "predicted_attendance": max(0, int(row['yhat'])) # No negative attendance
            })
        return results
    else:
        # Mock Prophet output for demonstration when library isn't installed
        last_date = df['ds'].max()
        avg_attendance = int(df['y'].mean())
        results = []
        for i in range(1, days_ahead + 1):
            results.append({
                "date": (last_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                "predicted_attendance": max(0, avg_attendance + (i % 5) - 2)
            })
        return results
