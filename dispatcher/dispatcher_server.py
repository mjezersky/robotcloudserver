#!/usr/bin/python

#reverse proxy server
SERVER_VERSION = "0.0.25"

# fwd ports: 2105-2106, 9090, 62100-62199
# default app server 2107 (bud bind na localhost nebo neforwardovat)

import socket, threading, time

BUFSIZE = 1024

class TunnelCommThread(threading.Thread):    
    def config(self, outSockClnt, inSockClnt):
        self.daemon = True
        self.outSockClnt = outSockClnt
        self.inSockClnt = inSockClnt
    def run(self):
        #print "tun comm linked"
        try:
            while 1:
                data = self.outSockClnt.recv(BUFSIZE) # prijmu data z tunelu
                if not data: break
                self.inSockClnt.send(data) # odeslu je do RMS
        except Exception as err:
            print err, "commThread"
            #print "tunnel disconnected, pls close client"
        self.outSockClnt.close()
        self.inSockClnt.close()
    

class Tunnel(threading.Thread):
    def config(self, appListenIP, appListenPort, serverPort):
        self.appListenIP = appListenIP
        self.appListenPort = appListenPort
        self.serverPort = serverPort
        self.serverIP = None #IP se ziska z bindingu
        self.daemon = True

    def interrupt(self):
        # preruseni tunelu (napr. pri prepnuti povoleneho tunelu behem aktivni komunikace)
        try: self.outSockClnt.close()
        except Exception as err: pass
        try: self.inSockClnt.close()
        except Exception as err: pass
        self.interrupted = True
    
    def run(self):
        #print "*Tunnel initialized*"
        #self.tunnelSem = threading.Semaphore()

        #socket pro pripojeni klienta
        self.inSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.inSock.bind((self.appListenIP, self.appListenPort))
        self.inSock.listen(1)

        self.inSockClnt = None
        
        self.tunSrv = None
        while 1: # pripojeni od RMS
            if True:
                self.interrupted = False
                #print "*RDY*", self.appListenPort

                #klient se pripoji (pres javascript)
                try:
                    self.inSockClnt, (clnt_ip, clnt_no) = self.inSock.accept()
                except Exception as err:
                    print "FATAL ERROR!!!", err
                    inSockClnt.close()
                    return

                self.serverIP = Collector.getBoundIP(clnt_ip)
                if self.serverIP != None:
                    try:
                        #print "*attempting to connect*"
                        #socket pro pripojeni na robota
                        outSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        outSock.connect((self.serverIP, self.serverPort))      
                        #print "*connected, starting comm threads*"
                        self.outThread = TunnelCommThread()
                        self.outThread.config(outSock, self.inSockClnt)
                        self.outThread.start()
                        self.inThread = TunnelCommThread()
                        self.inThread.config(self.inSockClnt, outSock)
                        self.inThread.start()
                    except Exception as err:
                        print "CONNERR:", err
                        self.inSockClnt.close()
                else: #serverIP None
                    print "*unbound connection attempt: "+clnt_ip+"*"
                    self.inSockClnt.close()
            else:
                time.sleep(1) 
        print "!!!!!!!!tunnel service stopped!!!!!!!!!"
        inSockClnt.close()



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
                dataArr.append("'"+str(i)+"' : "+dataDict[i])
            if dataArr == []:
                return "{}"
            dataStr = "{ 'bindings': " + Collector.currCollector.getBindings()
            dataStr += ", 'clients': { " + ", ".join(dataArr) + " } }"
            dataStr = dataStr.replace("'", '"') #json chce " misto '
            return dataStr
        elif data == "RESET":
            Collector.allowedTunnel = None
            return "ACK"
        elif data == "BINDINGS":
            return Collector.currCollector.getBindings()
        else:
            if len(data)>0:
                if data[0]=="A":
                    try:
                        linkID = data[1::]
                        link = Collector.currCollector.getLink(linkID)
                        print "allowing tunnel from", link.linkID
                        Collector.allowTunnel(link)
                        return "ACK"
                    except Exception as err:
                        print err
                        return "UNAVAILABLE"
                elif data[0]=="G":
                    try:
                        linkID = data[1::]
                        dataDict = Collector.currCollector.getData()
                        return dataDict[linkID]
                    except Exception as err:
                        print err
                        return "UNAVAILABLE"
                    
                elif data[0]=="B":
                    # "BclientIP#serverIP"
                    try:
                        content = data[1::]
                        ips = content.split("#")
                        Collector.bindIP(ips[0], ips[1])
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
            self.sock.send(str(len(resp))+"#")
            self.sock.send(resp)

        self.sock.close()

