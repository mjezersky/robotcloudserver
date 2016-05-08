#!/usr/bin/python

## --------------------------------------------------------------
## Dispatcher server
## Author: Matous Jezersky - xjezer01@stud.fit.vutbr.cz
## All rights reserved
## --------------------------------------------------------------

SERVER_VERSION = "1.0.1"

import socket
import threading
import time
import logging
import signal

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d.%m.%Y %H:%M:%S', filename='dispatcher_server.log',level=logging.DEBUG)

BUFSIZE = 1024 # socket buffer size


class TunnelCommThread(threading.Thread):
    def config(self, outSockClnt, inSockClnt, clientIP):
        self.daemon = True
        self.outSockClnt = outSockClnt
        self.inSockClnt = inSockClnt
        self.clientIP = clientIP

    def run(self):
        # print "tun comm linked"
        try:
            while 1:
                data = self.outSockClnt.recv(BUFSIZE)  # prijmu data z tunelu
                if not data: break
                self.inSockClnt.send(data)  # odeslu je do RMS
        except Exception as err:
            print err, "commThread"
            logging.warning("TunnelCommThread - %s", str(err))
        try:
            self.outSockClnt.close()
            self.inSockClnt.close()
        except:
            pass
        Collector.currCollector.removeActiveThread(self.clientIP, self)

class TunnelUDPThread(threading.Thread):
    def config(self, inSockClnt, outSockClnt, port):
        self.daemon = True
        self.inSockClnt = inSockClnt
        self.outSockClnt = outSockClnt
        self.port = port

    def run(self):
        while 1:
            try:
                data, addr = self.outSockClnt.recvfrom(BUFSIZE)  # prijmu data z tunelu
                if not data: break
                #send data to all bound IPs
                for bound_addr in Collector.currCollector.getBoundTo(addr):
                    self.inSockClnt.sendto(data, (bound_addr, self.port))
            except Exception as err:
                logging.warning("TunnelUDPThread - %s", str(err))
                print err, "udpThread"


class Tunnel(threading.Thread):
    def config(self, appListenIP, appListenPort, serverPort, udp=False, udpTunnelIP=None):
        self.appListenIP = appListenIP
        self.appListenPort = appListenPort
        self.serverPort = serverPort
        self.udp = udp
        self.udpTunnelIP = udpTunnelIP
        self.serverIP = None  # IP se ziska z bindingu
        self.daemon = True

    def interrupt(self):  # deprec?
        # preruseni tunelu (napr. pri prepnuti povoleneho tunelu behem aktivni komunikace)
        try:
            self.inSockClnt.close()
        except Exception as err:
            pass
        self.interrupted = True

    def shutdown(self):
        # shut down ingoring any errors
        try: self.inSock.close()
        except: pass
        try: self.outSock.close()
        except: pass

    def run(self):
        # print "*Tunnel initialized*"
        # self.tunnelSem = threading.Semaphore()

        ## UDP TUNNEL
        if self.udp:

            if self.udpTunnelIP == None:
                print "ERROR: UDP Tunnel Server IP must be set"
                return
            
            self.inSockClnt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.inSockClnt.bind((self.appListenIP, self.appListenPort))

            self.outSockClnt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.outSockClnt.bind((self.udpTunnelIP, self.serverPort))

            udpThread = TunnelUDPThread()
            udpThread.config(self.inSockClnt, self.outSockClnt, self.serverPort)
            udpThread.start()
            
            while 1:
                data, addr = self.inSockClnt.recvfrom(1024)
                serverIP = Collector.getBoundIP(clnt_ip)
                if serverIP != None:
                    self.outSockClnt.sendto(data, (serverIP, self.serverPort))

        ## TCP TUNNEL 
        else:
            self.inSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.inSock.bind((self.appListenIP, self.appListenPort))
            self.inSock.listen(1)

            self.inSockClnt = None
            
            while 1:
                self.interrupted = False
                # print "*RDY*", self.appListenPort

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
                        # print "*attempting to connect*"
                        # socket pro pripojeni na robota
                        self.outSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.outSock.connect((self.serverIP, self.serverPort))
                        # print "*connected, starting comm threads*"
                        self.outThread = TunnelCommThread()
                        self.outThread.config(self.outSock, self.inSockClnt, clnt_ip)
                        self.outThread.start()
                        self.inThread = TunnelCommThread()
                        self.inThread.config(self.inSockClnt, self.outSock, clnt_ip)
                        self.inThread.start()
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


