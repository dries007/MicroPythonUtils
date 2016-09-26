# DS3231 driver for MicroPython (on ESP8266)
# Copyright (c) 2016 Dries007
# License: MIT
#
# Removed functionality:
#   Alarm 2 (Module became too big to be imported)
#
# ToDo: add back alarm 2 & test in frozen bytecode (aka preloaded modules)
#

import time


_BIT0 = const(1 << 0)
_BIT1 = const(1 << 1)
_BIT2 = const(1 << 2)
_BIT3 = const(1 << 3)
_BIT4 = const(1 << 4)
_BIT5 = const(1 << 5)
_BIT6 = const(1 << 6)
_BIT7 = const(1 << 7)

_CALENDAR = const(0x00)
_ALARM1 = const(0x07)
_ALARM2 = const(0x0B)
_CONTROL = const(0x0E)
_STATUS = const(0x0F)
_AGING = const(0x10)
_TEMP = const(0x11)


def _bcd2bin(value):
    return value - 6 * (value >> 4)


def _bin2bcd(value):
    return value + 6 * (value // 10)


def _twocplm2int(val, bits=8):
    if (val & (1 << (bits - 1))) != 0: val -= 1 << bits
    return val


def _int2twocplm(val):
    mask = (1 << 7)
    if val >= 0: return val
    return mask | (mask + val)


def datetime2seconds(datetime):
    return time.mktime(datetime + (0,))


def seconds2datetime(sec):
    return time.localtime(sec)[0:7]


class DS3231:
    """
    Weekday = 0 (monday) -> 6 (sunday)
    Datetime tuple = (year, month, day, hour, minute, second, weekday)
    """

    def __init__(self, i2c, address=0x68, check=True):
        self.i2c = i2c
        self.address = address
        if check and address not in i2c.scan():
            raise Exception('DS3231 init failed: No device on address %x' % address)
        if self._bit(_STATUS, _BIT7):
            print("Oscillator Stop Flag is set. The RTC time may be in-accurate.")
        if self._bit(_CONTROL, _BIT7, False):
            print("Oscillator was not running. Stop flag has now been cleared.")

    def _read(self, register, length=1):
        buf = self.i2c.readfrom_mem(self.address, register, length)
        return buf[0] if length == 1 else buf

    def _write(self, register, data):
        self.i2c.writeto_mem(self.address, register, data)

    def _bit(self, register, mask, value=None):
        register_data = self._read(register)
        old = bool(mask & register_data)
        if value is None:
            return old
        if value:
            register_data |= mask
        else:
            register_data &= ~mask
        self._write(register, bytes((register_data,)))
        return old

    def get_datetime(self):
        buffer = self._read(_CALENDAR, 7)
        return (_bcd2bin(buffer[6]) + 2000,  # year
                _bcd2bin(buffer[5]),  # month
                _bcd2bin(buffer[4]),  # day
                _bcd2bin(buffer[2]),  # hour
                _bcd2bin(buffer[1]),  # minute
                _bcd2bin(buffer[0]),  # second
                _bcd2bin(buffer[3]) - 1)  # weekday

    def set_datetime(self, year=None, month=None, day=None, hour=None, minute=None, second=None, weekday=None):
        buffer = bytearray(self._read(_CALENDAR, 7))
        if year is not None: buffer[6] = _bin2bcd(year - 2000)
        if month is not None: buffer[5] = _bin2bcd(month)
        if day is not None: buffer[4] = _bin2bcd(day)
        if hour is not None: buffer[2] = _bin2bcd(hour)
        if minute is not None: buffer[1] = _bin2bcd(minute)
        if second is not None: buffer[0] = _bin2bcd(second)
        if weekday is not None: buffer[3] = _bin2bcd(weekday) + 1
        self._write(_CALENDAR, buffer)

    def sync(self):
        """ Set the internal RTC to this time """
        import machine

        dt = self.get_datetime()
        dt = dt[0:3] + (0,) + dt[3:6] + (0,)  # adds weekday & milliseconds
        machine.RTC().datetime(dt)

    def ntp(self):
        """ Sync via NTP """
        import ntptime

        sec = ntptime.time()
        self.set_datetime(*seconds2datetime(sec))
        self.sync()

    def temp(self, force=False):
        """ Get temperature. This function waits until the RTC is ready. By default the chip does 1 read evey 64 seconds. (You can force an update.) """
        if force:
            self._bit(_CONTROL, _BIT5, True)
            while self._bit(_CONTROL, _BIT5):
                time.sleep_ms(1)
        while self._bit(_STATUS, _BIT2):
            time.sleep_ms(1)
        buffer = self._read(_TEMP, 2)
        return _twocplm2int((buffer[0] << 2) + (buffer[1] >> 6), 10) * 0.25

    def get_alarm1(self, reset=True):
        """Get the alarm 1 flag, and reset it by default"""
        return self._bit(_STATUS, _BIT0, False if reset else None)

    def get_alarm_time_1(self):
        """Return: day_date, hour, minute, second, mask"""
        buffer = self._read(_ALARM1, 4)
        mask = (  # = A1M1 | A1M2 << 1 | A1M3 << 2 | A1M4 << 3 | DY/DT << 4
            (buffer[0] & _BIT7) >> 7 |  # A1M1
            (buffer[1] & _BIT7) >> 6 |  # A1M2
            (buffer[2] & _BIT7) >> 5 |  # A1M3
            (buffer[3] & _BIT7) >> 4 |  # A1M4
            (buffer[3] & _BIT6) >> 2)  # DY/DT
        second = _bcd2bin(buffer[0] & ~_BIT7)
        minute = _bcd2bin(buffer[1] & ~_BIT7)
        hour = _bcd2bin(buffer[2] & ~_BIT7)
        day_date = _bcd2bin(buffer[3] & ~_BIT7 & ~_BIT6)
        return day_date, hour, minute, second, mask

    def set_alarm_time_1(self, mask=None, second=None, minute=None, hour=None, day_date=None):
        """
        mask is 5 bit field made like this: AxM1 | AxM2 << 1 | AxM3 << 2 | AxM4 << 3 | DY/DT << 4
        AxM1 is ony available on alarm 1.
        The mask bits (M1 -> M4) determine what needs to match for an alarm to occur.
        M4  M3  M2  M1
        1   1   1   1   Alarm once per second
        1   1   1   0   Alarm once per minute (and when seconds match, in case of Alarm 1)
        1   1   0   0   Alarm when minutes (and seconds, A1) match
        1   0   0   0   Alarm when hours, minutes (and seconds, A1) match
        0   0   0   0   Alarm when day/date (see DY/DT), hours, minutes (and seconds, A1) match
        DY/DT set to 0 means the day/date field must match the date (day of month)
                     1 means the day/date field must match the day (day of week)
        """
        if mask is not None:
            self._bit(_ALARM1 + 0, _BIT7, mask & _BIT0)  # A1M1
            self._bit(_ALARM1 + 1, _BIT7, mask & _BIT1)  # A1M2
            self._bit(_ALARM1 + 2, _BIT7, mask & _BIT2)  # A1M3
            self._bit(_ALARM1 + 3, _BIT7, mask & _BIT3)  # A1M4
            self._bit(_ALARM1 + 3, _BIT6, mask & _BIT4)  # DY/DT
        if second is not None: self._write(_ALARM1 + 0, bytes(((self._read(_ALARM1 + 0) & _BIT7) + _bin2bcd(second),)))  # A1M1 << 7 | second in BCD
        if minute is not None: self._write(_ALARM1 + 1, bytes(((self._read(_ALARM1 + 1) & _BIT7) + _bin2bcd(minute),)))  # A1M2 << 7 | minute in BCD
        if hour is not None: self._write(_ALARM1 + 2, bytes(((self._read(_ALARM1 + 2) & _BIT7) + _bin2bcd(hour),)))  # A1M3 << 7 | hour in BCD
        if day_date is not None: self._write(_ALARM1 + 3, bytes(((self._read(_ALARM1 + 3) & 0b11000000) + _bin2bcd(day_date),)))  # A1M3 << 7 | DY/DT << 6 | day/date in BCD

    #
    # def get_alarm2(self, reset=True):
    #     """Get the alarm 1 flag, and reset it by default"""
    #     return self._bit(_STATUS, _BIT1, True if reset else None)
    #
    # def get_alarm_time_2(self):
    #     """Return: day_date, hour, minute, mask"""
    #     buffer = self._read(_ALARM2, 3)
    #     mask = (  # = A2M2 << 1 | A2M3 << 2 | A2M4 << 3 | DY/DT << 4; A2M1 does not exist.
    #         (buffer[0] & _BIT7) >> 6 |  # A2M2
    #         (buffer[1] & _BIT7) >> 5 |  # A2M3
    #         (buffer[2] & _BIT7) >> 4 |  # A2M4
    #         (buffer[2] & _BIT6) >> 5  # DY/DT
    #     )
    #     minute = _bcd2bin(buffer[0] & ~_BIT7)
    #     hour = _bcd2bin(buffer[1] & ~_BIT7)
    #     day_date = _bcd2bin(buffer[2] & ~_BIT7 & ~_BIT6)
    #     return day_date, hour, minute, mask
    #
    # def set_alarm_time_2(self, mask=None, minute=None, hour=None, day_date=None):
    #     """See set_alarm_time_1"""
    #     if mask is not None:
    #         self._bit(_ALARM2 + 0, _BIT7, mask & _BIT1)  # A1M2
    #         self._bit(_ALARM2 + 1, _BIT7, mask & _BIT2)  # A1M3
    #         self._bit(_ALARM2 + 2, _BIT7, mask & _BIT3)  # A1M4
    #         self._bit(_ALARM2 + 2, _BIT6, mask & _BIT4)  # DY/DT
    #     if minute is not None: self._write(_ALARM2 + 0, bytes(((self._read(_ALARM2 + 0) & _BIT7) + _bin2bcd(minute),)))  # A2M2 << 7 | minute in BCD
    #     if hour is not None: self._write(_ALARM2 + 1, bytes(((self._read(_ALARM2 + 1) & _BIT7) + _bin2bcd(hour),)))  # A2M2 << 7 | hour in BCD
    #     if day_date is not None: self._write(_ALARM2 + 2, bytes(((self._read(_ALARM2 + 2) & _BIT7) + _bin2bcd(day_date),)))  # A2M2 << 7 | DY/DT << 6 |
    # day/date in BCD

    def get_config(self):
        buffer = self._read(_CONTROL, 2)
        return (bool(buffer[0] & _BIT7),  # EOSC
                bool(buffer[0] & _BIT6),  # BBSQW
                (buffer[0] & (_BIT4 | _BIT3)) >> 3,  # RS
                bool(buffer[0] & _BIT2),  # INTCN
                # bool(buffer[0] & _BIT1),  # A2IE
                bool(buffer[0] & _BIT0),  # A1IE
                bool(buffer[1] & _BIT3))  # EN32kHz)

    def set_config(self, eosc=None, bbsqw=None, rs=None, intcn=None, a1ie=None, en32khz=None):  # a2ie=None,
        if eosc is not None: self._bit(_CONTROL, _BIT7, eosc)
        if bbsqw is not None: self._bit(_CONTROL, _BIT6, bbsqw)
        if rs is not None:
            self._bit(_CONTROL, _BIT4, rs >> 1)
            self._bit(_CONTROL, _BIT3, rs & 1)
        if intcn is not None: self._bit(_CONTROL, _BIT2, intcn)
        # if a2ie is not None: self._bit(_CONTROL, _BIT1, a2ie)
        if a1ie is not None: self._bit(_CONTROL, _BIT0, a1ie)
        if en32khz is not None: self._bit(_STATUS, _BIT3, en32khz)

    def age_offset(self, value=None):
        """ Something magical I don't quite understand. See DS3231 datasheet. """
        if value is None:
            return _twocplm2int(self._read(_AGING))
        self._write(_AGING, bytes((_int2twocplm(value),)))
