#!/usr/bin/python

## --------------------------------------------------------------
## Dispatcher server
## Author: Matous Jezersky - xjezer01@stud.fit.vutbr.cz
## All rights reserved
## --------------------------------------------------------------

SERVER_VERSION = "1.1.0"

import socket
import threading
import time
import logging
import signal

# enable logging into dispatcher_server.log
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d.%m.%Y %H:%M:%S', filename='dispatcher_server.log',level=logging.DEBUG)

# socket buffer size
BUFSIZE = 1024

# thread for TCP communication (to be launched twice for each connection, once for each direction)
class TunnelCommThread(threading.Thread):

    # since __init__ is being used by threading.Thread, once the class instance is initialized, use config to set it up
    # same principle is used by other classes that inherit from threading.Thread
    def config(self, outSockClnt, inSockClnt, clientIP):
        self.daemon = True
        self.outSockClnt = outSockClnt
        self.inSockClnt = inSockClnt
        self.clientIP = clientIP

    def run(self):
        try:
            while 1:
                # receive data from the server
                data = self.outSockClnt.recv(BUFSIZE)
                if not data: break
                # send them to the client
                self.inSockClnt.send(data)
        except Exception as err:
            print err, "commThread"
            logging.warning("TunnelCommThread - %s", str(err))
        try:
            self.outSockClnt.close()
            self.inSockClnt.close()
        except:
            pass
        Collector.currCollector.removeActiveThread(self.clientIP, self)


# thread for UDP communication
class TunnelUDPThread(threading.Thread):
    def config(self, inSockClnt, outSockClnt, addr):
        self.daemon = True
        self.inSockClnt = inSockClnt
        self.outSockClnt = outSockClnt
        self.addr = addr
        self.clientIP, port = addr

    def run(self):
        try:
            while 1:
                # receive data from server
                data, server = self.outSockClnt.recvfrom(BUFSIZE)
                if not data: break
                # send data back to the client
                # check whether the link still exists
                udpThread = Collector.currCollector.getUDPThread(self.addr)
                if udpThread == None: break
                self.inSockClnt.sendto(data, self.addr)
        except:
            # not reporting any exceptions,the link will simply close
            pass
        self.outSockClnt.close()
        Collector.currCollector.removeUDPThread(self.addr)
        Collector.currCollector.removeActiveThread(self.clientIP, self)


