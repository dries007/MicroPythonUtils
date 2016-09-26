# AT24CXX driver for MicroPython (on ESP8266)
# Copyright (c) 2016 Dries007
# License: MIT
#
# Only tested with AT24C32


class AT24CXX:

    def __init__(self, i2c, address=0x57, check=True):
        self.i2c = i2c
        self.address = address
        if check and address not in i2c.scan():
            raise Exception('AT24CXX init failed: No device on address %x' % address)

    def write_byte(self, address, data):
        self.i2c.start()
        self.i2c.write(bytes((self.address << 1, (address >> 8) & 0xFF, address & 0xFF, data)))
        self.i2c.stop()

    def write(self, address, data):
        if len(data) > 32: raise Exception("Can't write more then 32 bytes at one time.")
        self.i2c.start()
        self.i2c.write(bytes((self.address << 1, (address >> 8) & 0xFF, address & 0xFF)))
        self.i2c.write(data)
        self.i2c.stop()

    def read(self, address, size):
        self.write_address(address)
        return self.read_sequential(size)

    def write_address(self, address):
        self.i2c.writeto(self.address, bytes(((address >> 8) & 0xFF, address & 0xFF)))

    def read_sequential(self, size):
        return self.i2c.readfrom(self.address, size)
