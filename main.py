import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import ctypes
import winreg
import emoji
import logging
from PIL import Image, ImageDraw, ImageFont
import webuntis
from datetime import datetime, timedelta
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Konstanten und Einstellungen (wie in deinem Original-Code)
APP_PATH = os.path.abspath(os.path.dirname(__file__))
FONT_FOLDER = os.path.join(APP_PATH, "fonts")
FONT_NAME = "NotoColorEmoji_WindowsCompatible.ttf"
BACKGROUND_PATH = os.path.join(APP_PATH, "background", "old.png")
TODO_PATH = os.path.join(APP_PATH, "todo.md")
OUTPUT_DIR = os.path.join(APP_PATH, 'output')
OUTPUT_IMAGE_PATH = os.path.join(OUTPUT_DIR, 'background.png')

# Logging-Konfiguration (wie in deinem Original-Code)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("wallpaper.log"),
        logging.StreamHandler()
    ]
)

# Funktionen (wie in deinem Original-Code)
def load_font():
    """Loads the font with automatic error handling"""
    font_paths = [
        #os.path.join(FONT_FOLDER, FONT_NAME),  # Primary path
        "C:\\Windows\\Fonts\\seguiemj.ttf"     # Windows fallback
    ]
    
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size=32, encoding="unic")
        except Exception as e:
            logging.warning(f"Font not found or other error: {path}")
    
    logging.error("No working font found!")
    return ImageFont.load_default()

def manage_log_file():
    log_file = "wallpaper.log"
    if not os.path.exists(log_file):
        return

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) > 5000:
        # Remove first 1000 lines
        with open(log_file, "w", encoding="utf-8") as f:
            f.writelines(lines[1000:])

#---------------------------
# Code for printing weather
#---------------------------   

def get_weather_by_location(now):
    logging.info("Starting weather data retrieval...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)  # Set a timeout to prevent hanging

    api_key = os.getenv("tomorrowio")
    if not api_key:
        return "Error: TOMORROWIO environment variable not set."

    try:
        logging.info("Accessing location service...")
        driver.get("https://www.gps-coordinates.net/my-location")
        driver.execute_cdp_cmd("Browser.grantPermissions", {
            "origin": driver.current_url,
            "permissions": ["geolocation"]
        })
        
        wait = WebDriverWait(driver, 20)  # Increased timeout to 20 seconds
        
        # Wait for page to fully load before checking elements
        time.sleep(2)
        
        logging.info("Waiting for location data...")
        try:
            # First get the element references (without .text)
            addr_element = wait.until(EC.presence_of_element_located((By.ID, "addr")))
            # Then wait until it has non-empty text
            wait.until(lambda d: addr_element.text.strip() != "")
            addr = addr_element.text
            
            lng_element = wait.until(EC.presence_of_element_located((By.ID, "lng")))
            lat_element = wait.until(EC.presence_of_element_located((By.ID, "lat")))
            
            lng = lng_element.text
            lat = lat_element.text
            
            logging.info(f"Location retrieved: {addr}")
        except Exception as e:
            logging.error(f"Timeout waiting for location elements: {e}")
            return "Wetter: Standort konnte nicht ermittelt werden."
        
        if not addr:
            logging.error("Empty location data received")
            return "Error: Could not retrieve GPS coordinates"

        city = re.search(r'\d{4}\s([a-zA-ZäöüÄÖÜß]+)', addr)
        if not city:
            # Try alternate pattern for city extraction
            city = re.search(r'([a-zA-Z]+)', addr)
            
        city = city.group(1) if city else "Unknown"
        logging.info(f"Using city: {city}")
        
        # Use address directly if city extraction fails
        location = city.lower() if city != "Unknown" else addr
        
        logging.info(f"Retrieving weather for {location}...")
        url = f"https://api.tomorrow.io/v4/weather/realtime?location={location}&apikey={api_key}&fields=temperature,cloudCover&units=metric"
        response = requests.get(url, timeout=15)  # Increased timeout to 15 seconds
        response.raise_for_status()
        data = response.json()
        print(data)
        temperature = data['data']['values']['temperature']
        condition = data['data']['values']['cloudCover']
        weather = f"Wetter in {city}: {temperature}°C, Bewölkung: {condition}%\n\nStand: {now}"
        
        logging.info("Weather data successfully retrieved")
        return weather
    
    except requests.RequestException as e:
        logging.error(f"Error fetching weather data: {e}")
        return f"Error fetching weather data: {e}"
    except Exception as e:
        logging.error(f"Weather error: {e}")
        return f"An error occurred: {e}"
    finally:
        try:
            driver.quit()
            logging.info("Weather browser closed")
        except:
            pass

# --------------------------
# WALLPAPER FUNCTIONALITY
# --------------------------
def set_wallpaper(image_path):
    """Changes the Windows wallpaper"""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Control Panel\\Desktop",
            0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, "Wallpaper", 0, winreg.REG_SZ, image_path)
        
        SPI_SETDESKWALLPAPER = 20
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, image_path, 3)
        logging.info("Wallpaper changed successfully")
    except Exception as e:
        logging.error(f"Error changing wallpaper: {str(e)}")

