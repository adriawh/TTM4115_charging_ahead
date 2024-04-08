import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

red = 4
yellow = 22
green = 9
in_pin = 26

GPIO.setup(red, GPIO.OUT)
GPIO.setup(yellow, GPIO.OUT)
GPIO.setup(green, GPIO.OUT)
GPIO.setup(in_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def red_light():
    GPIO.output(red, GPIO.HIGH)
    GPIO.output(yellow, GPIO.LOW)
    GPIO.output(green, GPIO.LOW)

def yellow_light():
    GPIO.output(red, GPIO.LOW)
    GPIO.output(yellow, GPIO.HIGH)
    GPIO.output(green, GPIO.LOW)

def green_light():
    GPIO.output(red, GPIO.LOW)
    GPIO.output(yellow, GPIO.LOW)
    GPIO.output(green, GPIO.HIGH)

def off_light():
    GPIO.output(red, GPIO.LOW)
    GPIO.output(yellow, GPIO.LOW)
    GPIO.output(green, GPIO.LOW)

def main():
    while True:
        input_state = GPIO.input(in_pin)
        if input_state == False:
            yellow_light()
            time.sleep(1)
        else:
            green_light()
            time.sleep(1)
        

if __name__ == "__main__":
    main()
