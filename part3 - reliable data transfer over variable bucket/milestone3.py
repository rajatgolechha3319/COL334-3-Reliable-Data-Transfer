import socket
import threading
import time
import random
import sys
import os
import hashlib


serverAddressPort = ("10.17.6.5", 9802)
bufferSize = 4096
md5_hash = hashlib.md5()
time_out = 0.05
datadict = {}
num_packets = 0
reqs = []
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.settimeout(time_out)
reset_command = b"SendSize\nReset\n\n"
while True:
    try:
        UDPClientSocket.sendto(reset_command,serverAddressPort)
        msgFromServer = UDPClientSocket.recvfrom(bufferSize)
        msg = msgFromServer[0]
        break
    except socket.timeout:
        continue
# decode the message here
msg = msg.decode("utf-8")
msg.rstrip()
msg = msg[5::]
msg.lstrip()
bytes_to_rcv = int(msg)
rtt = 0.01
if bytes_to_rcv % 1448 == 0:
    num_packets = bytes_to_rcv // 1448
    for i in range(num_packets):
        req_msg = [1448*i, 1448]
        reqs.append(req_msg)
else:
    num_packets = bytes_to_rcv // 1448 + 1
    for i in range(num_packets - 1):
        req_msg = [1448*i, 1448]
        reqs.append(req_msg)
    req_msg = [1448*(num_packets - 1), bytes_to_rcv - 1448*(num_packets - 1)]
    reqs.append(req_msg)
# now we have the reqs to send in reqs
# now we need to start sending the messages but before that we need an estimate of RTT
# we will send 60 packets and then take the median of the RTTs
rtt_l = []
for i in range(30):
    s = time.time()
    if(len(reqs) == 0):
        break
    x = i % len(reqs)
    req_msg = "Offset: "+str(reqs[x][0])+"\n"+"NumBytes: "+str(reqs[x][1])+"\n\n"
    UDPClientSocket.sendto(req_msg.encode(),serverAddressPort)
    try:
        msgFromServer = UDPClientSocket.recvfrom(bufferSize)
        msg = msgFromServer[0]
        e = time.time()
        msg = msg.decode("utf-8")
        x = msg.find('Offset')
        y = msg.find('NumBytes')
        offset = int(msg[x+8:y-1])
        m1 = msg[y+9::]
        z = m1.find('\n')
        num_bytes = int(m1[0:z])
        m2 = m1[z+2:z+2+num_bytes]
        datadict[offset] = m2
        element = [offset, num_bytes]
        if element in reqs:
            reqs.remove(element)
        rtt_l.append(e-s)
        time.sleep(0.015)
    except socket.timeout:
        continue
rtt_l.sort()
x = len(rtt_l)
mid = x//2
rtt = (rtt_l[mid] + rtt_l[~mid])/2
if rtt < 0.004:
    rtt = 0.004
print("RTT is :",rtt)
UDPClientSocket.settimeout(rtt*2.5)
# now we have the RTT and the reqs to send, so let's start sending the messages using AIMD
burst_size = 5
i = 0
while(len(reqs) > 0):
    if(len(reqs) <= burst_size):
        burst_size = len(reqs)
    print("Burst size is %d" % burst_size)
    print(len(reqs))
    sendtime = time.time()
    for j in range(burst_size):
        x = i % len(reqs)
        i = i + 1
        req_msg = "Offset: "+str(reqs[x][0])+"\n"+"NumBytes: "+str(reqs[x][1])+"\n\n"
        UDPClientSocket.sendto(req_msg.encode(),serverAddressPort)
    resp = 0
    squished = False
    L = []
    rtt_cal = False
    for j in range(burst_size+1):
        try:
            msg = UDPClientSocket.recvfrom(bufferSize)
            msg = msg[0]
            msg = msg.decode("utf-8")
            x = msg.find('Offset')
            y = msg.find('NumBytes')
            offset = int(msg[x+8:y-1])
            m1 = msg[y+9::]
            z = m1.find('\n')
            num_bytes = int(m1[0:z])
            if (m1[z+1:z+10]=='Squished\n'):
                squished = True
                print("S    Q     U     I     S     H     E     D")
                m1 = m1[0:z+1] + m1[z+10:]
            m2 = m1[z+2:z+2+num_bytes]
            datadict[offset] = m2
            element = [offset, num_bytes]
            if element in reqs:
                reqs.remove(element)
            resp = resp + 1
            if(rtt_cal == False):
                recv_time = time.time()
                rtt_1 = recv_time - sendtime
                if(rtt_1 < 0.004):
                    pass
                else:
                    L.append(rtt_1)
        except socket.timeout:
            rtt_cal = True
            continue
    if(len(L) > 0):
        L.sort()
        x = len(L)
        mid = x//2
        rtt_ = (L[mid] + L[~mid])/2
        rtt = 0.7*rtt + 0.3*rtt_
        if(rtt < 0.004):
            rtt = 0.004
        if(rtt > 0.01):
            rtt = 0.01
        print("RTT is :",rtt)
        UDPClientSocket.settimeout(rtt*2.5)
    time.sleep((burst_size+2)*rtt*0.5)
    print(resp,burst_size)
    if (resp >= burst_size and squished == False):
        burst_size = burst_size + 1
    else:
        burst_size = (burst_size + 3) // 2 
submit = ""
for i in range(num_packets):
    submit += datadict[1448*i]

md5_hash = hashlib.md5(submit.encode('utf-8'))
md5_hex = md5_hash.hexdigest()
print(md5_hex)
submit_cmd = "Submit: Doof\n" + "MD5: " + md5_hex + "\n\n"
while True:
    try:
        UDPClientSocket.sendto(submit_cmd.encode(), serverAddressPort)
        msg = UDPClientSocket.recvfrom(bufferSize)
        msg = msg[0].decode()
        if(msg[0:6]=='Result'):
            break
    except socket.timeout:
        continue
print(msg)
UDPClientSocket.close()
