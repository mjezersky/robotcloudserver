#!/usr/bin/python

## --------------------------------------------------------------
## Dispatcher demo app client
## Author: Matous Jezersky - xjezer01@stud.fit.vutbr.cz
## All rights reserved
## --------------------------------------------------------------


## Example of a client for dispatcher control protocol.
## This is a line client, allowing the user to enter the commands manually

## Dispatcher control protocol commands:
## Bclient_ip#server_ip#bind_time ... bind client_ip to server_ip for amount of seconds specified in bind_time
##                                    ( example: link 10.8.0.10 to 10.7.0.5 for 1 minute: B10.8.0.1#10.7.0.5#60 )
## GET_ALL_DATA                   ... returns the JSON object containing information about connected clients )
## BINDINGS                       ... displays information about all bound IPs

import socket

try:

    data = "testdata"#raw_input("data=")

    print "mini debug app protocol type 'exit' to exit"
    
    

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", 2107))
    print "connected"
    msg = sock.recv(128) # prijmu HELLO
    if msg != "HELLO":
        sock.close()
        raise Exception("NO HELLO")
    sock.send("APP_CLIENT") # odeslu APP_CLIENT
    msg = sock.recv(128) # prijmu ACK
    if msg != "ACK":
        sock.close()
        raise Exception("NO ACK")
    while 1:
        data = raw_input("data>>>")
        if data == "exit": exit()
        sock.send(str(len(data))+"#") # odeslu delku dat
        sock.send(data) # odeslu data
        lenStr = ""
        lastch = ""
        while 1:
            lastch = sock.recv(1)
            if lastch == "#": break
            lenStr += lastch
        dataLen = int(lenStr)
        inData = sock.recv(dataLen)
        print inData
        if not inData: break
    sock.close()





except Exception as err:
    print err

raw_input("press enter to exit")
