import webuntis
from datetime import datetime, timedelta, date
import os

# Zugangsdaten und Schul-Info
username = "metzjon"
password = os.getenv("WEBUNTIS_PASSWORD")  # Passwort aus Umgebungsvariablen
school = "bg-brg-keimgasse"
baseurl = "https://neilo.webuntis.com"  # WebUntis-URL deiner Schule

# Session starten
session = webuntis.Session(
    username=username,
    password=password,
    school=school,
    useragent='WebUntisPython',
    server=baseurl
).login()

morgen = datetime.now() + timedelta(days=1)

heute = datetime.now()

timetable = session.my_timetable(
    start=heute,
    end=heute
)

sorted_timetable = sorted(timetable, key=lambda lesson: lesson.start)

# Stunden anzeigen
for lesson in sorted_timetable:
    if lesson.code == 'cancelled':
        continue  # Überspringt ausgefallene Stunden

    start = lesson.start.strftime('%H:%M')
    end = lesson.end.strftime('%H:%M')
    subject = lesson.subjects[0].name #if lesson.subjects else "Kein Fach"
    room = lesson.rooms[0].name #if lesson.rooms else "Kein Raum"

    print(f"{start} - {end}: {subject} in {room}")

holidays = [
    f"{h.name}: {h.start.strftime('%d.%m.%Y')} - {h.end.strftime('%d.%m.%Y')}"
    for h in sorted(session.holidays(), key=lambda x: x.start)
    if h.end.date() > datetime.now().date()
]

print("\n".join(holidays))

# Session beenden
session.logout()