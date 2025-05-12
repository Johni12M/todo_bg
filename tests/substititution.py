import os
from datetime import datetime, timedelta, date
import webuntis

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

    # Stundenplan und Supplierungen holen
    timetable = session.my_timetable(start=heute, end=heute)

    sorted_timetable = sorted(timetable, key=lambda lesson: lesson.start)
    
    lessons = []
    school_day_start = datetime.combine(heute.date(), datetime.strptime("08:00", "%H:%M").time())
    previous_end = school_day_start

    for lesson in sorted_timetable:
        if lesson.code == 'cancelled':
            continue

        start = lesson.start
        end = lesson.end
        subject = lesson.subjects[0].name if lesson.subjects else "Kein Fach"
        room = lesson.rooms[0].name if lesson.rooms else "Kein Raum"
        teacher = lesson.teachers[0].name if lesson.teachers else "Kein Lehrer"

        # Detect substitution
        is_substitution = lesson.code == 'irregular' or getattr(lesson, 'substText', None)
        subst_text = getattr(lesson, 'substText', '') or getattr(lesson, 'info', '')

        vertretungs_info = " (Vertretung)" if is_substitution else ""
        if subst_text:
            vertretungs_info += f" [{subst_text}]"

        lessons.append(f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}: {subject} in {room} bei {teacher}{vertretungs_info}")
    if not lessons:
        lessons.append("Heute ist schulfrei!!! :-)")
        
finally:
    session.logout()
