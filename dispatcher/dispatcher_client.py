#!/usr/bin/python

## --------------------------------------------------------------
## Dispatcher client
## Author: Matous Jezersky - xjezer01@stud.fit.vutbr.cz
## All rights reserved
## --------------------------------------------------------------

#client ver 0.0.21

import socket, threading, time, random

BUFSIZE = 1024


class DispatcherClient():
    def __init__(self, idStr, dispServerIp, dispServerPort=2107):
        self.dispServerIp = dispServerIp
        self.dispServerPort = dispServerPort

        self.idStr = idStr#str(random.randint(0,10000))       
        self.data = {"message":"N/A", "battery":"N/A", "conn_quality":"N/A"}
        self.socket = None
        self.tunnels = {} #dict tunelu port:[TunnelClient, appIp, appPort, tunIp, tunPort] (viz addTunnel)
        self.dataSem = threading.Semaphore()
        self.msgFunction = None
        print "my id:", self.idStr

    def updateData(self):
        self.dataSem.acquire()
        try: # info o baterii
            f = open("/sys/class/power_supply/BAT0/capacity", "r")
            self.data["battery"] = f.read()+"%"
            f.close()
        except:
            self.data["battery"] = "N/A"

        if self.msgFunction != None:
            self.data["message"] = self.msgFunction()
        self.dataSem.release()

    def setData(self, data):
        self.dataSem.acquire()
        self.data = data
        self.dataSem.release()

    def getData(self):
        self.dataSem.acquire()
        retVal = str(self.data)
        self.dataSem.release()
        return retVal

    def establishConnection(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.dispServerIp, self.dispServerPort))
            msg = self.sock.recv(128) # prijmu HELLO
            if msg != "HELLO":
                self.sock.send("NACK")
                self.sock.close()
                raise Exception("bad data")
            self.sock.send("TUNNEL_CLIENT") # odeslu TUNNEL_CLIENT
            msg = self.sock.recv(128) # prjimu ACK
            if msg != "ID_REQUEST":
                self.sock.send("NACK")
                self.sock.close()
                raise Exception("bad data")
            self.sock.send(self.idStr) # odeslu id
            return True
        except Exception as err:
            print err, "- establish failed", self.dispServerIp, self.dispServerPort
            return False

    def mainloop(self):
        while 1:
            if self.establishConnection():
		print "Connected"
                try:
                    while 1:
                        inData = self.sock.recv(128) # prijmam data
                        if "DISPATCHER_DATA_REQUEST" in inData:
                            self.updateData()
                            self.sock.send(self.getData())
                        elif "ECHO" in inData:
                            self.sock.send("ECHO")
                        else:
                            self.sock.send("NACK")
                except KeyboardInterrupt: break
                except Exception as err:
                    print err
                    print "Lost connection with dispatcher server"
            time.sleep(1)
            print "Reconnecting..."
        self.sock.close()

#demo function for message content
def demoFunction():
    return str(time.ctime())


cloudServerIP = "10.8.0.1"
robotName = socket.gethostname()

dispClnt = DispatcherClient(robotName, cloudServerIP)
dispClnt.msgFunction = demoFunction
dispClnt.mainloop()