#kazde prichozi pripojeni na dispatcher bude mit svuj thread, s okolim
#bude komunikovat skrz kolektor dat s vylucnym pristupem
class DispatcherLink(threading.Thread):
    tunnelRequest = False ## prepsat statickou promennou a metodu!!!!
    def config(self, linkID, sock, clientIP):
        self.daemon = True
        self.collector = None
        self.linkID = linkID
        self.clientIP = clientIP
        self.sock = sock
        self.sem = threading.Semaphore() # deprec.
        self.semTunnel = threading.Semaphore() # a na zadost o tunel
        self.semSock = threading.Semaphore() # a na odesilani pres socket (kvuli zadosti o tunel)

    def requestTunnel(self, tunnelPort):
        self.sendSafe("DISPATCHER_TUNNEL_REQUEST#"+str(tunnelPort))

    def requestApp(self, tunnelPort):
        try:
            self.sendSafe("DISPATCHER_APP_REQUEST#"+str(tunnelPort))
            return True
        except:
            return False
        
    def run(self):
        try:
            self.mainloop()
        except Exception as err:
            print err
        self.sock.close()
        if self.collector != None:
            self.collector.removeLink(self.linkID)
        print "link closed"

    def mainloop(self):
        print "new link", self.linkID
        while 1:
            self.sendSafe("DISPATCHER_DATA_REQUEST", requireAck=False)
            data = self.sock.recv(1024)
            if data == "" or data == None:
                break

            dataWrapped = "{ 'ip':'"+str(self.clientIP)+"', 'data':"+data+" }"            
            Collector.currCollector.setData(self.linkID, dataWrapped)
            time.sleep(1)

    # odeslani dat pres self.sock se semaforem a cekam na ack
    def sendSafe(self, data, requireAck=True):
        self.semSock.acquire()
        try:
            self.sock.send(data)
            if requireAck:
                #print "reqack"
                self.sock.settimeout(2)
                if self.sock.recv(8) != "ACK": raise Exception("sendSafe_NACK")
                self.sock.settimeout(None)
                #print "gotack"
        except Exception as err:
            if requireAck: print "reqackFAIL"
            self.semSock.release()
            raise err
        self.semSock.release()

    def getData(self): # deprec.
        self.sem.acquire()
        data = self.data
        self.sem.release()
        return data

    def setData(self, data): # deprec.
        self.sem.acquire()
        self.data = "{ 'ip':'"+str(self.clientIP)+"', 'data':"+data+" }"
        self.sem.release()
        