# main thread for a single tunnel/route - it handles all incomming connections and spawns new threads for each one that is allowed
class Tunnel(threading.Thread):
    def config(self, appListenIP, appListenPort, serverPort, udp=False):
        self.appListenIP = appListenIP
        self.appListenPort = appListenPort
        self.serverPort = serverPort
        self.udp = udp
        # server IP will be acquired from bindings
        self.serverIP = None
        self.daemon = True

    def interrupt(self):  # deprecated
        try:
            self.inSockClnt.close()
        except Exception as err:
            pass
        self.interrupted = True

    # shut down completely, ingoring any errors
    def shutdown(self):
        try: self.inSock.close()
        except: pass
        try: self.outSock.close()
        except: pass

    def run(self):

        ## UDP TUNNEL
        if self.udp:
            self.inSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.inSock.bind((self.appListenIP, self.appListenPort))
            # interrupt and shutdown will have the same effect, as UDP doesn't have active connections like TCP
            self.inSockClnt = self.inSock 
            self.outSock = None
            
            while 1:
                udpThread = None
                try:
                    data, (clnt_ip, clnt_port) = self.inSock.recvfrom(BUFSIZE)
                    addr = (clnt_ip, clnt_port)

                    self.serverIP = Collector.getBoundIP(clnt_ip)
                    if self.serverIP != None:                

                        # check whether there is an UDP thread for this address, if not, make one (port where to send data back is required)
                        udpThread = Collector.currCollector.getUDPThread(addr)
                        if udpThread == None:
                            
                            #binding = Collector.currCollector.setUDPBinding(clnt_ip, clnt_port)
                            self.outSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            self.outSock.settimeout(10)

                            # relay the data to the server
                            # this can be done as socket operations in python are atomic
                            self.outSock.sendto(data, (self.serverIP, self.serverPort))

                            udpThread = TunnelUDPThread()
                            udpThread.config(self.inSock, self.outSock, addr)
                            udpThread.start()
                            Collector.currCollector.addUDPThread(addr, udpThread)
                            Collector.currCollector.addActiveThreads(clnt_ip, udpThread, None)

                        else:
                            # relay the data to the server
                            # this can be done as socket operations in python are atomic
                            udpThread.outSockClnt.sendto(data, (self.serverIP, self.serverPort))

                except socket.error as err:
                    # won't print anything here, as it may be just unauthorized connections, which might take unnecessary resources
                    #pass
                    Collector.currCollector.removeUDPThread(addr)
                    print err
                
        ## TCP TUNNEL 
        else:
            self.inSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.inSock.bind((self.appListenIP, self.appListenPort))
            self.inSock.listen(1)

            self.inSockClnt = None
            
            while 1:
                self.interrupted = False
                
                # client connects
                try:
                    self.inSockClnt, (clnt_ip, clnt_no) = self.inSock.accept()
                except Exception as err:
                    logging.error("Tunnel sock accept - %s", str(err))
                    print "Fatal: accept failed -", err
                    self.inSockClnt.close()
                    return

                self.serverIP = Collector.getBoundIP(clnt_ip)
                if self.serverIP != None:
                    try:
                        # make socket to connect to the server
                        self.outSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.outSock.connect((self.serverIP, self.serverPort))

                        # once connected, create communication threads
                        self.outThread = TunnelCommThread()
                        self.outThread.config(self.outSock, self.inSockClnt, clnt_ip)
                        self.outThread.start()
                        self.inThread = TunnelCommThread()
                        self.inThread.config(self.inSockClnt, self.outSock, clnt_ip)
                        self.inThread.start()

                        # add new threads to the list, so they can be terminated when connection is to be interrupted
                        Collector.currCollector.addActiveThreads(clnt_ip, self.outThread, self.inThread)
                        
                    except Exception as err:
                        print "CONNERR:", err
                        self.inSockClnt.close()
                        
                else:  # serverIP None
                    logging.info("Unbound connection attempt - %s", clnt_ip)
                    print "*unbound connection attempt: " + clnt_ip + "*"
                    self.inSockClnt.close()
        print "Tunnel thread stopped"
        logging.warning("Tunnel thread stopped.")
        self.inSockClnt.close()


# timer class, used for checking of bindings expiration times
class Timer(threading.Thread):
    def config(self):
        self.daemon = True

    def run(self):
        while 1:
            Collector.currCollector.unbindExpired(time.time())
            time.sleep(2) # time period for checking for bind expiration


# class for link between dispatcher and an application using the configuration protocol
class DispatcherAppLink(threading.Thread):
    def config(self, sock, clntIP):
        self.sock = sock
        self.clntIP = clntIP
        self.daemon = True

    def run(self):
        try:
            self.mainloop()
        except Exception as err:
            print err
            self.sock.close()
            print "dispatcher app link closed"

    # method to handle received data and return a response string
    def handleData(self, data):
        # handle GET_ALL_DATA message
        if data == "GET_ALL_DATA":
            dataArr = []
            dataDict = Collector.currCollector.getData()
            for i in dataDict:
                if dataDict[i] == "":
                    dataDict[i] = "{}"
                dataArr.append("'" + str(i) + "' : " + dataDict[i])
            if dataArr == []:
                return "{}"
            dataStr = "{ 'bindings': " + Collector.currCollector.getBindings()
            dataStr += ", 'clients': { " + ", ".join(dataArr) + " } }"
            dataStr = dataStr.replace("'", '"')  # json requires " instead of '
            return dataStr
        
        # handle BINDINGS message
        elif data == "BINDINGS":
            return Collector.currCollector.getBindings()

        # handle other messages
        else:
            if len(data) > 0:
                if data[0] == "G":
                    # message format: "Gclient_ame"
                    try:
                        linkID = data[1::]
                        dataDict = Collector.currCollector.getData()
                        return dataDict[linkID]
                    except Exception as err:
                        print err
                        return "UNAVAILABLE"

                elif data[0] == "B":
                    # message format: "Bclient_ip#server_ip#lease_sec"
                    try:
                        content = data[1::]
                        ips = content.split("#")
                        Collector.bindIP(ips[0], ips[1], int(ips[2]))
                        return "ACK"
                    except Exception as err:
                        print err
                        return "UNAVAILABLE"

                else:
                    return "BAD_REQUEST"

    # main loop of the configuration protocol server
    def mainloop(self):
        while 1:
            lenStr = ""
            lastch = ""
            while 1:
                lastch = self.sock.recv(1)
                if not lastch:
                    self.sock.close()
                    return
                if lastch == "#": break
                lenStr += lastch
            dataLen = int(lenStr)
            data = self.sock.recv(dataLen)
            if not data: break
            resp = self.handleData(data)
            self.sock.send(str(len(resp)) + "#")
            self.sock.send(resp)

        self.sock.close()