def process_todos():
    """Processes the to-do list"""
    try:
        with open(TODO_PATH, encoding='utf-8') as file:
            todos = [emoji.emojize(line.rstrip(), language='alias') for line in file]
    except FileNotFoundError:
        logging.error(f"To-do file not found: {TODO_PATH}")
        return []

    processed = []
    mark_done = False
    done_indent_level = -1

    for raw_line in todos:
        # Initialize variables
        prefix = task_text = ""
        is_checked = should_strikethrough = False

        # Processing steps
        indent_level = len(raw_line) - len(raw_line.lstrip('\t'))
        todo_item = raw_line.lstrip('\t')

        # Checkbox processing
        if todo_item.startswith("- [x]"):
            is_checked = True
            text = todo_item.replace("- [x]", "-").strip()
        elif todo_item.startswith("- [ ]"):
            text = todo_item.replace("- [ ]", "-").strip()
        else:
            text = todo_item.strip()

        # Text formatting
        if text.startswith("-"):
            parts = text.split(" ", 1)
            prefix = parts[0]
            task_text = parts[1] if len(parts) > 1 else ""
        else:
            task_text = text
        
        # NOT WORKING: EXPIRING TASKS
        # Check for expiration dates - FIXED: moved after task_text is defined
        # date_match = re.search(r"- \[.\] (\d{2})\.(\d{2})\.(\d{4}):", raw_line)
        # if date_match:
        #     try:
        #         # Extract just the date part from the match
        #         day = date_match.group(1)
        #         month = date_match.group(2)
        #         year = date_match.group(3)
        #         date_str = f"{day}.{month}.{year}"

        #         exp_date = datetime.strptime(date_str, "%d.%m.%Y").date()

        #         if exp_date < datetime.now().date():
        #             continue  # Skip expired tasks

        #         task_text = task_text.replace(date_match.group(0), "", 1)  # Remove full match
        #     except ValueError:
        #         print(f"Invalid date: {date_str}")
        
        # Done status
        if is_checked:
            if indent_level == 0:
                mark_done = True
                done_indent_level = indent_level
            else:
                done_indent_level = indent_level
                mark_done = True
                should_strikethrough = True
        
        if mark_done and indent_level > done_indent_level:
            is_checked = True
            should_strikethrough = True

        # Calculate length of the formatted text
        formatted_text = f"{prefix} {task_text}"
        tab_count = formatted_text.count('\t')
        formatted_length = len(formatted_text) + (tab_count * 3)  # Each tab is 4 characters, so add 3 for each

        if formatted_length > 55:
            try:
                space_index = task_text[50:].index(" ") + 50
                first_part = task_text[0:space_index]
                second_part = task_text[space_index:]

                processed.append((prefix, first_part, is_checked, indent_level, should_strikethrough))
                processed.append(("", second_part, is_checked, indent_level + 0.25, should_strikethrough))
                continue

            except ValueError:
                task_text = task_text[:55]
                #task_text = task_text[:55] + "\n  " + task_text[55:]

        processed.append((prefix, task_text, is_checked, indent_level, should_strikethrough))
        if not is_checked:
            mark_done = False

    return processed

