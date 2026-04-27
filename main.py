import time

import board

import adafruit_dht

import RPi.GPIO as GPIO

from RPLCD.i2c import CharLCD

from luma.led_matrix.device import max7219

from luma.core.interface.serial import spi

from luma.core.render import canvas

# --- CONFIG ---

DHT_PIN_BOARD = board.D4

PIN_BODEN = 17

NEBEL_1 = 27

NEBEL_2 = 23

PIN_HEIZUNG = 16

PIN_LUEFTER = 18

TEMP_MIN = 18.0

TEMP_MAX = 28.0

HUM_TARGET = 35.0

# --- SETUP ---

GPIO.setwarnings(False)

GPIO.setmode(GPIO.BCM)

GPIO.setup([PIN_BODEN], GPIO.IN)

GPIO.setup([NEBEL_1, NEBEL_2, PIN_HEIZUNG, PIN_LUEFTER], GPIO.OUT)

dht_device = adafruit_dht.DHT22(DHT_PIN_BOARD, use_pulseio=False)

lcd = CharLCD('PCF8574', 0x27)

serial_matrix = spi(port=0, device=0, gpio_SCLK=11, gpio_MOSI=10, gpio_CS=8)

matrix = max7219(serial_matrix, cascaded=1, block_orientation=0, rotate=1)


# --- NEUE MATRIX FUNKTIONEN ---


def zeige_heizung_voll():
    # Alle LEDs an fuer die Heizung

    with canvas(matrix) as draw:
        for i in range(8):
            draw.line((0, i, 7, i), fill="white")


def zeige_luefter_drehend(wiederholungen=3):
    # Animiertes X und Plus wechselnd fuer Rotation

    for _ in range(wiederholungen):
        with canvas(matrix) as draw:
            draw.line((0, 0, 7, 7), fill="white")

            draw.line((0, 7, 7, 0), fill="white")

        time.sleep(0.1)

        with canvas(matrix) as draw:
            draw.line((3, 0, 3, 7), fill="white")

            draw.line((0, 3, 7, 3), fill="white")

        time.sleep(0.1)


def draw_ok():
    with canvas(matrix) as draw:
        draw.rectangle((2, 2, 5, 5), outline="white")


def lcd_scroll_text(line1, scroll_text):
    padding = " " * 16

    full_text = padding + scroll_text + padding

    for i in range(len(full_text) - 16 + 1):
        lcd.clear()

        lcd.write_string(line1 + "\r\n")

        lcd.write_string(full_text[i:i + 16])

        time.sleep(0.15)  # Etwas flotter eingestellt


print("System starting with Animations...")

try:

    while True:

        try:

            temp = dht_device.temperature

            hum = dht_device.humidity

            ground_dry = (GPIO.input(PIN_BODEN) == GPIO.HIGH)

            if temp is None or hum is None:
                time.sleep(2)

                continue

                # Logik Temperatur & Matrix Animationen

            if temp < TEMP_MIN:

                GPIO.output(PIN_HEIZUNG, GPIO.HIGH);
                GPIO.output(PIN_LUEFTER, GPIO.LOW)

                zeige_heizung_voll()  # Vollbild-LED

                h_stat = "HEIZ"

            elif temp > TEMP_MAX:

                GPIO.output(PIN_HEIZUNG, GPIO.LOW);
                GPIO.output(PIN_LUEFTER, GPIO.HIGH)

                zeige_luefter_drehend()  # Rotation

                h_stat = "KUEHL"

            else:

                GPIO.output(PIN_HEIZUNG, GPIO.LOW);
                GPIO.output(PIN_LUEFTER, GPIO.LOW)

                draw_ok()

                h_stat = " OK "

                # Logik Vernebler (Boden hat Prio vor Luft)

            if ground_dry:

                GPIO.output(NEBEL_1, GPIO.HIGH);
                GPIO.output(NEBEL_2, GPIO.HIGH)

                n_stat = "BODEN"

            elif hum < HUM_TARGET:

                GPIO.output(NEBEL_1, GPIO.HIGH);
                GPIO.output(NEBEL_2, GPIO.LOW)

                n_stat = "LUFT "

            else:

                GPIO.output(NEBEL_1, GPIO.LOW);
                GPIO.output(NEBEL_2, GPIO.LOW)

                n_stat = " AUS "

                # Anzeige zusammenbauen

            line1_text = f"T:{h_stat}  H:{n_stat}"

            scrolling_info = f"Temperatur: {temp:.1f}C  Feuchte: {hum:.1f}%  Boden: {'TROCKEN' if ground_dry else 'FEUCHT'}"

            lcd_scroll_text(line1_text, scrolling_info)



        except RuntimeError:

            time.sleep(2)

            continue



except KeyboardInterrupt:

    print("Stop")

finally:

    GPIO.cleanup()

    matrix.clear()

    lcd.clear()
    lcd.clear()

    test 2
