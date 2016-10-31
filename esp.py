import os
import serial
import time
import binascii
import textwrap
import re

from wifi import WIFI_SSID, WIFI_PASS


def ctrl(key):
    # Thank you https://github.com/zeevro/esp_file_sender/
    return chr(ord(key.upper()) - ord('A') + 1)


class Esp:
    def __init__(self, port, baudrate):
        super().__init__()
        # self.raw = serial.Serial(port, baudrate)

        # if not self.raw.is_open:
        #     raise RuntimeError("Port {} won't open.".format(port))

    def __del__(self):
        self.reset()

    def kill(self):
        self.send(ctrl('C'), 2)

    def reset(self):
        # self.send(ctrl('D'), 5)
        pass

    def send(self, data, wait=0.100):
        print(data.replace('\r\n', ''))
        # self.raw.write(data.encode('ascii'))
        # time.sleep(wait)
        # out = self.raw.read_all()
        # print(out.decode('ascii'), end="")
        # return out

    def settings(self, data=None, app=None):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'boot.py'), 'rb') as f:
            text = f.read().decode('ascii')

        if data is None:
            data = {}
        data.setdefault('WIFI_SSID', WIFI_SSID)
        data.setdefault('WIFI_PASS', WIFI_PASS)
        for k, v in data.items():
            text += '{} = {!r}\r\n'.format(k, v)
        self.save_file('boot.py', text.encode('ascii'))

        if app is not None:
            app = app.replace('.py', '')
            text = 'from boot import *\r\n'
            text += "if machine.reset_cause() == SLEEP_RESET or not wait_for(timeout=5, message='To abort booting \"{}\", press GPIO0'):\r\n".format(app)
            text += '\timport {}\r\n'.format(app)
            text += '\t{}.main()\r\n'.format(app)
            self.save_file('main.py', text.encode('ascii'))

    def save_file(self, filename, text):
        # self.send(ctrl('E'))
        self.send('import os\r\n')
        # self.send('import ubinascii\r\n')
        self.send('import gc\r\n')
        self.send('gc.collect()\r\n')
        # self.send('os.remove("{}")\r\n'.format(filename))
        self.send('f = open("{}", "wb")\r\n'.format(filename))
        # for part in re.findall('.{1,100}', text.decode('ascii'), re.DOTALL):
        #     self.send('f.write(ubinascii.a2b_base64("{}"))\r\n'.format(binascii.b2a_base64(part.encode('ascii')).decode('ascii')[:-1]))
        for part in re.findall('.{1,1000}', text.decode('ascii'), re.DOTALL):
            self.send('f.write({!r})\r\n'.format(part))
        # self.send('f.write({!r})\r\n'.format(text))
        self.send('f.close()\r\n')
        self.send('del f\r\n')
        self.send('gc.collect()\r\n')
        # self.send(ctrl('D'))

    def delete(self, *params):
        self.send('import os\r\n')
        for param in params:
            self.send('os.remove({!r})\r\n'.format(param))


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('port', help='Serial port')
    parser.add_argument('-b', '--baudrate', help='Serial baudrate', type=int, default=115200)
    parser.add_argument('app', help='Input file')
    parser.add_argument('drivers', help='Extra driver files', nargs='*')

    args = parser.parse_args()

    esp = Esp(args.port, args.baudrate)

    esp.settings(app=args.app)

    with open('apps/' + args.app, 'rb') as in_f:
        esp.save_file(args.app, in_f.read())

    for file in args.drivers:
        with open('drivers/' + file, 'rb') as in_f:
            esp.save_file(file, in_f.read())

if __name__ == '__main__':
    main()
