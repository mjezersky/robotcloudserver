#!/usr/bin/python

## --------------------------------------------------------------
## Dispatcher client
## Author: Matous Jezersky - xjezer01@stud.fit.vutbr.cz
## All rights reserved
## --------------------------------------------------------------

#client ver 1.1.0

import socket, threading, time, random, signal, sys

# SIGINT handler (only active if rospy is enabled)
def sigint_handler(signal, frame):
        print '\nInterrupted\n'
        sys.exit(0)

# check for rospy availability
try:
    import rospy
    from std_msgs.msg import String
    ROSPY_AVAILABLE = True
    signal.signal(signal.SIGINT, sigint_handler)
except ImportError:
    ROSPY_AVAILABLE = False
    print "Warning: rospy module unavailable - Functions using it have been disabled."

# socket buffer size
BUFSIZE = 1024

# the main and only class of the client
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
        print "This client's ID:", self.idStr
        print "Attempting to connect..."

    # get battery information from the set source
    def getBatteryInfo(self):
        global ROSPY_AVAILABLE
        if (self.batteryTopic == None) or (not ROSPY_AVAILABLE):
            f = open("/sys/class/power_supply/BAT0/capacity", "r")
            batState = f.read()+"%"
            f.close()
            return batState
        else:
            return self.batteryState

    # rospy callback
    def updateBattery(self, newState):
        # semaphore is unnecessary as we don't mind getting slightly outdated value
        self.batteryState = str(newState.data)
        
    # update data that is sent to the dispatcher - battery info and message
    def updateData(self):
        self.dataSem.acquire()
        try: # battery info
            self.data["battery"] = self.getBatteryInfo()
        except:
            self.data["battery"] = "N/A"

        if self.msgFunction != None:
            self.data["message"] = self.msgFunction()
        self.dataSem.release()

    # change data that is sent to the dispatcher
    def setData(self, data):
        self.dataSem.acquire()
        self.data = data
        self.dataSem.release()

    # get data that is sent to the dispatcher
    def getData(self):
        self.dataSem.acquire()
        retVal = str(self.data)
        self.dataSem.release()
        return retVal

    # method for initialization and establishing of a connection
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
        except KeyboardInterrupt:
            exit()
        except Exception as err:
            print err, "- establish failed at", self.dispServerIp, self.dispServerPort
            return False

    # main method of the client - it handles connecting to the server and also responds to the requests
    def mainloop(self):
        global ROSPY_AVAILABLE
        if ROSPY_AVAILABLE and self.batteryTopic != None:
            rospy.init_node('dclnt_bat_reader', anonymous=True)
            rospy.Subscriber(self.batteryTopic, String, self.updateBattery)
        while 1:
            # try to establish connection
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
                # IOError is thrown by both sockets on unexpected closure and by rospy
                except IOError as err:
                        print err
                        print "Lost connection with dispatcher server"
                except Exception as err:
                    print err
                    print "Lost connection with dispatcher server"
            try:
                time.sleep(1)
                print "Reconnecting..."
            except:
                print "\nExiting..."
                self.sock.close()
                exit()
        self.sock.close()