# thread handling Dispatcher clients, each thread handles one client, each has their unique linkID (name)

class DispatcherLink(threading.Thread):
    tunnelRequest = False  # deprecated

    def config(self, linkID, sock, clientIP):
        self.daemon = True
        self.collector = None
        self.linkID = linkID
        self.clientIP = clientIP
        self.sock = sock
        self.sem = threading.Semaphore()  # deprecated
        self.semSock = threading.Semaphore()  # semaphore for sendSafe

    def requestApp(self, tunnelPort):  # deprecated
        try:
            self.sendSafe("DISPATCHER_APP_REQUEST#" + str(tunnelPort))
            return True
        except:
            return False

    def run(self):
        try:
            self.mainloop()
        except socket.error:
            pass
        except Exception as err:
            print err
        self.sock.close()
        if self.collector != None:
            self.collector.removeLink(self.linkID)
        logging.info("Dispatcher client disconnected - %s", self.clientIP)
        print "Dispatcher client disconnected:", self.clientIP

    # method for measuring Round Trip Time using ECHO message
    def measureRTT(self):
        self.sendSafe("ECHO", requireAck=False)
        t0 = time.time()
        data = self.sock.recv(16)
        t1 = time.time()
        if data == "ECHO":
            return str(int((t1 - t0) * 1000))  # convert RTT to miliseconds
        else:
            return "N/A"

    def mainloop(self):
        logging.info("Dispatcher client connected - %s", self.clientIP)
        print "Dispatcher client connected:", self.clientIP
        while 1:
            self.sendSafe("DISPATCHER_DATA_REQUEST", requireAck=False)
            data = self.sock.recv(1024)
            if data == "" or data == None:
                break
            rtt = self.measureRTT()
            dataWrapped = "{ 'ip':'" + str(self.clientIP) + "', 'data':" + data + ", 'rtt':'" + rtt + "' }"
            Collector.currCollector.setData(self.linkID, dataWrapped)
            time.sleep(1)

    # odeslani dat pres self.sock se semaforem a cekam na ack
    def sendSafe(self, data, requireAck=True):
        self.semSock.acquire()
        try:
            self.sock.send(data)
            if requireAck:
                # print "reqack"
                self.sock.settimeout(2)
                if self.sock.recv(8) != "ACK": raise Exception("sendSafe_NACK")
                self.sock.settimeout(None)
                # print "gotack"
        except Exception as err:
            if requireAck:
                logging.error("sendSafe: reqAck failed - %s", self.clientIP)
                print "reqAck fail"
            self.semSock.release()
            raise err
        self.semSock.release()

    def getData(self):  # deprecated
        self.sem.acquire()
        data = self.data
        self.sem.release()
        return data

    def setData(self, data):  # deprecated
        self.sem.acquire()
        self.data = "{ 'ip':'" + str(self.clientIP) + "', 'data':" + data + " }"
        self.sem.release()


