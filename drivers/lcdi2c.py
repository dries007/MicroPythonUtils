# LCD via i2c driver for MicroPython (on ESP8266)
# Copyright (c) 2016 Dries007
# License: MIT
#
# Only tested with PCF8574T and a 16*2 LCD
#
# ToDo: Make pinout part of object initializer

import time

_BIT0 = const(1 << 0)
_BIT1 = const(1 << 1)
_BIT2 = const(1 << 2)
_BIT3 = const(1 << 3)
_BIT4 = const(1 << 4)
_BIT5 = const(1 << 5)
_BIT6 = const(1 << 6)
_BIT7 = const(1 << 7)

_DATA = 4

_RS_DATA = _BIT0
_RS_COMMAND = 0

_RW_READ = _BIT1
_RW_WRITE = 0

_ENABLE_ON = _BIT2
_ENABLE_OFF = 0

_LED_ON = _BIT3
_LED_OFF = 0


class LCD:
    def __init__(self, i2c, address=0x3F, check=True):
        self.i2c = i2c
        self.address = address
        self._led = _LED_ON
        if check and address not in i2c.scan():
            raise Exception('LCD init failed: No device on address %x' % address)

    def led(self, value=None):
        old = self._led == _LED_ON
        if value is not None:
            self._led = _LED_ON if value else _LED_OFF
            self.i2c.writeto(self.address, bytes((self._led | _ENABLE_OFF, )))
        return old

    def clear(self):
        self.write_byte(0b1, rs=_RS_COMMAND)
        time.sleep(.01)

    def home(self):
        self.write_byte(0b10, rs=_RS_COMMAND)
        time.sleep(.01)

    def pos(self, col, row=0):
        self.write_byte(_BIT7 | (col & 0b111111) | ((row & 1) << 6), rs=_RS_COMMAND)

    def custom_char(self, char, data):
        self.write_byte(_BIT6 | ((7 & char) << 3), rs=_RS_COMMAND)
        self.write(data)

    def display_control(self, enabled=True, cursor=True, blink=True):
        byte = 0b00001000
        if enabled: byte |= _BIT2
        if cursor: byte |= _BIT1
        if blink: byte |= _BIT0
        self.write_byte(byte, rs=_RS_COMMAND)

    def write_nibble(self, data, rs=_RS_DATA):
        self.i2c.writeto(self.address, bytes((
            self._led | rs | _RW_WRITE | _ENABLE_OFF | (data << _DATA),
            self._led | rs | _RW_WRITE | _ENABLE_ON | (data << _DATA),
            self._led | rs | _RW_WRITE | _ENABLE_OFF | (data << _DATA)
        )))
        time.sleep(.0001)

    def write_byte(self, data, rs=_RS_DATA):
        self.write(bytes((data, )), rs=rs)

    def write(self, data, rs=_RS_DATA):
        for byte in data:
            self.write_nibble((byte >> 4) & 0x0F, rs=rs)
            self.write_nibble(byte & 0x0F, rs=rs)

    def text(self, text, pos=None, clear=True):
        if clear:
            self.clear()
        if pos is not None:
            if isinstance(pos, int): self.pos(pos)
            else: self.pos(*pos)
        self.write(text.encode('ascii'))

    def init(self):
        time.sleep(.005)
        self.write_byte(0b00110011, rs=_RS_COMMAND) # Force display in 8 bit mode
        time.sleep(.005)
        self.write_nibble(0b0010, rs=_RS_COMMAND) # Set 4 bit mode
        time.sleep(.005)
        self.write_byte(0b00101000, rs=_RS_COMMAND) # Function set: 4 Bit, 2 Lines, Font 5*8
        time.sleep(.005)
        self.display_control(True, True, True) # Display control: Display on, cursor on, blink on
        time.sleep(.005)
        self.clear()

