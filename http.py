# HTTP helper functions for MicroPython (on ESP8266)
# Copyright (c) 2016 Dries007
# License: MIT

# To be used in combo with boot.py

from boot import *


def http_get(host, url, headers=None, port=80):
    import socket
    headers_ = {'Host': host, 'User-Agent': PYTHON_VERSION, 'Connection': 'close', 'UUID': UUID}
    if headers:
        for k, v in headers.items():
            headers_[k] = v
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.1\r\n' % url, 'utf8'))
    for k, v in headers_.items():
        s.send(bytes('%s: %s\r\n' % (k, v), 'utf8'))
    s.send(bytes('\r\n', 'utf8'))
    resp = ''
    while True:
        data = s.recv(100)
        if data:
            resp += str(data, 'utf8')
        else:
            break
    return resp.split("\r\n\r\n", 1)


def http_post(host, url='/', data='', headers=None, port=80):
    import socket
    headers_ = {'Host': host, 'User-Agent': PYTHON_VERSION, 'Connection': 'close', 'UUID': UUID, 'Content-Length': len(data)}
    if headers:
        for k, v in headers.items():
            headers_[k] = v
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('POST %s HTTP/1.1\r\n' % url, 'utf8'))
    for k, v in headers_.items():
        s.send(bytes('%s: %s\r\n' % (k, v), 'utf8'))
    s.send(bytes('\r\n', 'utf8'))
    s.send(bytes(data, 'utf8'))
    s.send(bytes('\r\n', 'utf8'))
    resp = ''
    while True:
        data = s.recv(100)
        if data:
            resp += str(data, 'utf8')
        else:
            break
    return resp.split("\r\n\r\n", 1)