# datovy kolektor - sbira info z pripojenych dispatcher clientu
class Collector():
    currCollector = None
    allowedTunnel = None
    semAllowedTunnel = threading.Semaphore()

    # pokud je k dispozici tunel, pozadam o nej, jinak cekam, az nejaky k dispozici bude
    # nemoznost pripojit se k tunelu zpusobi cekani
    @staticmethod
    def requestAllowedTunnel(tunnelPort):
        try:
            Collector.allowedTunnel.requestTunnel(tunnelPort)
            return True
        except:
            return False

    @staticmethod
    def allowTunnel(link):
        # pokud povoluji jiny link, nez je prave aktivni, prerusim tunely
        # pokdu nebyl aktivni zadny, nic neprerusuju
        if link != Collector.allowedTunnel and Collector.allowedTunnel != None:
            Dispatcher.currDispatcher.interruptTunnels()
        Collector.allowedTunnel = link

    @staticmethod
    def isAllowedTunnelUp():
        try:
            return Collector.currCollector.isLinkUp(Collector.allowedTunnel.linkID)
        except Exception as err:
            return False

    @staticmethod
    def getBoundIP(IP):
        return Collector.currCollector.bindingGet(IP)

    @staticmethod
    def bindIP(clientIP, serverIP):
        Collector.currCollector.bindingSet(clientIP, serverIP)

    #inicializacni metoda
    def __init__(self):
        self.daemon = True
        self.links = {}
        self.data = {}
        self.bindings = {}
        self.sem = threading.Semaphore()
        self.semBinding = threading.Semaphore()
        Collector.currCollector = self

    def getBindings(self):
        self.semBinding.acquire()
        retVal = str(self.bindings)
        self.semBinding.release()
        return retVal

    def bindingGet(self, IP):
        self.semBinding.acquire()
        try:
            retVal = self.bindings[IP]
        except KeyError:
            retVal = None
        self.semBinding.release()
        return retVal
        

    def bindingSet(self, clientIP, serverIP):
        self.semBinding.acquire()
        self.bindings[clientIP]=serverIP
        self.semBinding.release()

    def getLinks(self):
        self.sem.acquire()
        retVal = {}
        for linkID in self.links:
            retVal[linkID]=self.links[linkID]
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
        #pokud se jedna o "reconnect" driv povoleneho linku, updatuju allowedTunnel
        if Collector.allowedTunnel != None:
            if Collector.allowedTunnel.linkID == link.linkID:
                Collector.allowedTunnel = link
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
    def __init__(self, listenOnIp, listenOnPort):
        self.listenOnIP = listenOnIp
        self.listenOnPort = listenOnPort
        self.collector = Collector()
        
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
                    clnt.send("ACK")
                else:
                    clnt.send("NACK")
            except Exception as err:
                print err, "dispMainloop"
                data = None
            if data == "TUNNEL_CLIENT":
                try: linkID = clnt.recv(1024)
                except: linkID = None
                if self.collector.isLinkUp(linkID):
                    #pokud existuje link se stejnym id, nedovolim spojeni
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
    def __init__(self, listenOnIp="0.0.0.0", listenOnPort=2107):
        self.tunnels = []
        self.server = DispatcherServer(listenOnIp, listenOnPort)
        self.listenOnIp = listenOnIp
        self.listenOnPort = listenOnPort
        Dispatcher.currDispatcher = self

    # metoda pro inicializaci noveho tunelu
    # pr. pouziti:
    # tunelovani portu 80 pres port 2106:
    #       disp.addTunnel(80, 2106)
    # tunelovani portu 80 (localhost) pres port 80 (tunnel.hostname.cz):
    #       disp.addTunnel(80, 80, appListenIp="localhost", tunListenIp="tunnel.hostname.cz")
    def addTunnel(self, appListenPort, serverPort, appListenIp="0.0.0.0"):
        tun = Tunnel()
        tun.config(appListenIp, appListenPort, serverPort)
        self.tunnels.append(tun)

    def interruptTunnels(self):
        print "!!!!! BREAKING TUNNELS"
        for tun in self.tunnels:
            tun.interrupt()

    def startServer(self):
        print "================================================================================"
        print "                             |ROS Dispatcher Server|"
        print "                             -----------------------"
        print ""
        print " Author:     Matous Jezersky - xjezer01@stud.fit.vutbr.cz"
        print " Version:    "+SERVER_VERSION
        print ""
        print "--------------------------------------------------------------------------------"
        print ""
        print " Listening on:   "+self.listenOnIp+":"+str(self.listenOnPort)
        print " Tunnels: "
        tunCount = 0
        for tun in self.tunnels:
            print "  ["+str(tunCount)+"]  client:"+str(tun.appListenPort)+" -> server:"+str(tun.serverPort)
            tunCount += 1
        print ""
        print "================================================================================"
        for tun in self.tunnels:
            tun.start()
        self.server.mainloop()

    

disp = Dispatcher(listenOnPort=2107)
disp.addTunnel(9090, 9090)
#disp.addTunnel(2110, 2111)
disp.startServer()



