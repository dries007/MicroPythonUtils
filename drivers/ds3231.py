# DS3231 driver for MicroPython (on ESP8266)
# Copyright (c) 2016 Dries007
# License: MIT

import time
import machine

_BIT0 = 1 << 0
_BIT1 = 1 << 1
_BIT2 = 1 << 2
_BIT3 = 1 << 3
_BIT4 = 1 << 4
_BIT5 = 1 << 5
_BIT6 = 1 << 6
_BIT7 = 1 << 7


def _bcd2bin(value):
    return value - 6 * (value >> 4)


def _bin2bcd(value):
    return value + 6 * (value // 10)


def _twocplm2int(val, bits=8):
    if (val & (1 << (bits - 1))) != 0:
        val -= 1 << bits
    return val


def _int2twocplm(val, bits=8):
    mask = (1 << (bits - 1))
    if val >= mask or val < -mask:
        raise Exception("%d won't fit in an %d bit 2's complement." % (val, bits))
    if val > 0: return val
    return mask | (mask + val)


def datetime2seconds(datetime):
    return time.mktime(datetime + (0, ))


def seconds2datetime(sec):
    return time.localtime(sec)[0:7]


class DS3231:
    """
    Weekday = 0 (monday) -> 6 (sunday)
    Datetime tuple = (year, month, day, hour, minute, second, weekday)
    """
    _CALENDAR = 0x00
    _ALARM1 = 0x07
    _ALARM2 = 0x0B
    _CONTROL = 0x0E
    _STATUS = 0x0F
    _AGING = 0x10
    _TEMP = 0x11

    def __init__(self, i2c, address=0x68, check=True):
        self.i2c = i2c
        self.address = address
        if check and address not in i2c.scan():
            raise Exception('DS3231 init failed: No device on address %x' % address)
        if self._bit(self._CONTROL, _BIT7, False):
            print("Oscillator was not running. Stop flag has now been cleared.")

    def ntp(self):
        """ Sync via NTP """
        import ntptime
        sec = ntptime.time()
        self.seconds(sec)
        self.sync()

    def sync(self):
        """ Set the internal RTC to this time """
        dt = self.datetime()
        dt = dt[0:3] + (0, ) + dt[3:6] + (0, ) # adds weekday & milliseconds
        machine.RTC().datetime(dt)

    def datetime(self, datetime=None):
        """ Get or Set the time as datetime tuple """
        if datetime is None:
            return self._get_datetime()
        else:
            self._set_datetime(*datetime)

    def seconds(self, seconds=None):
        """ Get or Set the time as seconds int """
        if seconds is None:
            return datetime2seconds(self._get_datetime())
        else:
            self._set_datetime(*seconds2datetime(seconds))

    def temp(self, force=False):
        """ Get temperature. This function waits until the RTC is ready. By default the chip does 1 read evey 64 seconds. (You can force an update.) """
        if force:
            self._bit(self._CONTROL, _BIT5, True)
            while self._bit(self._CONTROL, _BIT5):
                time.sleep_ms(1)
        while self._bit(self._STATUS, _BIT2):
            time.sleep_ms(1)
        buffer = self._read(self._TEMP, 2)
        return _twocplm2int((buffer[0] << 2) + (buffer[1] >> 6), 10) * 0.25

    def age_offset(self, value=None):
        """ Something magical I don't quite understand. See DS3231 datasheet. """
        if value is None:
            return _twocplm2int(self._read(self._AGING))
        self._write(self._AGING, _int2twocplm(value))

    def alarm_time(self, alarm_nr, mask=None, second=None, minute=None, hour=None, day_date=None):
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

        :param alarm_nr: 1 or 2
        :param mask: see above
        :param second: Must be None when setting Alarm 2
        :param minute:
        :param hour:
        :param day_date:
        :return: day_date, hour, minute, second, mask (seconds will be None on alarm 2)
        """
        get = mask is None and second is None and minute is None and hour is None and day_date is None
        if alarm_nr != 1 and alarm_nr != 2: raise Exception('Alarm id must be 1 or 2. Not %d ' % alarm_nr)

        if get:
            if alarm_nr == 1:
                buffer = self._read(self._ALARM1, 4)
                mask = ( # = A1M1 | A1M2 << 1 | A1M3 << 2 | A1M4 << 3 | DY/DT << 4
                    (buffer[0] & _BIT7) >> 7 | # A1M1
                    (buffer[1] & _BIT7) >> 6 | # A1M2
                    (buffer[2] & _BIT7) >> 5 | # A1M3
                    (buffer[3] & _BIT7) >> 4 | # A1M4
                    (buffer[3] & _BIT6) >> 5   # DY/DT
                )
                second = _bcd2bin(buffer[0] & ~_BIT7)
                minute = _bcd2bin(buffer[1] & ~_BIT7)
                hour = _bcd2bin(buffer[2] & ~_BIT7)
                day_date = _bcd2bin(buffer[3] & ~_BIT7 & ~_BIT6)
                return day_date, hour, minute, second, mask
            else: # alarm 2, no seconds to be had
                buffer = self._read(self._ALARM2, 3)
                mask = ( # = A2M2 << 1 | A2M3 << 2 | A2M4 << 3 | DY/DT << 4; A2M1 does not exist.
                    (buffer[0] & _BIT7) >> 6 |  # A2M2
                    (buffer[1] & _BIT7) >> 5 |  # A2M3
                    (buffer[2] & _BIT7) >> 4 |  # A2M4
                    (buffer[2] & _BIT6) >> 5    # DY/DT
                )
                minute = _bcd2bin(buffer[0] & ~_BIT7)
                hour = _bcd2bin(buffer[1] & ~_BIT7)
                day_date = _bcd2bin(buffer[2] & ~_BIT7 & ~_BIT6)
                return day_date, hour, minute, None, mask
        else: # set
            if alarm_nr == 1:
                if mask is not None:
                    self._bit(self._ALARM1 + 0, _BIT7, bool(mask & _BIT0)) # A1M1
                    self._bit(self._ALARM1 + 1, _BIT7, bool(mask & _BIT1)) # A1M2
                    self._bit(self._ALARM1 + 2, _BIT7, bool(mask & _BIT2)) # A1M3
                    self._bit(self._ALARM1 + 3, _BIT7, bool(mask & _BIT3)) # A1M4
                    self._bit(self._ALARM1 + 3, _BIT6, bool(mask & _BIT4)) # DY/DT
                if second is not None: self._write(self._ALARM1 + 0, bytes(((self._read(self._ALARM1 + 0) & _BIT7) + _bin2bcd(second), ))) # A1M1 << 7 | second in BCD
                if minute is not None: self._write(self._ALARM1 + 1, bytes(((self._read(self._ALARM1 + 1) & _BIT7) + _bin2bcd(minute), ))) # A1M2 << 7 | minute in BCD
                if hour is not None: self._write(self._ALARM1 + 2, bytes(((self._read(self._ALARM1 + 2) & _BIT7) + _bin2bcd(hour), ))) # A1M3 << 7 | hour in BCD
                if day_date is not None: self._write(self._ALARM1 + 3, bytes(((self._read(self._ALARM1 + 3) & 0b11000000) + _bin2bcd(day_date), ))) # A1M3 << 7 | DY/DT << 6 | day/date in BCD
            else:
                if mask is not None:
                    self._bit(self._ALARM2 + 0, _BIT7, bool(mask & _BIT1))  # A1M2
                    self._bit(self._ALARM2 + 1, _BIT7, bool(mask & _BIT2))  # A1M3
                    self._bit(self._ALARM2 + 2, _BIT7, bool(mask & _BIT3))  # A1M4
                    self._bit(self._ALARM2 + 2, _BIT6, bool(mask & _BIT4))  # DY/DT
                if second is not None: raise Exception('Alarm 2 does not have a seconds field.')
                if minute is not None: self._write(self._ALARM2 + 0, bytes(((self._read(self._ALARM2 + 0) & _BIT7) + _bin2bcd(minute),)))  # A2M2 << 7 | minute in BCD
                if hour is not None: self._write(self._ALARM2 + 1, bytes(((self._read(self._ALARM2 + 1) & _BIT7) + _bin2bcd(hour),)))  # A2M2 << 7 | hour in BCD
                if day_date is not None: self._write(self._ALARM2 + 2, bytes(((self._read(self._ALARM2 + 2) & _BIT7) + _bin2bcd(day_date),)))  # A2M2 << 7 | DY/DT << 6 | day/date in BCD

    def config(self, eosc=None, bbsqw=None, rs=None, intcn=None, a2ie=None, a1ie=None, en32khz=None):
        get = eosc is None and bbsqw is None and rs is None and intcn is None and a2ie is None and a1ie is None and en32khz is None
        if get:
            buffer = self._read(self._CONTROL, 2)
            return (
                bool(buffer[0] & _BIT7),  # EOSC
                bool(buffer[0] & _BIT6),  # BBSQW
                (buffer[0] & (_BIT4 | _BIT3)) >> 3,  # RS
                bool(buffer[0] & _BIT2),  # INTCN
                bool(buffer[0] & _BIT1),  # A2IE
                bool(buffer[0] & _BIT0),  # A1IE
                bool(buffer[1] & _BIT3),  # EN32kHz
            )
        if eosc is not None: self._bit()
        # todo: write


    def alarm(self, id=1, reset=True):
        # todo: write
        if id==1:
            register = _ALARM1
        elif id==2:
            register = _ALARM2
        else: raise Exception('Alarm id must be 1 or 2. Not %d ' % id)

    def dump(self):
        dt = self._get_datetime()
        print("Now: %04d-%02d-%02d %02d:%02d:%02d" % dt[0:6], ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[dt[6]])

        day_date, hour, minute, second, mask = self.alarm_time(1)
        print("Alarm 1: %d (%s) %02d:%02d:%02d" % (day_date, ('DT', 'DY')[mask >> 4], hour, minute, second), "Mask: {:04b}".format(mask & 0b1111))

        day_date, hour, minute, second, mask = self.alarm_time(2)
        print("Alarm 1: %d (%s) %02d:%02d" % (day_date, ('DT', 'DY')[mask >> 4], hour, minute), "Mask: {:04b}".format(mask & 0b1111))

        buffer = self._read(self._CONTROL, 2)
        print("EOSC     Enable battery backup               [True]      ", bool(buffer[0] & _BIT7))
        print("BBSQW    Enable battery backed square wave   [False]     ", bool(buffer[0] & _BIT6))
        print("RS       Square wave rate select             [8.192kHz]  ", ("1Hz", "1.024kHz", "4.096kHz", "8.192kHz")[(buffer[0] & (_BIT4 | _BIT3)) >> 3])
        print("INTCN    Interrupt control (SQW or INT)      [INT]       ", ("SQW", "INT")[(buffer[0] & _BIT2) >> 2])
        print("A2IE     Alarm 2 interrupt enable            [False]     ", bool(buffer[0] & _BIT1))
        print("A1IE     Alarm 1 interrupt enable            [False]     ", bool(buffer[0] & _BIT0))

        print("OSF      Oscillator Stop Flag                [False]     ", bool(buffer[1] & _BIT7))
        print("EN32kHz  Enable 32kHz Output                 [True]      ", bool(buffer[1] & _BIT3))
        print("BSY      Busy                                            ", bool(buffer[1] & _BIT2))
        print("A2F      Alarm 2 Flag                                    ", bool(buffer[1] & _BIT1))
        print("A1F      Alarm 1 Flag                                    ", bool(buffer[1] & _BIT0))

        print("Aging offset:        ", age_offset())
        print("Temperature:         ", self.temp())

    def _get_datetime(self):
        buffer = self._read(self._CALENDAR, 7)
        return (
            _bcd2bin(buffer[6]) + 2000,  # year
            _bcd2bin(buffer[5]),         # month
            _bcd2bin(buffer[4]),         # day
            _bcd2bin(buffer[2]),         # hour
            _bcd2bin(buffer[1]),         # minute
            _bcd2bin(buffer[0]),         # second
            _bcd2bin(buffer[3]) - 1,     # weekday
        )

    def _set_datetime(self, year=None, month=None, day=None, hour=None, minute=None, second=None, weekday=None):
        buffer = bytearray(self._read(self._CALENDAR, 7))
        if year is not None: buffer[6] = _bin2bcd(year - 2000)
        if month is not None: buffer[5] = _bin2bcd(month)
        if day is not None: buffer[4] = _bin2bcd(day)
        if hour is not None: buffer[2] = _bin2bcd(hour)
        if minute is not None: buffer[1] = _bin2bcd(minute)
        if second is not None: buffer[0] = _bin2bcd(second)
        if weekday is not None: buffer[3] = _bin2bcd(weekday) + 1
        self._write(self._CALENDAR, buffer)

    def _read(self, register, length=1):
        return self.i2c.readfrom_mem(self.address, register, length)

    def _write(self, register, data):
        i2c.writeto_mem(self.address, register, data)

    def _bit(self, register, mask, value=None):
        register_data = self._read(register)
        if value is None:
            return bool(mask & register_data)
        if bool(mask & register_data) != value:
            if value:
                register_data |= mask
            else:
                register_data &= mask
            self._write(register, bytes((register_data, )))
            return True
        return False
