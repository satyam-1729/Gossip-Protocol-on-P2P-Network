import socket
import sys
import random
import hashlib
import threading
from _thread import *
import tqdm
from time import sleep,time

serverStarted=False
connectedPeers=[]
connectedPeersDict={}
messageList={}
messageFrom={}
livenessTracker=[]
deadCounter={}
connected_seeds=[]
def writeToFileAndPrint(host,port,data):
    print(data)
    with open("outputfile.txt","a+") as f:
        f.write("Peer: "+host+":"+str(port)+" says --> "+data+"\n")
def readAllSeeds():
    seeds=[]
    with open("config.txt","r") as f:
        data=f.read()
        seeds+=list(set(data.split("\n")[:-1]))
        if "" in seeds:
            seeds.remove("")
    return seeds
def broadcast(msg):
    global messageFrom
    key=msg
    msg=msg+"\n"
    for peer in connectedPeers:
        if messageFrom[key] != peer:
            try:
                peer.send(msg.encode())
            except:
                pass
def handleDeadNode(peer,host,port):
    try:
        connectedPeers.remove(connectedPeersDict[peer])
    except:
        pass
    for seed in connected_seeds:
        seed.send(("Dead Node:"+peer+":"+str(time())+":"+str(host)).encode())
    try:
        del connectedPeersDict[peer]
        del deadCounter[peer]
    except:
        pass

def handleUnreplied(host,port):
    global livenessTracker
    global connectedPeersDict
    global deadCounter
    tempDict= list(connectedPeersDict.keys())
    for peer in tempDict:
        if peer in livenessTracker:
            deadCounter[peer]=0
        else:
            try:
                deadCounter[peer]+=1
            except:
                deadCounter[peer]=1
        if(deadCounter[peer]>=3):
            handleDeadNode(peer,host,port)
    print(deadCounter)
    
def livenessCheck(host,port):
    global connectedPeers
    global livenessTracker
    sleep(15)
    while True:
        
        for peer in connectedPeers:
            try:
                peer.send(("Liveness Request:"+str(time())+":"+host+":"+str(port)+"\n").encode())
            except:
                pass
        sleep(13)
        print(livenessTracker)
        print(connectedPeersDict.keys())
        handleUnreplied(host,port)
        livenessTracker=[]
def peerListener(host,port):
        global serverStarted 
        global connectedPeers
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            s.bind((host,port))
        except:
            print("port is already in use")
            exit()
        writeToFileAndPrint(host,port,"Binded to "+str(port))
        s.listen(10)
        serverStarted=True
        while True:
            c,addr=s.accept()
            connectedPeers.append(c)
        s.close()
def sendMessages(peerID,host,port):
    global connectedPeers
    i=0
    while i<10:
        sleep(5)
        if len(connectedPeers)>0:
            i+=1
            messageGen=str(time())+":"+host+":"+str(port)+":msg#"+str(i)+"\n"
            for peer in connectedPeers:
                try:
                    peer.send(messageGen.encode())
                except:
                    pass
def recieveMessages(host,port):
    global connectedPeers
    global livenessTracker
    global messageFrom
    while True:
        for peer in connectedPeers:
            peer.settimeout(5)
            data=""
            try:
                data=peer.recv(2048).decode()
            except:
                pass
            peer.settimeout(None)
            if data and data!="":
                data=data.split("\n")[:-1]
                for d in data:
                    if "MyAddress" in d:
                        address=d.split("_")
                        connectedPeersDict[address[1]]=peer
                        print("inserted "+address[1]+" from recieving")
                    elif "Liveness" in d:
                        print(d)
                        if "Liveness Request" in d:
                            d=d.split(":")
                            try:
                                peer.send(("Liveness Reply:"+d[1]+":"+d[2]+":"+d[3]+":"+host+":"+str(port)+"\n").encode())
                            except:
                                pass
                        else:
                            d=d.split(":")
                            livenessTracker.append(d[4]+":"+d[5])
                        d=""
                        continue
                    elif d not in messageList.keys():
                        messageFrom[d]=peer
                        broadcast(d)
                        messageList[d]=True
                        writeToFileAndPrint(host,port,d)
                    else:
                        pass
                        #print("already got this message")
                data=""

def Main():
    global connectedPeers
    global connected_seeds
    host= sys.argv[1]
    port=int(sys.argv[2])

    start_new_thread(peerListener,(host,port,))
    peer_address=host+":"+str(port)
    peerID=str(hashlib.md5(peer_address.encode()).hexdigest())
    sleep(5)
    if not serverStarted:
        print("It took more time to bind the port or port is already is use")
        exit()
    seeds=readAllSeeds()
    available_peers=[]
    seeds=random.sample(seeds,int(len(seeds)/2)+1)
    #print(seeds)
    for seed in tqdm.tqdm(seeds):

        writeToFileAndPrint(host,port,"Connectiong to "+seed)
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        seed_host=seed.split(":")[0]
        seed_port=int(seed.split(":")[1])
        try:
            s.settimeout(10)
            s.connect((seed_host,seed_port))
            s.settimeout(None)
            connected_seeds.append(s)
            writeToFileAndPrint(host,port,"Connected to "+seed)

        except:
            writeToFileAndPrint(host,port,"Could not connect to "+seed)

    if len(connected_seeds)==0:
        writeToFileAndPrint(host,port,"No any seed server is online.")

        exit()
    for s in connected_seeds:
        data=s.recv(1024)
        print(data.decode())
        s.send(peerID.encode())
        s.recv(128)
        s.send(peer_address.encode())
        data=s.recv(2048).decode()
        if data!="first peer":
            available_peers+=data.split("\n")[:-1]
    available_peers=list(set(available_peers))
    if(len(available_peers)>4):
        available_peers = random.sample(available_peers,4)
    print(available_peers)
    for peer in available_peers:
        peer_host=peer.split(":")[0]
        peer_port=int(peer.split(":")[1])
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((peer_host,peer_port))
            s.settimeout(None)
            s.send(("MyAddress_"+host+":"+str(port)+"\n").encode())
            writeToFileAndPrint(host,port,"Connected to peer "+peer_host+":"+str(peer_port))
            connectedPeersDict[peer_host+":"+str(peer_port)]=s
            print("inserted "+peer_host+":"+str(peer_port)+"from main")
            connectedPeers.append(s)
        except:
            print("Peer seems to be dead")
            handleDeadNode(peer,host,port)
    start_new_thread(recieveMessages,(host,port,))
    start_new_thread(sendMessages,(peerID,host,port,))
    start_new_thread(livenessCheck,(host,port,))
    while True:
        pass 
Main() 