#!/usr/bin/python

## --------------------------------------------------------------
## Dispatcher client
## Author: Matous Jezersky - xjezer01@stud.fit.vutbr.cz
## All rights reserved
## --------------------------------------------------------------

#client ver 0.0.30

import socket, threading, time, random
try:
    import rospy
    from std_msgs.msg import String
    ROSPY_AVAILABLE = True
except ImportError:
    ROSPY_AVAILABLE = False
    print "Warning: rospy module unavailable - Functions using it have been disabled."

BUFSIZE = 1024


class DispatcherClient():
    def __init__(self, idStr, dispServerIp, dispServerPort=2107, batteryTopic = None):
        self.dispServerIp = dispServerIp
        self.dispServerPort = dispServerPort

        self.idStr = idStr      
        self.data = {"message":"N/A", "battery":"N/A", "conn_quality":"N/A"}
        self.socket = None
        self.dataSem = threading.Semaphore()
        self.msgFunction = None
        self.batteryTopic = batteryTopic
        self.batteryState = "N/A"
        print "my id:", self.idStr

    def getBatteryInfo(self):
        global ROSPY_AVAILABLE
        if (self.batteryTopic == None) or (not ROSPY_AVAILABLE):
            f = open("/sys/class/power_supply/BAT0/capacity", "r")
            batState = f.read()+"%"
            f.close()
            return batState
        else:
            return self.batteryState

    #rospy callback
    def updateBattery(self, newState):
        # semaphore is unnecessary as we don't mind getting slightly outdated value
        self.batteryState = str(newState.data)
        

    def updateData(self):
        self.dataSem.acquire()
        try: # battery info
            self.data["battery"] = self.getBatteryInfo()
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
            msg = self.sock.recv(128) # receive HELLO
            if msg != "HELLO":
                self.sock.send("NACK")
                self.sock.close()
                raise Exception("bad data")
            self.sock.send("TUNNEL_CLIENT") # respond with TUNNEL_CLIENT
            msg = self.sock.recv(128) # receive ACK
            if msg != "ID_REQUEST":
                self.sock.send("NACK")
                self.sock.close()
                raise Exception("bad data")
            self.sock.send(self.idStr) # respond with id
            return True
        except Exception as err:
            print err, "- establish failed", self.dispServerIp, self.dispServerPort
            return False

    def mainloop(self):
        global ROSPY_AVAILABLE
        if ROSPY_AVAILABLE and self.batteryTopic != None:
            rospy.init_node('dclnt_bat_reader', anonymous=True)
            rospy.Subscriber(self.batteryTopic, String, self.updateBattery)
        while 1:
            if self.establishConnection():
		print "Connected"
                try:
                    while 1:
                        inData = self.sock.recv(128) # request from dispatcher server
                        if "DISPATCHER_DATA_REQUEST" in inData:
                            self.updateData()
                            self.sock.send(self.getData())
                        elif "ECHO" in inData: # echo for RTT measurement
                            self.sock.send("ECHO")
                        else:
                            self.sock.send("NACK")
                except KeyboardInterrupt: break
                except IOError: break
                except Exception as err:
                    print err
                    print "Lost connection with dispatcher server"
            time.sleep(1)
            print "Reconnecting..."
        self.sock.close()

#demo function for message content, must return string
def demoFunction():
    return str(time.ctime())


cloudServerIP = "10.8.0.1"
robotName = socket.gethostname()

dispClnt = DispatcherClient(robotName, cloudServerIP)
dispClnt.msgFunction = demoFunction
dispClnt.batteryTopic = "/battery"
dispClnt.mainloop()
