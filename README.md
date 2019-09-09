# modem-tcp
Initialise a modem connection, answer an incoming call and redirect data from the modem to a TCP/IP connection and vice versa.
A great way to get old computers online by connecting a USB modem to a Raspberry Pi.  The Pi modem can then be connected to your old machine using a ringdown/line simulator such as https://www.amazon.com/Viking-DLE-200B-Two-Way-Line-Simulator/dp/B004PXK314 (or a real POTS phone line if you prefer).

Usage: modem-tcp.py [-h] [-q] [--develop] [--bytesize {5,6,7,8}]
                    [--parity {N,E,O,S,M}] [--stopbits {1,1.5,2}] [--rtscts]
                    [--xonxoff] [--rts RTS] [--dtr DTR]
                    SERIALPORT HOST [BAUDRATE]

Noting that HOST should be in the format Hostname:Portnumber
Typically a USB modem will appear to the Pi as /dev/ttyACM0 but check for correct detection with lsusb then ls /dev/tty*

Example usage: python modem-tcp.py /dev/ttyACM0 a80sappleiibbs.ddns.net:6502

For a good list of telnet BBS's see https://www.telnetbbsguide.com/

This software is distributed under a Creative Commons Attribution Share Alike CC BY-SA license, allowing modification for your own purposes https://creativecommons.org/share-your-work/licensing-types-examples/#by-sa