# data collector - collects information from connected Dispatcher clients and manages shared data access
class Collector():
    currCollector = None

    # get the IP of the server, that is bound to the client IP passed in the argument
    @staticmethod
    def getBoundIP(IP):
        return Collector.currCollector.bindingGet(IP)

    # bind clientIP to serverIP for the duration of bindTime
    @staticmethod
    def bindIP(clientIP, serverIP, bindTime):
        endTime = time.time() + bindTime
        Collector.currCollector.bindingSet(clientIP, serverIP, endTime)

    # initialization method
    def __init__(self):
        self.daemon = True
        self.links = {}
        self.data = {}
        self.bindings = {}
        self.activeThreads = {}
        self.udpThreads = {}
        self.sem = threading.Semaphore()
        self.semBinding = threading.Semaphore()
        self.semThreads = threading.Semaphore()
        self.semUDP = threading.Semaphore()
        self.interruptOnRebind = True
        Collector.currCollector = self

    # add new UDP thread to the list of "active" UDP connections
    def addUDPThread(self, addr, thread):
        self.semUDP.acquire()
        self.udpThreads[addr] = thread
        self.semUDP.release()

    # remove UDP thread from the list
    def removeUDPThread(self, addr):
        self.semUDP.acquire()
        try: self.udpThreads.pop(addr)
        except: pass
        self.semUDP.release()

    # retriefe UDP thread bound to the address addr
    def getUDPThread(self, addr):
        self.semUDP.acquire()
        try: thread = self.udpThreads[addr]
        except: thread = None
        self.semUDP.release()
        return thread

    # adds active threads to the list, so they can be terminated later when the connection is interrupted
    def addActiveThreads(self, clientIP, thread1, thread2):
        self.semThreads.acquire()
        if not clientIP in self.activeThreads:
            self.activeThreads[clientIP] = []
        self.activeThreads[clientIP].append(thread1)
        if thread2 != None:
            self.activeThreads[clientIP].append(thread2)
        self.semThreads.release()

    # removes only one thread, used by the thread itself on exiting
    def removeActiveThread(self, clientIP, thread):
        self.semThreads.acquire()
        if clientIP in self.activeThreads:
            self.activeThreads[clientIP].pop(self.activeThreads[clientIP].index(thread))
        self.semThreads.release()

    # breaks all TCP and UDP threads for clientIP
    def breakAllThreads(self, clientIP):
        self.semThreads.acquire()
        if clientIP in self.activeThreads:
            for thread in self.activeThreads[clientIP]:
                try: thread.outSockClnt.close()
                except: pass
                try: thread.inSockClnt.close()
                except: pass
        self.semThreads.release()

    #clean exit for all threads (the socket exception is handled by the thread)
    def shutdownAll(self):
        self.semThreads.acquire()
        for clientIP in self.activeThreads:
            for thread in self.activeThreads[clientIP]:
                try:
                    thread.outSockClnt.close()
                    thread.inSockClnt.close()
                except:
                    pass
            self.semThreads.release()

    # reverse table lookup, get the list of client IPs boud to a server IP
    def getBoundTo(self, serverIP):
        self.semBinding.acquire()
        retVal = []
        for clientIP in self.bindings:
            if self.bindings[clientIP][0] == serverIP:
                retVal.append = clientIP
        self.semBinding.release()
        return retVal

    # get string of all bindings
    def getBindings(self, displayEndTime=False):
        self.semBinding.acquire()
        if displayEndTime:
            retVal = str(self.bindings)
        else:
            retVal = {}
            for clientIP in self.bindings:
                retVal[clientIP] = self.bindings[clientIP][0]
            retVal = str(retVal)

        self.semBinding.release()
        return retVal

    # check for expired bindings and remove them
    def unbindExpired(self, currTime):
        expired = []
        self.semBinding.acquire()
        for clientIP in self.bindings:
            if self.bindings[clientIP][1] <= currTime:
                expired.append(clientIP)

        # remove separately for not removing in the FOR loop during which they are being read (might cause issues with dict)
        for clientIP in expired:
            self.bindings.pop(clientIP)

        self.semBinding.release()

        for clientIP in expired:
            self.breakAllThreads(clientIP)

    # return to which server IP is the client bound
    def bindingGet(self, IP):
        self.semBinding.acquire()
        try:
            retVal = self.bindings[IP][0]
        except KeyError:
            retVal = None
        self.semBinding.release()
        return retVal

    # set new binding - bind clientIP to serverIP until endTime
    def bindingSet(self, clientIP, serverIP, endTime):
        self.semBinding.acquire()
        if (clientIP in self.bindings) and self.interruptOnRebind:
            # break current connections after binding to different server
            if self.bindings[clientIP][0] != serverIP:
                self.breakAllThreads(clientIP)
        if serverIP in ["", " ", "none"]:
            self.bindings.pop(clientIP)
        else:
            self.bindings[clientIP] = [serverIP, endTime]
        self.semBinding.release()

    # get list of all dispatcher client links
    def getLinks(self):
        self.sem.acquire()
        retVal = {}
        for linkID in self.links:
            retVal[linkID] = self.links[linkID]
        self.sem.release()
        return retVal

    # return instance of dispatcher client link identified by linkID
    def getLink(self, linkID):
        self.sem.acquire()
        if linkID in self.links:
            retVal = self.links[linkID]
        else:
            retVal = None
        self.sem.release()
        return retVal

    # return data of dispatcher client link identified by linkID
    def getLinkData(self, linkID):
        self.sem.acquire()
        if linkID in self.links:
            retVal = self.data[linkID]
        else:
            retVal = None
        self.sem.release()
        
    # return data of dispatcher client link identified by linkID
    def isLinkUp(self, linkID):
        self.sem.acquire()
        retVal = linkID in self.links
        self.sem.release()
        return retVal

    # add new link as a dispatcher client connects
    def addLink(self, link):
        self.sem.acquire()
        link.collector = self
        self.links[link.linkID] = link
        self.data[link.linkID] = "{}"
        self.sem.release()

    # remove link after dispatcher client disconnects
    def removeLink(self, identifier):
        self.sem.acquire()
        if identifier in self.links:
            self.links.pop(identifier)
            self.data.pop(identifier)
        self.sem.release()

    # get data of all links
    def getData(self):
        self.sem.acquire()
        currData = {}
        for linkID in self.data:
            currData[linkID] = self.data[linkID]
        self.sem.release()
        return currData

    # set data for link identified by linkID
    def setData(self, linkID, data):
        self.sem.acquire()
        self.data[linkID] = data
        self.sem.release()

