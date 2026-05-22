#!/usr/bin/env python3
"""
reset_gpio.py - Schaltet ALLES aus.
"""

import RPi.GPIO as GPIO
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from RPLCD.i2c import CharLCD

# Alle verwendeten GPIOs
ALLE_PINS = [18, 27, 25]

# GPIOs zurücksetzen
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(ALLE_PINS, GPIO.OUT, initial=GPIO.LOW)
GPIO.cleanup()
print("GPIOs: AUS")

# LED-Matrix ausschalten
try:
    serial = spi(port=0, device=0, gpio=noop())
    matrix_device = max7219(serial, cascaded=1)
    matrix_device.clear()
    print("LED-Matrix: AUS")
except:
    print("LED-Matrix: nicht erreichbar")

# LCD ausschalten
try:
    lcd = CharLCD('PCF8574', 0x27)
    lcd.clear()
    lcd.backlight_enabled = False
    print("LCD: AUS")
except:
    print("LCD: nicht erreichbar")

print("Alles zurückgesetzt.")
