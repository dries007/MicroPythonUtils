# MICROPYTHON

import esp
import machine
import gc
import micropython
import network
import time
import ds3231
import lcdi2c
import ubinascii
import sys
import socket
import websocket
import uhashlib
import json

esp.osdebug(None)
machine.freq(160000000)
micropython.alloc_emergency_exception_buf(200)

wlan = network.WLAN(network.STA_IF)
ap = network.WLAN(network.AP_IF)

SOFT_RESET = const(4)
SLEEP_RESET = const(5)
HARD_RESET = const(6)

print()
print('FLASH ID:    %s' % hex(esp.flash_id()))
print('WLAN MAC:    %s' % ':'.join('%02X' % b for b in wlan.config("mac")))
print('AP MAC:      %s' % ':'.join('%02X' % b for b in ap.config("mac")))

gc.collect()

print('Initial setup...')

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# Pinouts:
PIN_SCL = const(5)
PIN_SDA = const(4)

PIN_HEATING = const(12)
PIN_COOLING = const(13)

# 0 -> 0 = active, 1 -> 0 = inactive
RELAY_POLARITY = const(0)

PIN_ONEWIRE = const(14)

settings = {'utc_offset': 3600, 'target': 28.0, 'hyst': 0.25}

timer = machine.Timer(-1)

i2c = machine.I2C(machine.Pin(PIN_SCL), machine.Pin(PIN_SDA), freq=400000)
heating = machine.Pin(PIN_HEATING, machine.Pin.OUT, value=not RELAY_POLARITY)
cooling = machine.Pin(PIN_COOLING, machine.Pin.OUT, value=not RELAY_POLARITY)

rtc = ds3231.DS3231(i2c)
lcd = lcdi2c.LCD(i2c)
lcd.init()
lcd.display_control(True, False, False)
print('Initialized LCD')
gc.collect()

print('Testing heating')
lcd.print(b'Testing Heating')
heating(RELAY_POLARITY)
time.sleep(1)
heating(not RELAY_POLARITY)
time.sleep(1)

print('Testing cooling')
lcd.print(b'Testing Cooling')
cooling(RELAY_POLARITY)
time.sleep(1)
cooling(not RELAY_POLARITY)
time.sleep(1)

print('Starting WiFi')

AP_ESSID = b'Beer' + ubinascii.hexlify(wlan.config("mac"))[8:].upper()
AP_PASSWD = ubinascii.hexlify(wlan.config("mac"))[:8].upper()

wlan.active(True)
ap.active(True)
ap.config(essid=AP_ESSID, password=AP_PASSWD)

print('Initial setup done')


def lcd_status(line1, line2):
    if not heating():
        lcd.custom_char(0x00, [0b00100, 0b01110, 0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100])
    elif not cooling():
        lcd.custom_char(0x00, [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b11111, 0b01110, 0b00100])
    else:
        lcd.custom_char(0x00, [0b00000, 0b00000, 0b00000, 0b11111, 0b11111, 0b00000, 0b00000, 0b00000])

    if wlan.isconnected():
        lcd.custom_char(0x01, [0b00000, 0b00000, 0b00000, 0b11100, 0b00010, 0b11001, 0b00101, 0b10101])
    else:
        lcd.custom_char(0x01, [0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b00000, 0b00000, 0b10000])
    lcd.print(b'%-14s\x00\x01#\n%-16s#' % (line1, line2))


def timer_callback(*args):
    global lcd_count
    gc.collect()
    temp = rtc.temp()
    if 'target' not in settings:
        heating(not RELAY_POLARITY)
        cooling(not RELAY_POLARITY)
    else:
        t_min = settings['target'] - settings['hyst']
        t_max = settings['target'] + settings['hyst']
        if temp > t_max:
            cooling(RELAY_POLARITY)
            heating(not RELAY_POLARITY)
        elif temp < t_min:
            heating(RELAY_POLARITY)
            cooling(not RELAY_POLARITY)
        else:
            heating(not RELAY_POLARITY)
            cooling(not RELAY_POLARITY)

    lcd_count = (lcd_count + 1) % 5
    if lcd_count == 1:
        lcd_status(b'T Outside', b'%2.2f\xDF' % rtc.temp())
    elif lcd_count == 2:
        lcd_status(b'IP WiFi', wlan.ifconfig()[0] if wlan.isconnected() else 'Not connected')
    elif lcd_count == 3:
        if ap.isconnected():
            lcd_status(b'IP AP', ap.ifconfig()[0])
        else:
            lcd_status(b'SSID: %s' % AP_ESSID, b'Pass: %s' % AP_PASSWD)
    else:
        tmp = ds3231.seconds2datetime(ds3231.datetime2seconds(rtc.get_datetime()) + settings['utc_offset'])
        lcd_status(b'%02d:%02d' % (tmp[3], tmp[4]), b'%4d-%02d-%02d' % (tmp[0], tmp[1], tmp[2]))

lcd_count = 0
timer_callback()
timer.init(period=5000, mode=machine.Timer.PERIODIC, callback=timer_callback)

print('Socket setup...')


def socket_handler(listen_s):
    global settings
    gc.collect()

    try:
        client, remote_addr = listen_s.accept()
        if not client.readline() == b'GET / HTTP/1.1\r\n':
            client.close()
            return

        ws = None
        ws_key = None

        while True:
            line = client.readline()
            if line == b'\r\n' or line == b'':
                break
            h, v = [x.strip() for x in line.split(b':', 1)]
            if h == b'Connection':
                if v == b'Upgrade':
                    ws = True
            elif h == b'Sec-WebSocket-Key':
                ws_key = v
            print(v, h)
        if not ws:
            client.close()
            return
        print('Got valid socket connection from', remote_addr)
        d = uhashlib.sha1(ws_key)
        d.update(b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
        client.send(b'\\n'
                    b'HTTP/1.1 101 Switching Protocols\r\n'
                    b'Upgrade: websocket\r\n'
                    b'Connection: Upgrade\r\n'
                    b'Sec-WebSocket-Accept: ')
        client.send(ubinascii.b2a_base64(d.digest())[:-1])
        client.send(b'\r\n\r\n')
        ws = websocket.websocket(client)
        # client.setblocking(False)
        # client.setsockopt(socket.SOL_SOCKET, 20, socket_handler_inner)
        gc.collect()

        cmd = ws.readline().strip()
        if len(cmd) == 0:
            ws.close()
            client.close()
            return
        elif cmd == b'get':
            ws.write(json.dumps(settings))
            ws.write(b'OK\n')
        elif cmd == b'set':
            settings = json.loads(ws.readline())
            ws.write(b'OK\n')
        elif cmd == b'exec':
            try:
                exec(ws.readline())
                ws.write(b'OK\n')
            except Exception as e:
                print('error', e)
                ws.write(b'ERROR\n')
                ws.write(json.dumps(repr(e)))
                ws.write(b'\n')
        else:
            ws.write(b'ERROR\nUnknown action')
            ws.write(cmd)
            ws.write(b'\n')
    except Exception as e:
        print('Error handing socket:', e)

listen_s = socket.socket()
listen_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_s.bind(("0.0.0.0", 80))
listen_s.listen(1)
listen_s.setsockopt(socket.SOL_SOCKET, 20, socket_handler)

print('Socket setup done.')
