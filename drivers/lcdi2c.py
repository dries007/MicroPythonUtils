# LCD via i2c driver for MicroPython (on ESP8266)
# Copyright (c) 2016 Dries007
# License: MIT
#
# Only tested with PCF8574T and a 16*2 LCD

import time

_BIT0 = const(1 << 0)
_BIT1 = const(1 << 1)
_BIT2 = const(1 << 2)
_BIT3 = const(1 << 3)
_BIT4 = const(1 << 4)
_BIT5 = const(1 << 5)
_BIT6 = const(1 << 6)
_BIT7 = const(1 << 7)


class LCD:
    def __init__(self, i2c, address=0x3F, check=True, bit_rs=0, bit_rw=1, bit_enable=2, bit_led=3, bit_data=4):
        self.i2c = i2c
        self.address = address
        self.bit_rs = 1 << bit_rs
        self.bit_rw = 1 << bit_rw
        self.bit_enable = 1 << bit_enable
        self.bit_led = 1 << bit_led
        self.current_led = 1 << bit_led
        self.shift_data = bit_data
        if check and address not in i2c.scan():
            raise Exception('LCD init failed: No device on address %x' % address)

    def led(self, value=None):
        old = self.current_led == self.bit_led
        if value is not None:
            self.current_led = self.bit_led if value else 0
            self.i2c.writeto(self.address, bytes((self.current_led,)))
        return old

    def clear(self):
        self.write_byte(0b1, rs=0)
        time.sleep(.01)

    def home(self):
        self.write_byte(0b10, rs=0)
        time.sleep(.01)

    def pos(self, col, row=0):
        self.write_byte(_BIT7 | (col & 0b111111) | ((row & 1) << 6), rs=0)

    def custom_char(self, char, data):
        self.write_byte(_BIT6 | ((7 & char) << 3), rs=0)
        self.write(data, rs=1)

    def display_control(self, enabled=True, cursor=True, blink=True):
        byte = 0b00001000
        if enabled: byte |= _BIT2
        if cursor: byte |= _BIT1
        if blink: byte |= _BIT0
        self.write_byte(byte, rs=0)

    def write_nibble(self, data, rs):
        self.i2c.writeto(self.address, bytes((
            self.current_led | rs | (data << self.shift_data),
            self.current_led | rs | self.bit_enable | (data << self.shift_data),
            self.current_led | rs | (data << self.shift_data)
        )))
        time.sleep(.0001)

    def write_byte(self, data, rs):
        self.write(bytes((data, )), rs=rs)

    def write(self, data, rs):
        for byte in data:
            self.write_nibble((byte >> 4) & 0x0F, rs=rs)
            self.write_nibble(byte & 0x0F, rs=rs)

    def print(self, text):
        self.clear()
        lines = text.split(b'\n', 2)
        self.write(lines[0], self.bit_rs)
        if len(lines) == 2:
            self.pos(0, 1)
            self.write(lines[1], self.bit_rs)

    def init(self):
        time.sleep(.005)
        self.write_byte(0b00110011, rs=0) # Force display in 8 bit mode
        time.sleep(.005)
        self.write_nibble(0b0010, rs=0) # Set 4 bit mode
        time.sleep(.005)
        self.write_byte(0b00101000, rs=0) # Function set: 4 Bit, 2 Lines, Font 5*8
        time.sleep(.005)
        self.display_control(True, True, True) # Display control: Display on, cursor on, blink on
        time.sleep(.005)
        self.clear()

