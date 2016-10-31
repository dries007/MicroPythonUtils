# MICROPYTHON

import machine
import gc
import esp
import machine
import network
import micropython

esp.osdebug(None)
machine.freq(160000000)
micropython.alloc_emergency_exception_buf(200)

wlan = network.WLAN(network.STA_IF)
wlan.active(False)
ap = network.WLAN(network.AP_IF)
ap.active(False)

# DEBUG causes long sleep cycles to be only 5 sec
DEBUG = True

SOFT_RESET = 4
SLEEP_RESET = 5
HARD_RESET = 6


def _version():
    import sys
    return '%s/%s' % (sys.implementation.name, '.'.join(str(x) for x in sys.implementation.version))


def _uuid():
    import ubinascii
    return ubinascii.hexlify(machine.unique_id()).decode('ascii')

UUID = _uuid()
PYTHON_VERSION = _version()

del _uuid
del _version
gc.collect()

RTC = machine.RTC()
RTC.irq(trigger=RTC.ALARM0, wake=machine.DEEPSLEEP)

P0 = machine.Pin(0, machine.Pin.OPEN_DRAIN)


def long_sleep(blocks_30min):
    # 0 means cancel running sleep
    RTC.memory(blocks_30min.to_bytes(4))
    if blocks_30min != 0:
        print('Long sleep for %.1f hours' % (blocks_30min/2))
        deep_sleep(1800 if not DEBUG else 5)


def deep_sleep(time_sec):
    # if time_sec > 2100:
    #     print('MAX SLEEP IS 2100 sec (71 min)!! ', end='')
    #     time_sec = 2100
    print('Deep sleep for %d min %d sec.' % (time_sec / 60, time_sec % 60))
    RTC.alarm(RTC.ALARM0, time_sec * 1000)
    machine.deepsleep()


def wait_for(button=P0, pull_up=True, timeout=None, message='Press GPIO0 to abort.'):
    import time
    prompt = ''
    if message is not None:
        prompt += message
    if timeout is not None:
        prompt += ' (Timeout: %ds)' % timeout
    print(prompt)
    start = time.time()
    while True:
        if timeout is not None and time.time() - start > timeout:
            return False
        if not pull_up and button.value():
            return True
        if pull_up and not button.value():
            return True


def timestamp():
    now = RTC.datetime()
    return '%02d-%02d-%02d %02d:%02d:%02d.%03d' % (now[0], now[1], now[2], now[4], now[5], now[6], now[7])


def do_connect():
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect("WIFI_SSID", "WIFI_PASS")
        while not wlan.isconnected():
            if not P0.value():
                print('Skipped network with GPIO0')
                return False
            pass
    return True


if __name__ == "__main__":
    import esp
    esp.osdebug(None)
    machine.freq(160000000)
    print()
    print('VERSION:     %s' % PYTHON_VERSION)
    print('UUID:        %s' % UUID)
    print('FLASH ID:    %s' % hex(esp.flash_id()))
    print('WLAN MAC:    %s' % ':'.join('%02X' % b for b in wlan.config("mac")))
    print('AP MAC:      %s' % ':'.join('%02X' % b for b in ap.config("mac")))
    try:
        print('WAKEUP:      %s' % {SOFT_RESET: 'Software reset', SLEEP_RESET: 'Deep sleep', HARD_RESET: 'Hard reset'}[machine.reset_cause()])
    except KeyError:
        print('WAKEUP:      ERROR?!')

    if machine.reset_cause() == SLEEP_RESET:
        i = int.from_bytes(RTC.memory())
        if i > 0:
            long_sleep(i - 1)
    else:
        long_sleep(0)

    gc.collect()
