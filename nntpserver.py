#!/usr/bin/python

import socket, sys, os, signal

import nntp

signal.signal(signal.SIGCHLD, signal.SIG_IGN)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 4321))
s.listen(1)

while True:
    conn, addr = s.accept()
    pid = os.fork() 
    if pid > 0:
        conn.close()
    else:
        nntp.NNTPServer(input=conn.makefile('r'), output=conn.makefile('w')).process_commands()
        conn.close()
        sys.exit(0)