class Timer(threading.Thread):
    def config(self):
        self.daemon = True

    def run(self):
        while 1:
            Collector.currCollector.unbindExpired(time.time())
            time.sleep(2) # period for checking for bind expiration


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

    def handleData(self, data):
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
        elif data == "BINDINGS":
            return Collector.currCollector.getBindings()
        else:
            if len(data) > 0:
                if data[0] == "G": # deprec?
                    try:
                        linkID = data[1::]
                        dataDict = Collector.currCollector.getData()
                        return dataDict[linkID]
                    except Exception as err:
                        print err
                        return "UNAVAILABLE"

                elif data[0] == "B":
                    # "BclientIP#serverIP#lease_sec"
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


# kazde prichozi pripojeni na dispatcher bude mit svuj thread, s okolim
# bude komunikovat skrz kolektor dat s vylucnym pristupem
class DispatcherLink(threading.Thread):
    tunnelRequest = False  ## prepsat statickou promennou a metodu!!!!

    def config(self, linkID, sock, clientIP):
        self.daemon = True
        self.collector = None
        self.linkID = linkID
        self.clientIP = clientIP
        self.sock = sock
        self.sem = threading.Semaphore()  # deprec.
        self.semTunnel = threading.Semaphore()  # a na zadost o tunel
        self.semSock = threading.Semaphore()  # a na odesilani pres socket (kvuli zadosti o tunel)

    def requestApp(self, tunnelPort):  # deprec.
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

    def measureRTT(self):
        self.sendSafe("ECHO", requireAck=False)
        t0 = time.time()
        data = self.sock.recv(16)
        t1 = time.time()
        if data == "ECHO":
            return str(int((t1 - t0) * 1000))  # RTT v ms
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

    def getData(self):  # deprec.
        self.sem.acquire()
        data = self.data
        self.sem.release()
        return data

    def setData(self, data):  # deprec.
        self.sem.acquire()
        self.data = "{ 'ip':'" + str(self.clientIP) + "', 'data':" + data + " }"
        self.sem.release()


