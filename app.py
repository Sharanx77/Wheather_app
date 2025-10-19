import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz # Necessary for accurate time zone handling

# --- Configuration ---
API_KEY = "5a53980184dd4b1e993193b19f7d2d18"
CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

# --- Utility Functions ---

# Use Streamlit's cache to avoid repeated API calls for the same city/unit
@st.cache_data(ttl=600) # Cache for 10 minutes
def get_weather_data(city, unit):
    """Fetches current and 5-day forecast data from OpenWeatherMap."""
    params = {
        'q': city,
        'appid': API_KEY,
        'units': unit # 'metric' for Celsius, 'imperial' for Fahrenheit
    }

    current_response = requests.get(CURRENT_URL, params=params)
    forecast_response = requests.get(FORECAST_URL, params=params)
    
    # Check for success (status code 200)
    if current_response.status_code != 200:
        return {'error': current_response.json().get('message', 'Error fetching current weather data.')}
    if forecast_response.status_code != 200:
        return {'error': forecast_response.json().get('message', 'Error fetching forecast data.')}

    return {
        'current': current_response.json(),
        'forecast': forecast_response.json()
    }

def format_unix_time(timestamp, timezone_offset):
    """Converts a Unix timestamp to a human-readable time string for the local timezone."""
    # datetime.utcfromtimestamp assumes the timestamp is UTC, then we apply the offset
    utc_dt = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
    local_dt = utc_dt + pd.Timedelta(seconds=timezone_offset)
    return local_dt.strftime('%H:%M:%S')

def create_forecast_dataframe(forecast_data, unit_symbol):
    """Processes the 3-hour forecast data into a daily max/min temperature DataFrame."""
    
    # Convert list of 3-hour forecasts to a Pandas DataFrame
    df_list = []
    for entry in forecast_data['list']:
        df_list.append({
            'Time': datetime.fromtimestamp(entry['dt']),
            'Date': datetime.fromtimestamp(entry['dt']).date(),
            f'Temperature ({unit_symbol})': entry['main']['temp'],
            'Weather': entry['weather'][0]['description'].capitalize()
        })
        
    df = pd.DataFrame(df_list)
    
    # Group by date to get daily max/min/average temperature
    daily_forecast = df.groupby('Date').agg(
        Max_Temp=(f'Temperature ({unit_symbol})', 'max'),
        Min_Temp=(f'Temperature ({unit_symbol})', 'min'),
        Weather=('Weather', lambda x: x.iloc[0]) # Take the weather condition from the first entry of the day
    ).reset_index()

    # Only keep the next 5 days (excluding today if the first entry is today's morning)
    # The API gives ~5 days of data, so we limit to 5 entries
    return daily_forecast.head(5)

def get_weather_icon_url(icon_code):
    """Returns the URL for the dynamic weather icon."""
    return f"http://openweathermap.org/img/wn/{icon_code}@2x.png"


# --- Streamlit App Layout ---

st.title("☀️ Real-Time Weather App")

# 1. Input for city names
city_name = st.text_input("Enter City Name", "London").strip()

# 6. Unit toggle (C/F)
unit_option = st.radio(
    "Select Temperature Unit",
    ('Celsius', 'Fahrenheit'),
    horizontal=True
)

if unit_option == 'Celsius':
    unit_param = 'metric'
    unit_symbol = '°C'
elif unit_option == 'Fahrenheit':
    unit_param = 'imperial'
    unit_symbol = '°F'

if st.button("Get Weather", use_container_width=True) and city_name:
    
    with st.spinner(f"Fetching weather for {city_name}..."):
        # 2. Fetch data from OpenWeatherMap
        data = get_weather_data(city_name, unit_param)

    if 'error' in data:
        st.error(f"Could not fetch weather data: {data['error']}")
    else:
        current = data['current']
        forecast = data['forecast']

        # -----------------
        # Current Weather Section (3 & 5)
        # -----------------
        
        st.header(f"Current Weather in {current['name']}, {current['sys']['country']}")
        
        col1, col2 = st.columns([1, 2])
        
        # 5. Dynamic icon and main temp
        with col1:
            icon_code = current['weather'][0]['icon']
            icon_url = get_weather_icon_url(icon_code)
            st.image(icon_url, width=150)
            
        with col2:
            current_temp = current['main']['temp']
            weather_desc = current['weather'][0]['description'].capitalize()
            
            st.markdown(f"## {current_temp:.1f} {unit_symbol}")
            st.markdown(f"**Condition:** {weather_desc}")

        st.divider()

        # Detailed Stats (3)
        st.subheader("Detailed Stats")
        col3, col4, col5, col6 = st.columns(4)

        # Humidity
        col3.metric("Humidity", f"{current['main']['humidity']}%")

        # Feels Like
        col4.metric("Feels Like", f"{current['main']['feels_like']:.1f} {unit_symbol}")

        # Sunrise / Sunset (handling Unix timestamp)
        timezone_offset = current.get('timezone', 0)
        sunrise_time = format_unix_time(current['sys']['sunrise'], timezone_offset)
        sunset_time = format_unix_time(current['sys']['sunset'], timezone_offset)
        
        col5.metric("🌅 Sunrise", sunrise_time)
        col6.metric("🌇 Sunset", sunset_time)
        
        st.divider()

        # -----------------
        # Forecast Section (4)
        # -----------------
        
        st.header("5-Day Forecast")
        
        # 4. Add 5-day forecast chart
        df_forecast = create_forecast_dataframe(forecast, unit_symbol)
        
        # Display the line chart
        st.line_chart(
            df_forecast, 
            x='Date', 
            y=['Max_Temp', 'Min_Temp'], 
            use_container_width=True
        )

        # Display the data in an expandable table for detail
        with st.expander("View Daily Details"):
            # Rename columns for better display
            df_display = df_forecast.rename(columns={
                'Max_Temp': f'Max Temp ({unit_symbol})',
                'Min_Temp': f'Min Temp ({unit_symbol})'
            })
            st.dataframe(df_display, hide_index=True)

# --- Sample Queries ---
st.sidebar.markdown("---")
st.sidebar.subheader("Sample Queries")
st.sidebar.markdown("- Tokyo, JP")
st.sidebar.markdown("- New York, US")
st.sidebar.markdown("- Sydney, AU")

# --- How to Run ---
st.sidebar.markdown("---")
st.sidebar.subheader("How to Run")

st.sidebar.code("streamlit run weather_app.py")