def time_table(weather_data):
    """Fetches the timetable"""
    # Zugangsdaten und Schul-Info
    username = "metzjon"
    password = os.getenv("WEBUNTIS_PASSWORD")  # Passwort aus Umgebungsvariablen
    school = "bg-brg-keimgasse"
    baseurl = "https://neilo.webuntis.com"  # WebUntis-URL deiner Schule

    try:
        # Session starten
        session = webuntis.Session(
            username=username,
            password=password,
            school=school,
            useragent='WebUntisPython',
            server=baseurl
        ).login()

        heute = datetime.now() + timedelta(days=0)   

        timetable = session.my_timetable(
            start=heute,
            end=heute
        )
        
        sorted_timetable = sorted(timetable, key=lambda lesson: lesson.start)
        
        lessons = []
        sorted_timetable = sorted(timetable, key=lambda lesson: lesson.start)

        # Anfang des Schultages
        school_day_start = datetime.combine(heute.date(), datetime.strptime("08:00", "%H:%M").time())
        previous_end = school_day_start
        for lesson in sorted_timetable:
            if lesson.code == 'cancelled':
                continue

            start = lesson.start
            end = lesson.end
            subject = lesson.subjects[0].name if lesson.subjects else "Kein Fach"
            room = lesson.rooms[0].name if lesson.rooms else "Kein Raum"

            # Freistunde vor dieser Stunde?
            if (start - previous_end).total_seconds() > 15 * 60:
                lessons.append(f"{previous_end.strftime('%H:%M')} - {start.strftime('%H:%M')}: FREI!!!")
    
            lessons.append(f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}: {subject} in {room}")
            previous_end = end
            
        if not lessons:
            # Falls keine Stunden vorhanden sind (z. B. ein ferienähnlicher Tag)
            lessons.append("Heute ist schulfrei!!! :-)")
        
        holidays = [
            f"{h.name}: {h.start.strftime('%d.%m.%Y')}" if h.start.date() == h.end.date()
            else f"{h.name}: {h.start.strftime('%d.%m.%Y')} - {h.end.strftime('%d.%m.%Y')}"
            for h in sorted(session.holidays(), key=lambda x: x.start)
            if h.end.date() > datetime.now().date()
        ]
        
        future_holidays = [h for h in session.holidays() if h.end.date() >= datetime.now().date()]
        if future_holidays:
            next_holiday = sorted(future_holidays, key=lambda x: x.start)[0]
            days_until = (next_holiday.start.date() - datetime.now().date()).days
            
        # Get weather data explicitly before building the holidays_info list
        logging.info("Fetching weather data...")
        logging.info("Weather data fetched")

        holidays_info = ["Nächsten 10 Ferien/Feiertage:\n"]
        for i, holiday in enumerate(holidays):
            if i < 10:
                holidays_info.append(holiday)
            else:
                break
        
        next_holiday_text = f'\n{next_holiday.name}: Wie gesagt, es ist gerade frei!\n(Ja, man muss das zweimal sagen ;) )' if next_holiday.start.date() <= datetime.now().date() <= next_holiday.end.date() else f'{next_holiday.start.strftime("%d.%m.%Y")}\nIn {days_until} Tag(en)'
        
        holidays_info.append(f"\nNächste(r) Ferien/Feiertag: {next_holiday_text}\n\nWetter an deinem (nicht wirklich genauen) Standort:\n{weather_data}")

        # Session beenden
        session.logout()
        return lessons, holidays_info

    except Exception as e:
        logging.error(f"Error fetching timetable: {str(e)}")
        return []

