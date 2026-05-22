import time
import csv
import os
from datetime import datetime

import board
import adafruit_dht
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD
import requests

from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.led_matrix.device import max7219

# ==========================================
# HARDWARE KONFIGURATION (BCM GPIO Nummern)
# ==========================================
# BOARD 2: KRAFTWERK (Weiss) - Starkstrom
PIN_LUEFTER = 18
PIN_NEBEL_1 = 27

# BOARD 1: ZENTRALE (Schwarz) - Sensoren & Signal
PIN_BODEN = 17

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

# --- FIREBASE KONFIGURATION ---
FIREBASE_REGION = "us-central1"
FIREBASE_PROJECT_ID = "awesome-growth-82e6b"
FIREBASE_FUNCTION_URL = "https://us-central1-awesome-growth-82e6b.cloudfunctions.net/submitMeasurement"
DEVICE_ID = "greenhouse-01"

# ==========================================
# SETUP DER HARDWARE
# ==========================================
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([PIN_LUEFTER, PIN_NEBEL_1], GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(PIN_BODEN, GPIO.IN)

dht_device = adafruit_dht.DHT22(board.D4, use_pulseio=False)

# --- LED-MATRIX (Heizung) SETUP ---
serial = spi(port=0, device=0, gpio=noop())
matrix_device = max7219(serial, cascaded=1)
matrix_device.clear()
heizung_an = False
print("LED-Matrix (Heizung): BEREIT")

try:
    lcd = CharLCD('PCF8574', 0x27)
    lcd.clear()
    print("LCD Zentrale: BEREIT")
except:
    lcd = None
    print("LCD Fehler: Verkabelung prüfen.")


# ==========================================
# HEIZUNG (LED-MATRIX) HILFSFUNKTIONEN
# ==========================================
def heizung_ein():
    global heizung_an
    with canvas(matrix_device) as draw:
        draw.line((1, 0, 1, 7), fill="white")
        draw.line((0, 0, 0, 7), fill="white")
        draw.line((6, 0, 6, 7), fill="white")
        draw.line((7, 0, 7, 7), fill="white")
        draw.line((1, 3, 6, 3), fill="white")
        draw.line((1, 4, 6, 4), fill="white")
    heizung_an = True


def heizung_aus():
    global heizung_an
    matrix_device.clear()
    heizung_an = False


# ==========================================
# CSV VORBEREITEN
# ==========================================
datei_existiert = os.path.isfile(CSV_DATEI)

csv_file = open(CSV_DATEI, mode='a', newline='', buffering=1)
csv_writer = csv.writer(csv_file)

if not datei_existiert:
    csv_writer.writerow(CSV_SPALTEN)
    print(f"Neue Log-Datei erstellt: {CSV_DATEI}")
else:
    print(f"Hänge an bestehende Log-Datei an: {CSV_DATEI}")

print("========================================")
print(" INTELLIGENTES GEWÄCHSHAUS AKTIV")
print(" (Modus: Multi-Tasking + CSV + Firebase)")
print("========================================")

letzter_klima_status = ""


# ==========================================
# FIREBASE UPLOAD FUNKTION
# ==========================================
def send_to_firebase(temp, hum, boden_trocken, heizung_an, luefter_an, nebel_an, mode="auto"):
    payload = {
        "data": {
            "deviceId": DEVICE_ID,
            "temperature": round(temp, 1),
            "humidity": round(hum, 1),
            "soilDry": boden_trocken,
            "heaterOn": bool(heizung_an),
            "fanOn": bool(luefter_an),
            "mist1On": bool(nebel_an),
            "mist2On": False,
            "mode": mode
        }
    }

    try:
        response = requests.post(
            FIREBASE_FUNCTION_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            return True
        else:
            print(f"  [Firebase] Fehler: Status {response.status_code} - {response.text[:100]}")
            return False

    except requests.exceptions.ConnectionError:
        print("  [Firebase] Keine Internetverbindung - überspringe Upload.")
        return False
    except requests.exceptions.Timeout:
        print("  [Firebase] Timeout - überspringe Upload.")
        return False
    except Exception as e:
        print(f"  [Firebase] Unerwarteter Fehler: {e}")
        return False


# ==========================================
# HAUPTSCHLEIFE
# ==========================================
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

            bewaesserung_aktiv = False
            luefter_aktiv = False
            nebel_aktiv = False

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
                    heizung_aus()
                    letzter_klima_status = "KUEHLEN"

                GPIO.output(PIN_LUEFTER, GPIO.HIGH)
                luefter_aktiv = True
                time.sleep(3)
                GPIO.output(PIN_LUEFTER, GPIO.LOW)
                time.sleep(1)
                GPIO.output(PIN_NEBEL_1, GPIO.HIGH)
                nebel_aktiv = True
                time.sleep(5)
                GPIO.output(PIN_NEBEL_1, GPIO.LOW)

            elif temp < TEMP_MIN:
                if letzter_klima_status != "HEIZEN":
                    print(f"[{temp}°C] ZU KALT! LED-Matrix Heizung EIN.")
                    GPIO.output(PIN_LUEFTER, GPIO.LOW)
                    heizung_ein()
                    letzter_klima_status = "HEIZEN"

            else:
                if letzter_klima_status != "OK":
                    print(f"[{temp}°C] Temperatur ideal.")
                    GPIO.output(PIN_LUEFTER, GPIO.LOW)
                    heizung_aus()
                    letzter_klima_status = "OK"

            # 4. GEHIRNHÄLFTE 2: BEWÄSSERUNGS-LOGIK
            if boden_trocken:
                print("BEWÄSSERUNG: Bodenfeuchte kritisch! Vernebler startet...")
                GPIO.output(PIN_NEBEL_1, GPIO.HIGH)
                nebel_aktiv = True
                time.sleep(5)
                GPIO.output(PIN_NEBEL_1, GPIO.LOW)
                print("Bewässerung beendet.")
                bewaesserung_aktiv = True
                time.sleep(2)
            else:
                if letzter_klima_status != "KUEHLEN":
                    GPIO.output(PIN_NEBEL_1, GPIO.LOW)

            # 5. CSV ZEILE SCHREIBEN
            zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            csv_writer.writerow([
                zeitstempel,
                round(temp, 1),
                round(hum, 1),
                boden_trocken,
                letzter_klima_status,
                bewaesserung_aktiv,
                luefter_aktiv,
                heizung_an,
                nebel_aktiv
            ])

            # 6. KONSOLEN-AUSGABE
            print(f"[{zeitstempel}] "
                  f"Temp: {temp:.1f}°C | "
                  f"Feuchte: {hum:.1f}% | "
                  f"Boden: {'TROCKEN' if boden_trocken else 'FEUCHT'} | "
                  f"Status: {letzter_klima_status} | "
                  f"Heizung: {'AN' if heizung_an else 'AUS'} | "
                  f"Lüfter: {'AN' if luefter_aktiv else 'AUS'} | "
                  f"Nebel: {'AN' if nebel_aktiv else 'AUS'}")

            # 7. FIREBASE UPLOAD
            firebase_ok = send_to_firebase(
                temp=temp,
                hum=hum,
                boden_trocken=boden_trocken,
                heizung_an=heizung_an,
                luefter_an=luefter_aktiv,
                nebel_an=nebel_aktiv,
                mode="auto"
            )

            if firebase_ok:
                print("  [Firebase] ✓ Upload erfolgreich")

            time.sleep(2)

        except RuntimeError:
            time.sleep(2)
            continue

except KeyboardInterrupt:
    print("\nSystem beendet.")

finally:
    csv_file.close()
    matrix_device.clear()
    GPIO.cleanup()
    if lcd:
        lcd.clear()
    print("Hardware gesichert. CSV-Datei geschlossen.")
