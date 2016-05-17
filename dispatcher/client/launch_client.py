#!/usr/bin/python

## Dispatcher client launch script
## (for client version 1.x)

from dispatcher_client import *

## Demo function for message content
def demoFunction():
    return str(time.ctime())

## IP address of dispatcher server to connect to
dispatcherServerIP = "10.8.0.1"

## Unique ID (name) of the dispatcher client
clientName = socket.gethostname()

## Create dispatcher client instance - required arguments:
## idStr          ... unique string for easier client identification, name or similar
## dispServerIp   ... IP address of the dispatcher server to connect to
## Optional arguments:
## dispServerPort ... port of the dispatcher server to connect to (default 2107)
## batteryTopic   ... ROS topic for reading battery state, should be a std_msgs/String with data containing the battery percentage
##                    if rospy module is not available, this argument is ignored
##                    if set to None or ignored, /sys/class/power_supply/BAT0/capacity is used
##                    (default None)
dispClnt = DispatcherClient(clientName, dispatcherServerIP, batteryTopic="/battery")

## Custom function for the message, that will be displayed in dispatcher interface
## Return value of the function has to be string
dispClnt.msgFunction = demoFunction

## Launch the client
dispClnt.mainloop()