# main part of the dispatcher configuration and client protocols - this handles all the incomming requests
class DispatcherServer():
    def __init__(self, listenOnIp, listenOnPort, localOnly=True, interruptOnRebind=True):
        self.listenOnIP = listenOnIp
        self.listenOnPort = listenOnPort
        self.collector = Collector()
        self.collector.interruptOnRebind = interruptOnRebind
        self.localOnly = localOnly
        timer = Timer()
        timer.config()
        timer.start()

    def mainloop(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.listenOnIP, self.listenOnPort))
        self.sock.listen(1)

        while 1:
            clnt, (clnt_ip, clnt_no) = self.sock.accept()
            # do not report local connections (can be done from PHP+AJAX, which only causes too many messages to appear)
            if clnt_ip != "127.0.0.1":
                print "Connection accepted: ", clnt_ip
            try:
                # handshake
                clnt.send("HELLO")
                data = clnt.recv(128)
                if data == "TUNNEL_CLIENT":
                    clnt.send("ID_REQUEST")
                elif data == "APP_CLIENT":
                    # allow only local with configuration protocol connection if set
                    if self.localOnly and clnt_ip != '127.0.0.1':
                        clnt.send("NACK")
                        data = ""
                        logging.warning("Dispatcher control connection attempt from %s", clnt_ip)
                        print "Warning: dispatcher control connection attempt from", clnt_ip
                    else:
                        clnt.send("ACK")
                else:
                    clnt.send("NACK")
            except Exception as err:
                print err, "dispMainloop"
                data = None

            # handle dispatcher clients
            if data == "TUNNEL_CLIENT":
                try:
                    linkID = clnt.recv(1024)
                except:
                    linkID = None
                if self.collector.isLinkUp(linkID):
                    # if a link with this linkID already exists, connection is refused
                    clnt.send("ID_CONFLICT")
                    clnt.close()
                    print "! ID CONFLICT !", linkID
                elif linkID:
                    newLink = DispatcherLink()
                    newLink.config(linkID, clnt, clnt_ip)
                    newLink.start()
                    self.collector.addLink(newLink)
                else:
                    clnt.send("NACK")
                    clnt.close()

            # handle configuration clients
            elif data == "APP_CLIENT":
                newApp = DispatcherAppLink()
                newApp.config(clnt, clnt_ip)
                newApp.start()
            else:
                clnt.close()

        self.sock.close()
        print "SERVER STOPPED"


