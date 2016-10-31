import esp
import machine
esp.osdebug(None)
machine.freq(160000000)


import gc
import uos
import time

print("Mem Pre Import:", gc.mem_free())
import at24cxx

print("Mem Pre Collect:", gc.mem_free())
gc.collect()
print("Mem Post Collect:", gc.mem_free())

i2c = machine.I2C(machine.Pin(12), machine.Pin(13), freq=100000)
eeprom = at24cxx.AT24CXX(i2c)

rnd = bytearray(uos.urandom(10))

eeprom.write(0, rnd)
time.sleep(.1)
print(eeprom.read(0, 10) == rnd)

eeprom.write_address(1)
time.sleep(.1)
print(eeprom.read_sequential(4) == rnd[1:5])

rnd_ = uos.urandom(1)[0]
eeprom.write_byte(0, rnd_)
time.sleep(.1)

rnd[0] = rnd_
print(eeprom.read(0, 10) == rnd)
time.sleep(.1)
