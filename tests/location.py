from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# Chrome-Optionen für präzisere Geolokalisierung
options = Options()
options.add_argument("--headless")  # Headless-Modus für bessere Performance
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")  # Wichtig für Layout-Stabilität

# Headless-Modus für bessere Performance (wenn benötigt)
# options.add_argument("--headless=new")  # Nur aktivieren wenn notwendig

driver = webdriver.Chrome(options=options)

try:
    driver.get("https://www.gps-coordinates.net/my-location")
    
    # Explizite Geolocation-Berechtigung über CDP
    driver.execute_cdp_cmd("Browser.grantPermissions", {
        "origin": driver.current_url,
        "permissions": ["geolocation"]
    })

    # Dynamisches Warten auf Koordinaten-Update
    time.sleep(5)
    
    addr = driver.find_element(By.ID, "addr").text
    lng = driver.find_element(By.ID, "lng").text
    lat = driver.find_element(By.ID, "lat").text

    print(f"Präzise Addresse: {addr}, latitude: {lat}, longitude: {lng}")

finally:
    driver.quit()