def create_wallpaper_image(todos, timetable, background_path=BACKGROUND_PATH):
    """Creates the wallpaper image with todos on the left and timetable on the right."""
    try:
        image = Image.open(background_path) 
        #print(f"Background image mode: {image.mode}, size: {image.size}")
        
        # Convert to RGBA if not already
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
            #print(f"Converted image to RGBA mode from {image.mode}")
    except FileNotFoundError:
        logging.error(f"Background image not found: {background_path}")
        return None

    fnt = load_font()
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Layout settings
    line_spacing = 37
    todo_line_spacing = 32

    # Positioning for Todos
    todo_x_offset = 850  # Abstand vom linken Rand

    # Positioning for Timetable (links oben)
    timetable_x_offset = 850
    timetable_h_start = 50

    # Positioning for holidays (oben rechts)
    holidays_x_offset = 50  # Abstand vom rechten Rand
    holidays_h_start = 50

    # Render Timetable
    for i, lesson in enumerate(timetable[0]):
        y = timetable_h_start + i * line_spacing
        x = timetable_x_offset

        color = (255, 255, 255)
        draw.text((x, y), lesson, font=fnt, fill=color)

    # Dynamischer Abstand nach dem Stundenplan
    last_timetable_y = timetable_h_start + len(timetable[0]) * line_spacing
    
    # Calculate the 1/3 position of the screen for todos
    two_fifth_of_the_screen= 2* (height // 5)  
    
    # Position todos at 1/3 of screen or below timetable with 50px gap, whichever is lower
    todo_h_start = max(two_fifth_of_the_screen, last_timetable_y + 13)

    # Render Todos
    line_count = 0
    for i, (prefix, text, checked, indent, strike) in enumerate(todos):
        y = todo_h_start + line_count * todo_line_spacing
        x = todo_x_offset + indent * 40
        
        color = (180, 180, 180) if checked else (255, 255, 255)
        draw.text((x, y), f"{prefix} {text}", font=fnt, fill=color, embedded_color=True)
        
        if strike:
            text_width = draw.textlength(f"{prefix} {text}", font=fnt)
            draw.line((x, y+15, x+text_width, y+15), fill=color, width=2)
        
        line_count += 1

    # Render Holidays
    for i, holiday in enumerate(timetable[1]):
        y = holidays_h_start + i * (line_spacing+20)
        x = holidays_x_offset
        
        color = (255, 255, 255)
        draw.text((x, y), holiday, font=fnt, fill=color)

    return image

wallpaper_lock = threading.Lock()

def wallpaper():
    """Main function to create the wallpaper"""

    #manage_log_file() # Ensure log file is not longer than 5000 lines

    with wallpaper_lock:  # Use lock to prevent concurrent updates
        now = datetime.now().strftime('%H:%M:%S')
        todos = process_todos()
        
        try:
            weather_data = get_weather_by_location(now)
            timetable_data = time_table(weather_data)  # This now waits for weather data to complete
            
            if not todos and not timetable_data:
                logging.warning("No todo items or timetable data to display")
                return

            image = create_wallpaper_image(todos=todos, timetable=timetable_data)
            if not image:
                return

            os.makedirs(OUTPUT_DIR, exist_ok=True)
            image.save(OUTPUT_IMAGE_PATH)
            time.sleep(1)
            set_wallpaper(OUTPUT_IMAGE_PATH)
            logging.info("Wallpaper updated successfully with weather data")
        
        except Exception as e:
            logging.error(f"Error in wallpaper update: {str(e)}")

# --------------------------
# FILE MONITORING
# --------------------------
class TodoFileHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_modified = 0

    def on_modified(self, event):
        if not event.is_directory and os.path.abspath(event.src_path) == TODO_PATH:
            current_time = time.time()
            if current_time - self.last_modified > 2:  # Uncomment this
                self.last_modified = current_time
                logging.info("Change detected - updating wallpaper")
                threading.Thread(target=wallpaper).start()  # Run in thread to avoid blocking

def watch():
    """Starts the file monitor"""
    observer = Observer()
    observer.schedule(TodoFileHandler(), path=APP_PATH, recursive=False)
    observer.start()
    logging.info(f"Watching file: {TODO_PATH}")

    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# --------------------------
# Automatische Aktualisierung alle 2 Minuten
# --------------------------
def auto_update():
    while True:
        logging.info("Automatisches Update des Wallpapers...")
        wallpaper()
        time.sleep(240)  # Warte 4 Minuten (240 Sekunden)

# --------------------------
# MAIN PROGRAM
# --------------------------
if __name__ == "__main__":
    logging.info("Starting wallpaper engine...")
    #print(f"Font folder exists: {os.path.exists(FONT_FOLDER)}")
    #print(f"Font file exists: {os.path.exists(os.path.join(FONT_FOLDER, FONT_NAME))}")
    #wallpaper()  # Initial execution

    # Starte den Thread für die automatische Aktualisierung
    auto_update_thread = threading.Thread(target=auto_update, daemon=True)
    auto_update_thread.start()
    
    watch()