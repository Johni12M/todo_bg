import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_weather_info(now):
    api_key = os.getenv("tomorrowio")
    if not api_key:
        logging.error("TOMORROWIO environment variable not set.")
        return "Error: TOMORROWIO environment variable not set."

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.gps-coordinates.net/my-location")
        driver.execute_cdp_cmd("Browser.grantPermissions", {
            "origin": driver.current_url,
            "permissions": ["geolocation"]
        })
        time.sleep(5)
        coords = {
            "addr": driver.find_element(By.ID, "addr").text,
            "lng": driver.find_element(By.ID, "lng").text,
            "lat": driver.find_element(By.ID, "lat").text
        }
        if not coords["addr"]:
            logging.error("Could not retrieve GPS coordinates.")
            return "Error: Could not retrieve GPS coordinates."

        match_city = re.search(r'\d{4}\s([a-zA-Z]+)', coords["addr"])
        city_name = match_city.group(1) if match_city else "Unknown"

        # Log the extracted city name
        logging.info(f"Extracted city name: {city_name}")

        url_realtime = f"https://api.tomorrow.io/v4/weather/realtime?location={city_name.lower()}&apikey={api_key}&units=metric"
        url_forecast = f"https://api.tomorrow.io/v4/weather/forecast?location={city_name.lower()}&apikey={api_key}&units=metric&timesteps=1d&timezone=auto"
        response_realtime = requests.get(url_realtime)
        response_forecast = requests.get(url_forecast)
        response_realtime.raise_for_status()
        response_forecast.raise_for_status()

        data_realtime = response_realtime.json()
        data_forecast = response_forecast.json()
        print(data_forecast)
        # Log the API responses for debugging
        logging.debug(f"Realtime Weather Data: {data_realtime}")
        logging.debug(f"Forecast Weather Data: {data_forecast}")

        # Safely extract data with default values
        temperature = data_realtime.get('data', {}).get('values', {}).get('temperature', 'N/A')
        cloud_cover = data_realtime.get('data', {}).get('values', {}).get('cloudCover', 'N/A')
        forecast_temp = data_forecast.get('data', {}).get('values', {}).get('temperature', 'N/A')
        forecast_rain = data_forecast.get('data', {}).get('values', {}).get('precipitationProbability', 'N/A')

        # Fallback for missing forecast data
        if forecast_temp == 'N/A' or forecast_rain == 'N/A':
            logging.warning("Forecast data is missing or incomplete. Falling back to default values.")
            forecast_temp = "Data unavailable"
            forecast_rain = "Data unavailable"

        if temperature == 'N/A' or cloud_cover == 'N/A':
            logging.warning("Missing or incomplete realtime weather data.")
        if forecast_temp == 'N/A' or forecast_rain == 'N/A':
            logging.warning("Missing or incomplete forecast weather data.")

        weather_str = f"Wetter in {city_name}: {temperature}°C, Bewölkung: {cloud_cover}%"
        forecast_str = f"Wettervorhersage für {city_name}: {forecast_temp}, {forecast_rain}% Regenwahrscheinlichkeit"
        logging.info(weather_str)
        logging.info(forecast_str)
        return f"{weather_str}, Stand: {now}", forecast_str

    except requests.RequestException as e:
        logging.error(f"Error fetching weather data: {e}")
        return f"Error fetching weather data: {e}"
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return f"An error occurred: {e}"
    finally:
        driver.quit()

if __name__ == "__main__":
    weather_info = get_weather_info(datetime.now())
    print(weather_info[0])
    print(weather_info[1])