# hlavni trida serveru - pouziti: disp = Dispatcher() nebo disp = Dispatcher("0.0.0.0", 2105)
# main class of the server, launches tunnel threads and configuration and client-protocol servers
class Dispatcher():
    currDispatcher = None

    def __init__(self, listenOnIP="0.0.0.0", listenOnPort=2107, interruptOnRebind=True):
        self.tunnels = []
        self.server = DispatcherServer(listenOnIP, listenOnPort, interruptOnRebind)
        self.listenOnIP = listenOnIP
        self.listenOnPort = listenOnPort
        Dispatcher.currDispatcher = self

    # method for initialization of a new tunnel
    # usage example:
    #  connect to http server that run on port 80 on the servers, but this (dispatcher server) machine already uses it,
    #  you can map the destination port 80, but accept on 8080 on the server, so port 80 requests will communicate with server,
    #  but port 8080 will be redirected to the target servers with the web app running in their port 80 as well:
    #       disp.addTunnel(8080, 80)
    #  also, you can use a different interface to listen on and send through - 80 from (localhost) to 80 (through hostname):
    #       disp.addTunnel(80, 80, appListenIp="localhost", tunListenIp="hostname")
    def addTunnel(self, appListenPort, serverPort, appListenIP="0.0.0.0", udp=False):
        tun = Tunnel()
        tun.config(appListenIP, appListenPort, serverPort, udp)
        self.tunnels.append(tun)

    # shut down all tunnels
    def shutdownTunnels(self):
        for tun in self.tunnels:
            tun.shutdown()

    # shut down the whole server
    def serverShutdown(self, unused1=None, unused2=None):
        logging.info("Shutting down.")
        print "\nServer shutting down..."
        Collector.currCollector.shutdownAll()
        self.shutdownTunnels()
        exit()

    # start all the servers, this is the main method of this class
    def startServer(self):
        signal.signal(signal.SIGTERM, self.serverShutdown)
        logging.info("Starting up.")
        print "================================================================================"
        print "                             |  Dispatcher Server  |"
        print "                             -----------------------"
        print ""
        print " Author:     Matous Jezersky - xjezer01@stud.fit.vutbr.cz"
        print " Version:    " + SERVER_VERSION
        print ""
        print "--------------------------------------------------------------------------------"
        print ""
        print " Listening on:   " + self.listenOnIP + ":" + str(self.listenOnPort)
        print " Tunnels: "
        tunCount = 0
        for tun in self.tunnels:
            if tun.udp == True: protocol="(UDP)"
            else: protocol="(TCP)"
            print "  [" + str(tunCount) + "]  client:" + str(tun.appListenPort) + " -> server:" + str(tun.serverPort) + " \t" + protocol
            tunCount += 1
        print ""
        print "================================================================================"
        for tun in self.tunnels:
            tun.start()
        try:
            self.server.mainloop()
        except KeyboardInterrupt:
            self.serverShutdown()

