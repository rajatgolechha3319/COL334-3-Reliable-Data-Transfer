import socket
import threading
import time
import random
import sys
import os
import hashlib

serverAddressPort = ("10.17.6.5", 9801)
bufferSize = 4096
md5_hash = hashlib.md5()
# rate = 200
time_out = 0.1
# submit = False
datadict = {}
reqs_recv = []
num_packets = 0
datadict_lock = threading.Lock()
reqs_lock = threading.Lock()
rate_lock = threading.Lock()
recv_lock = threading.Lock()
reqs = []
M = []
burst_size = 8
# upper_bound = 400

def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3

def recieving_thread(client,rtt):
    global time_out
    global datadict
    # global submit
    global reqs
    global rate
    all_data = ""
    client.settimeout(4*rtt)
    while True:
        with reqs_lock:
            # print(len(reqs))
            if len(reqs) == 0:
                break
        try:
            recv = client.recvfrom(bufferSize)
            recv = recv[0].decode()
            all_data += recv
            while all_data.count('Offset')>0:
                x = all_data.find('Offset')
                y = all_data.find('NumBytes')
                offset = int(all_data[x+8:y-1])
                m1 = all_data[y+9::]
                z = m1.find('\n')
                num_bytes = int(m1[0:z])
                if (m1[z+1:z+10]=='Squished\n'):
                    print("Sqqqquiiiiissssshhheeeeddd")
                    m1 = m1[0:z+1] + m1[z+10:]
                if(z+2+num_bytes > len(m1)):
                    break
                m2 = m1[z+2:z+2+num_bytes]
                with recv_lock:
                    reqs_recv.append(offset)
                with datadict_lock:
                    datadict[offset] = m2
                    all_data = m1[z+2+num_bytes::]
                element = [offset, num_bytes]
                with reqs_lock:
                    if element in reqs:
                        reqs.remove(element)
            
        except socket.timeout:
            continue

def sending_thread(client,rtt,default):
    global time_out
    global datadict
    global reqs
    global upper_bound
    global rate
    # global submit
    global reqs_recv
    global num_packets
    global burst_size
    # uppb = 1000
    i = 0
    while True:
        reqs_sent = []
        with recv_lock:
            reqs_recv = []
        for j in range(burst_size):
            with reqs_lock:
                if len(reqs) == 0:
                    break
            with reqs_lock:
                x = i % len(reqs)
                i = i + 1
                req_msg = "Offset: "+str(reqs[x][0])+"\n"+"NumBytes: "+str(reqs[x][1])+"\n\n"
                reqs_sent.append(reqs[x][0])
            client.sendto(req_msg.encode(),serverAddressPort)
            y = 0.1/burst_size
            time.sleep(y*0.35)
        time.sleep(burst_size*rtt*0.2)
        
        with recv_lock:
            L3 = intersection(reqs_sent, reqs_recv)
            x = len(L3)
            if(x >= burst_size * 0.9):
                burst_size = burst_size + 1
            elif(x >= 0.8*burst_size):
                burst_size = burst_size
            # elif(x>=0.6*burst_size):
            #     burst_size = max(1,burst_size -2 )
            else:
                burst_size = (burst_size+3) // 2
                    
                
        print("burst_size is :",burst_size)
        with reqs_lock:
                if len(reqs) == 0:
                    break
        
    

def main():
    global burst_size
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocket.settimeout(time_out)
    alpha = b"SendSize\nReset\n\n"
    UDPClientSocket.sendto(alpha, serverAddressPort)
    while True:
        try:
            UDPClientSocket.sendto(alpha, serverAddressPort)
            msgFromServer = UDPClientSocket.recvfrom(bufferSize)
            msg = msgFromServer[0]
            print(msg)
            break
        except socket.timeout:
            continue
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
    rtt_l = []
    for i in range(60):
        s = time.time()
        if(len(reqs) == 0):
            break
        x = i % len(reqs)
        req_msg = "Offset: "+str(reqs[x][0])+"\n"+"NumBytes: "+str(reqs[x][1])+"\n\n"
        UDPClientSocket.sendto(req_msg.encode(),serverAddressPort)
        try:
            msgFromServer = UDPClientSocket.recvfrom(bufferSize)
            msg = msgFromServer[0]
            msg = msg.decode("utf-8")
            x = msg.find('Offset')
            y = msg.find('NumBytes')
            offset = int(msg[x+8:y-1])
            m1 = msg[y+9::]
            z = m1.find('\n')
            num_bytes = int(m1[0:z])
            if (m1[z+1:z+10]=='Squished\n'):
                m1 = m1[0:z+1] + m1[z+10:]
            if(z+2+num_bytes > len(m1)):
                continue
            m2 = m1[z+2:z+2+num_bytes]
            with datadict_lock:
                datadict[offset] = m2
            element = [offset, num_bytes]
            with reqs_lock:
                if element in reqs:
                    reqs.remove(element)
            t = time.time()
            rtt_l.append(t-s)
            time.sleep(0.015)
        except socket.timeout:
            continue            
    # sum_ = 0
    rtt_l.sort()
    x = len(rtt_l)
    mid = x//2
    rtt = (rtt_l[mid] + rtt_l[~mid])/2
    print("RTT is :",rtt)
    if rtt < 0.0001:
        rtt = 0.0001
    burst_size = int((0.05/rtt))
    default = 1
    burst_size = 5
    print("burst_size is :",burst_size)
    rec_thread = threading.Thread(target=recieving_thread, args=(UDPClientSocket,rtt))
    rec_thread.start()
    send_thread = threading.Thread(target=sending_thread, args=(UDPClientSocket,rtt,default))
    send_thread.start()
    send_thread.join()
    rec_thread.join()
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

        
if __name__ == "__main__":
    main()