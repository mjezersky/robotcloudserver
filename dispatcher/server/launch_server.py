#!/usr/bin/python

## Dispatcher server launch script
## (for dispatcher_server version 1.x) 

from dispatcher_server import *

## Create Dispatcher with following optional arguments:
## listenOnIP        ... bind dispatcher server to listen on ip - for dispatcher clients (default "0.0.0.0")
## listenOnPort      ... listen on specific port (default 2107)
## interruptOnRebind ... when the bindings change for a client, interrupt all their connections (default True)
disp = Dispatcher(listenOnPort=2107)

## Map ports from user clients to dispatcher clients, required arguments:
## appListenPort ... source port - the port to which user clients connect
## serverPort    ... destination port - the port of the server application on dispatcher clients
## Optional arguments:
## appListenIP   ... bind the server to listen on specific IP/interface (default "0.0.0.0")
## udp           ... if set to True, protocol used will be UDP instead of TCP (default False)
## udpTunnelIP   ... listen on IP/interface for UDP communication from the dispatcher clients !mandatory if udp is set to True! (default None)
disp.addTunnel(9090, 9090)
disp.addTunnel(2110, 80)


## Example of an UDP tunnel:
#disp.addTunnel(20000, 20001, udp=True, udpTunnelIP="0.0.0.0")

# Launch the server
disp.startServer()
