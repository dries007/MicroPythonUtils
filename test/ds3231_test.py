import esp
import machine
esp.osdebug(None)
machine.freq(160000000)

import gc

print("Mem Pre Import:", gc.mem_free())
import ds3231

print("Mem Pre Collect:", gc.mem_free())
gc.collect()
print("Mem Post Collect:", gc.mem_free())

i2c = machine.I2C(machine.Pin(12), machine.Pin(13), freq=100000)
rtc = ds3231.DS3231(i2c)


def test():
    dt = rtc.get_datetime()
    print("Now: %04d-%02d-%02d %02d:%02d:%02d" % dt[0:6], ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[dt[6]])
    day_date, hour, minute, second, mask = rtc.get_alarm_time_1(); print("Alarm 1: %d (%s) %02d:%02d:%02d" % (day_date, ('DT', 'DY')[mask >> 4], hour, minute, second), "Mask: {:04b}".format(mask & 0b1111), rtc.get_alarm1())
    eosc, bbsqw, rs, intcn, a1ie, en32khz = rtc.get_config()
    for l in [("SYMBOL", 'NAME', 'DEFAULT', 'CURRENT VALUE'),
        ("EOSC", "Enable battery backup", True, eosc),
        ("BBSQW", "Enable battery backed square wave", False, bbsqw),
        ("RS", "Square wave rate select", "8.192kHz", ("1Hz", "1.024kHz", "4.096kHz", "8.192kHz")[rs]),
        ("INTCN", "Interrupt control (SQW=False INT=True)", True, intcn),
        ("A1IE", "Alarm 1 interrupt enable", True, a1ie),
        ("EN32kHz", "Enable 32kHz Output", True, en32khz)]:
        print("{:8} {:45} {!s:10} {}".format(*l))
    print("Temperature:         ", rtc.temp())
    print("Aging offset:        ", rtc.age_offset())
    print("Mem Pre Collect:", gc.mem_free())
    gc.collect()
    print("Mem Post Collect:", gc.mem_free())
