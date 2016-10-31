import time

i2c = machine.I2C(machine.Pin(12), machine.Pin(13), freq=100000)
lcd = LCD(i2c)
lcd.init()
lcd.clear()


for i in range(0, 0xFF, 32):
    lcd.clear()
    lcd.write(range(i, i + 16))
    lcd.pos(0, 1)
    lcd.write(range(i + 16, i + 32))
    time.sleep(5)

# @formatter:off

lcd.text('\x00\x01')

while True:
    lcd.custom_char(0, [
        0b01100,
        0b01100,
        0b10000,
        0b10000,
        0b11111,
        0b10100,
        0b10100,
        0b10100,
    ])
    lcd.custom_char(1, [
        0b00000,
        0b00000,
        0b00011,
        0b00011,
        0b11100,
        0b01100,
        0b01010,
        0b01001,
    ])
    time.sleep(.1)
    lcd.custom_char(0, [
        0b00110,
        0b00110,
        0b01000,
        0b01000,
        0b01111,
        0b01100,
        0b10100,
        0b10100,
    ])
    lcd.custom_char(1, [
        0b00000,
        0b00000,
        0b00011,
        0b00011,
        0b11110,
        0b00110,
        0b01010,
        0b01001,
    ])
    time.sleep(.1)
    lcd.custom_char(0, [
        0b00011,
        0b00011,
        0b00100,
        0b00100,
        0b00111,
        0b01100,
        0b01100,
        0b01100,
    ])
    lcd.custom_char(1, [
        0b00000,
        0b00000,
        0b00011,
        0b00011,
        0b11111,
        0b00011,
        0b00110,
        0b01001,
    ])
    time.sleep(.1)

# @formatter:on