# datovy kolektor - sbira info z pripojenych dispatcher clientu
class Collector():
    currCollector = None
    
    @staticmethod
    def getBoundIP(IP):
        return Collector.currCollector.bindingGet(IP)

    @staticmethod
    def bindIP(clientIP, serverIP, leaseTime):
        endTime = time.time() + leaseTime
        Collector.currCollector.bindingSet(clientIP, serverIP, endTime)

    # inicializacni metoda
    def __init__(self):
        self.daemon = True
        self.links = {}
        self.data = {}
        self.bindings = {}
        self.activeThreads = {}
        self.sem = threading.Semaphore()
        self.semBinding = threading.Semaphore()
        self.semThreads = threading.Semaphore()
        self.interruptOnRebind = True
        Collector.currCollector = self

    def addActiveThreads(self, clientIP, thread1, thread2):
        self.semThreads.acquire()
        if not clientIP in self.activeThreads:
            self.activeThreads[clientIP] = []
        self.activeThreads[clientIP].append(thread1)
        self.activeThreads[clientIP].append(thread2)
        self.semThreads.release()

    # removes only one thread, used by the thread itself on exiting
    def removeActiveThread(self, clientIP, thread):
        self.semThreads.acquire()
        if clientIP in self.activeThreads:
            self.activeThreads[clientIP].pop(self.activeThreads[clientIP].index(thread))
        self.semThreads.release()

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

    def getBoundTo(self, serverIP):
        self.semBinding.acquire()
        retVal = []
        for clientIP in self.bindings:
            if self.bindings[clientIP][0] == serverIP:
                retVal.append = clientIP
        self.semBinding.release()
        return retVal

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

    def unbindExpired(self, currTime):
        expired = []
        self.semBinding.acquire()
        for clientIP in self.bindings:
            if self.bindings[clientIP][1] <= currTime:
                expired.append(clientIP)

        # zvlast odstraneni abych neodstranoval ve foru behem ktereho ctu
        for clientIP in expired:
            self.bindings.pop(clientIP)

        self.semBinding.release()

        for clientIP in expired:
            self.breakAllThreads(clientIP)

    def bindingGet(self, IP):
        self.semBinding.acquire()
        try:
            retVal = self.bindings[IP][0]
        except KeyError:
            retVal = None
        self.semBinding.release()
        return retVal

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

    def getLinks(self):
        self.sem.acquire()
        retVal = {}
        for linkID in self.links:
            retVal[linkID] = self.links[linkID]
        self.sem.release()
        return retVal

    def getLink(self, linkID):
        self.sem.acquire()
        if linkID in self.links:
            retVal = self.links[linkID]
        else:
            retVal = None
        self.sem.release()
        return retVal

    def getLinkData(self, linkID):
        self.sem.acquire()
        if linkID in self.links:
            retVal = self.data[linkID]
        else:
            retVal = None
        self.sem.release()

    def isLinkUp(self, linkID):
        self.sem.acquire()
        retVal = linkID in self.links
        self.sem.release()
        return retVal

    def addLink(self, link):
        self.sem.acquire()
        link.collector = self
        self.links[link.linkID] = link
        self.data[link.linkID] = "{}"
        self.sem.release()

    def removeLink(self, identifier):
        self.sem.acquire()
        if identifier in self.links:
            self.links.pop(identifier)
            self.data.pop(identifier)
        self.sem.release()

    def getData(self):
        self.sem.acquire()
        currData = {}
        for linkID in self.data:
            currData[linkID] = self.data[linkID]
        self.sem.release()
        return currData

    def setData(self, linkID, data):
        self.sem.acquire()
        self.data[linkID] = data
        self.sem.release()


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
            if clnt_ip != "127.0.0.1":
                print "Connection accepted: ", clnt_ip
            try:
                clnt.send("HELLO")
                data = clnt.recv(128)
                if data == "TUNNEL_CLIENT":
                    clnt.send("ID_REQUEST")
                elif data == "APP_CLIENT":
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
            if data == "TUNNEL_CLIENT":
                try:
                    linkID = clnt.recv(1024)
                except:
                    linkID = None
                if self.collector.isLinkUp(linkID):
                    # pokud existuje link se stejnym id, nedovolim spojeni
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
            elif data == "APP_CLIENT":
                newApp = DispatcherAppLink()
                newApp.config(clnt, clnt_ip)
                newApp.start()
            else:
                clnt.close()

        self.sock.close()
        print "SERVER STOPPED"


# hlavni trida serveru - pouziti: disp = Dispatcher() nebo disp = Dispatcher("0.0.0.0", 2105)
class Dispatcher():
    currDispatcher = None

    def __init__(self, listenOnIP="0.0.0.0", listenOnPort=2107, interruptOnRebind=True):
        self.tunnels = []
        self.server = DispatcherServer(listenOnIP, listenOnPort, interruptOnRebind)
        self.listenOnIP = listenOnIP
        self.listenOnPort = listenOnPort
        Dispatcher.currDispatcher = self

    # metoda pro inicializaci noveho tunelu
    # pr. pouziti:
    # tunelovani portu 80 pres port 2106:
    #       disp.addTunnel(80, 2106)
    # tunelovani portu 80 (localhost) pres port 80 (tunnel.hostname.cz):
    #       disp.addTunnel(80, 80, appListenIp="localhost", tunListenIp="tunnel.hostname.cz")
    def addTunnel(self, appListenPort, serverPort, appListenIP="0.0.0.0", udp=False, udpTunnelIP=None):
        tun = Tunnel()
        tun.config(appListenIP, appListenPort, serverPort, udp, udpTunnelIP)
        self.tunnels.append(tun)

    def shutdownTunnels(self):
        for tun in self.tunnels:
            tun.shutdown()

    def serverShutdown(self, unused1=None, unused2=None):
        logging.info("Shutting down.")
        print "\nServer shutting down..."
        Collector.currCollector.shutdownAll()
        self.shutdownTunnels()
        exit()

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

