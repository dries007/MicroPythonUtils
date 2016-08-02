import binascii
import serial
import time


def ctrl(key):
    # Thank you https://github.com/zeevro/esp_file_sender/
    return chr(ord(key.upper()) - ord('A') + 1)


class Esp:
    def __init__(self, port, baudrate):
        super().__init__()
        self.raw = serial.Serial(port, baudrate)

        if not self.raw.is_open:
            raise RuntimeError("Port {} won't open.".format(port))

        self.kill()
        self.reset()

    def kill(self):
        self.send(ctrl('C'), 2)

    def reset(self):
        self.send(ctrl('D'), 5)

    def send(self, data, wait=0.100):
        # print(data.encode('ascii'))
        self.raw.write(data.encode('ascii'))
        time.sleep(wait)
        out = self.raw.read_all()
        print(out.decode('ascii'), end="")
        return out

    def upload(self, filename):
        with open(filename, 'rb') as in_f:
            text = in_f.read()
            self.send(ctrl('E'))
            self.send('with open("{}", "wb") as f:\r\n'.format(filename))
            self.send('\timport ubinascii\r\n')
            self.send('\tf.write(ubinascii.a2b_base64("{}"))\r\n'.format(binascii.b2a_base64(text).decode('ascii')[:-1]))
            self.send(ctrl('D'))
        self.reset()


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('port', help='Serial port')
    parser.add_argument('-b', '--baudrate', help='Serial baudrate', type=int, default=115200)
    parser.add_argument('input', help='Input files', nargs='+')

    args = parser.parse_args()

    esp = Esp(args.port, args.baudrate)

    for file in args.input:
        esp.upload(file)

if __name__ == '__main__':
    main()

