import socket

try:

    data = "testdata"#raw_input("data=")

    print "mini debug app protocol type 'X' to exit"
    
    

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
        if "X" in data: exit()
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
