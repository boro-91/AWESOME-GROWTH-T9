import time
import csv
import os
from datetime import datetime

import board
import adafruit_dht
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD

# ==========================================
# HARDWARE KONFIGURATION (BCM GPIO Nummern)
# ==========================================
# BOARD 2: KRAFTWERK (Weiss) - Starkstrom
PIN_LUEFTER = 18
PIN_NEBEL_1 = 27

# BOARD 1: ZENTRALE (Schwarz) - Sensoren & Signal
PIN_BODEN = 17
PIN_HEIZUNG = 25

# --- SCHWELLENWERTE ---
TEMP_MAX = 25.0
TEMP_MIN = 22.0

# --- CSV KONFIGURATION ---
CSV_DATEI = "gewaechshaus_log.csv"
CSV_SPALTEN = [
    "zeitstempel",
    "temperatur_c",
    "luftfeuchte_pct",
    "boden_trocken",
    "klima_status",
    "bewaesserung_aktiv",
    "luefter_an",
    "heizung_an",
    "nebel_an"
]

# ==========================================
# SETUP DER HARDWARE
# ==========================================
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([PIN_LUEFTER, PIN_NEBEL_1, PIN_HEIZUNG], GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_BODEN, GPIO.IN)

dht_device = adafruit_dht.DHT22(board.D4, use_pulseio=False)

try:
    lcd = CharLCD('PCF8574', 0x27)
    lcd.clear()
    print("LCD Zentrale: BEREIT")
except:
    lcd = None
    print("LCD Fehler: Verkabelung prüfen.")

# ==========================================
# CSV VORBEREITEN
# ==========================================
datei_existiert = os.path.isfile(CSV_DATEI)

csv_file = open(CSV_DATEI, mode='a', newline='', buffering=1)
csv_writer = csv.writer(csv_file)

# Header nur schreiben, wenn die Datei neu ist
if not datei_existiert:
    csv_writer.writerow(CSV_SPALTEN)
    print(f"Neue Log-Datei erstellt: {CSV_DATEI}")
else:
    print(f"Hänge an bestehende Log-Datei an: {CSV_DATEI}")

print("========================================")
print(" INTELLIGENTES GEWÄCHSHAUS AKTIV")
print(" (Modus: Multi-Tasking + CSV-Logging)")
print("========================================")

letzter_klima_status = ""

try:
    while True:
        try:
            # 1. DATEN LESEN
            temp = dht_device.temperature
            hum = dht_device.humidity
            boden_trocken = (GPIO.input(PIN_BODEN) == GPIO.HIGH)

            if temp is None:
                time.sleep(2)
                continue

            # Variable um Bewässerung zu tracken
            bewaesserung_aktiv = False

            # 2. LCD ANZEIGE
            if lcd:
                try:
                    lcd.clear()
                    lcd.cursor_pos = (0, 0)
                    lcd.write_string(f"T:{temp:.1f}C H:{hum:.0f}%")
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(f"Erde: {'TROCKEN' if boden_trocken else 'FEUCHT'}")
                except OSError:
                    pass

            # 3. GEHIRNHÄLFTE 1: TEMPERATUR-LOGIK
            if temp > TEMP_MAX:
                if letzter_klima_status != "KUEHLEN":
                    print(f"[{temp}°C] ZU WARM! Kühlung startet...")
                    GPIO.output(PIN_HEIZUNG, GPIO.LOW)
                    letzter_klima_status = "KUEHLEN"

                GPIO.output(PIN_LUEFTER, GPIO.HIGH)
                time.sleep(3)
                GPIO.output(PIN_LUEFTER, GPIO.LOW)
                time.sleep(1)
                GPIO.output(PIN_NEBEL_1, GPIO.HIGH)
                time.sleep(5)
                GPIO.output(PIN_NEBEL_1, GPIO.LOW)

            elif temp < TEMP_MIN:
                if letzter_klima_status != "HEIZEN":
                    print(f"[{temp}°C] ZU KALT! Bar-Graph Heizung EIN.")
                    GPIO.output(PIN_LUEFTER, GPIO.LOW)
                    GPIO.output(PIN_HEIZUNG, GPIO.HIGH)
                    letzter_klima_status = "HEIZEN"

            else:
                if letzter_klima_status != "OK":
                    print(f"[{temp}°C] Temperatur ideal.")
                    GPIO.output([PIN_LUEFTER, PIN_HEIZUNG], GPIO.LOW)
                    letzter_klima_status = "OK"

            # 4. GEHIRNHÄLFTE 2: BEWÄSSERUNGS-LOGIK
            if boden_trocken:
                print("BEWÄSSERUNG: Bodenfeuchte kritisch! Vernebler startet...")
                GPIO.output(PIN_NEBEL_1, GPIO.HIGH)
                time.sleep(5)
                GPIO.output(PIN_NEBEL_1, GPIO.LOW)
                print("Bewässerung beendet.")
                bewaesserung_aktiv = True
                time.sleep(2)
            else:
                if letzter_klima_status != "KUEHLEN":
                    GPIO.output(PIN_NEBEL_1, GPIO.LOW)

            # 5. CSV ZEILE SCHREIBEN
            csv_writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                round(temp, 1),
                round(hum, 1),
                boden_trocken,
                letzter_klima_status,
                bewaesserung_aktiv,
                GPIO.input(PIN_LUEFTER),
                GPIO.input(PIN_HEIZUNG),
                GPIO.input(PIN_NEBEL_1)
            ])

            time.sleep(2)

        except RuntimeError:
            time.sleep(2)
            continue

except KeyboardInterrupt:
    print("\nSystem beendet.")

finally:
    csv_file.close()
    GPIO.cleanup()
    if lcd:
        lcd.clear()
    print("Hardware gesichert. CSV-Datei geschlossen.")
