#!/usr/bin/env python
#
# Initialise a modem connection, answer an incoming call and redirect data from the modem to a TCP/IP connection and vice versa.
# (c) 2019 Steve Crozier CC BY-SA license
# based on/kudos to tcp_serial_redirect.py from Chris Liechti
#
# example usage...
# python modem-tcp.py /dev/ttyACM0 a80sappleiibbs.ddns.net:6502

import sys
import socket
import serial
import serial.threaded
import time

class SerialToNet(serial.threaded.Protocol):
    """serial->socket"""
    def __init__(self):
        self.socket = None

    def __call__(self):
        return self

    def data_received(self, data):
        if self.socket is not None:
            self.socket.sendall(data)


if __name__ == '__main__':  # noqa
    import argparse

    parser = argparse.ArgumentParser(
        description='Simple Hayes modem handler and network (TCP/IP) redirector.',
        epilog="""\
NOTE: no security measures are implemented.
""")

    parser.add_argument(
        'SERIALPORT',
        help="serial port name")

    parser.add_argument(
        'HOST',
        help='telnet BBS host address/IP:port number')

    parser.add_argument(
        'BAUDRATE',
        type=int,
        nargs='?',
        help='set baud rate, default: %(default)s',
        default=9600)

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='suppress non error messages',
        default=False)

    parser.add_argument(
        '--develop',
        action='store_true',
        help='Development mode, prints Python internals on errors',
        default=False)

    group = parser.add_argument_group('serial port')

    group.add_argument(
        "--bytesize",
        choices=[5, 6, 7, 8],
        type=int,
        help="set bytesize, one of {5 6 7 8}, default: 8",
        default=8)

    group.add_argument(
        "--parity",
        choices=['N', 'E', 'O', 'S', 'M'],
        type=lambda c: c.upper(),
        help="set parity, one of {N E O S M}, default: N",
        default='N')

    group.add_argument(
        "--stopbits",
        choices=[1, 1.5, 2],
        type=float,
        help="set stopbits, one of {1 1.5 2}, default: 1",
        default=1)

    group.add_argument(
        '--rtscts',
        action='store_true',
        help='enable RTS/CTS flow control (default off)',
        default=False)

    group.add_argument(
        '--xonxoff',
        action='store_true',
        help='enable software flow control (default off)',
        default=False)

    group.add_argument(
        '--rts',
        type=int,
        help='set initial RTS line state (possible values: 0, 1)',
        default=None)

    group.add_argument(
        '--dtr',
        type=int,
        help='set initial DTR line state (possible values: 0, 1)',
        default=None)

    args = parser.parse_args()

    # connect to serial port
    ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True)
    ser.baudrate = args.BAUDRATE
    ser.bytesize = args.bytesize
    ser.parity = args.parity
    ser.stopbits = args.stopbits
    ser.rtscts = args.rtscts
    ser.xonxoff = args.xonxoff

    if args.rts is not None:
        ser.rts = args.rts

    if args.dtr is not None:
        ser.dtr = args.dtr

    if not args.quiet:
        sys.stderr.write(
            '--- Serial Hayes modem to TCP/IP redirect on {p.name}  {p.baudrate},{p.bytesize},{p.parity},{p.stopbits} ---\n'
            '--- type Ctrl-C / BREAK to quit\n'.format(p=ser))

    try:
        ser.open()
    except serial.SerialException as e:
        sys.stderr.write('Could not open serial port {}: {}\n'.format(ser.name, e))
        sys.exit(1)

    ser.flush()
    sys.stderr.write("--Initializing--\r\n")
    # Re-initialize the modem by ATI command, echo output to the console
    ser.write(b'ATI\r\n')
    sys.stderr.write("> " + ser.readline())
    sys.stderr.write("> " + ser.readline())
    sys.stderr.write("> " + ser.readline())
    sys.stderr.write("> " + ser.readline())
    time.sleep(0.5)

    sys.stderr.write("--Waiting for ring--\r\n")

    # Add a loop here to wait for ring interrupt
    try:
        while ser.ri == False:
            pass
            # just wait
    except KeyboardInterrupt:
        sys.exit(1)

    # When ring seen, copy buffer to console and send answer command
    sys.stderr.write("> " + ser.readline())
    sys.stderr.write("> " + ser.readline())
    sys.stderr.write('--Answering ring--\r\n')
    ser.write(b'ATA\r\n')
    sys.stderr.write("> " + ser.readline())


    # Loop to wait for 'CONNECT'
    while True:
        recstring=ser.readline()
        sys.stderr.write("> " + recstring)
        if 'CONNECT' in recstring:
            break

    # Delay to make sure modem is happy
    time.sleep(2)

    ser_to_net = SerialToNet()
    serial_worker = serial.threaded.ReaderThread(ser, ser_to_net)
    serial_worker.start()

    try:
        intentional_exit = False
        while intentional_exit == False:
            host, port = args.HOST.split(':')
            sys.stderr.write("--Opening connection to {}:{}...--\n".format(host, port))
            client_socket = socket.socket()
            try:
                client_socket.connect((host, int(port)))
            except socket.error as msg:
                sys.stderr.write('--WARNING: {}--\n'.format(msg))
                time.sleep(5)  # intentional delay on reconnection as client
                continue
            sys.stderr.write('--Connected--\n')
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                ser_to_net.socket = client_socket
                # enter network <-> serial loop
                while True:
                    try:
                        # Check for on-hook/hung-up modem
                        if ser.cd == False:
                            sys.stderr.write('--Line dropped--\n')
                            intentional_exit = True
                            break
                        # Copy socket data to modem port
                        data = client_socket.recv(1024)
                        if not data:
                            break
                        ser.write(data)                 # get a bunch of bytes and send them
                    except socket.error as msg:
                        if args.develop:
                            raise
                        sys.stderr.write('--ERROR: {}--\n'.format(msg))
                        # probably got disconnected
                        break
            except KeyboardInterrupt:
                intentional_exit = True
                raise
            except socket.error as msg:
                if args.develop:
                    raise
                sys.stderr.write('--ERROR: {}--\n'.format(msg))
            finally:
                ser_to_net.socket = None
                sys.stderr.write('--Disconnected--\n')
                client_socket.close()
                intentional_exit = True
    except KeyboardInterrupt:
        pass


    serial_worker.stop()
    time.sleep(1)

    # Enter command mode (don't do redback's here or below - serial worker seems to still be redirecting)
    ser.write(b'+++')
    time.sleep(1)
    # Send hang-up command
    ser.write(b'ATH\r\n')

    sys.stderr.write('\n--- exit ---\n')

