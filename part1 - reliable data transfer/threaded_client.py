import socket
import threading
import time
import random
import sys
import os
import hashlib

serverAddressPort = ("127.0.0.1", 9801)
bufferSize = 4096
md5_hash = hashlib.md5()
time_out = 0.1
datadict = {}
num_packets = 0
datadict_lock = threading.Lock()
reqs_lock = threading.Lock()
reqs = []
M = []
offset_time = {}
start_time = time.time()

def recieving_thread(client):
    global time_out
    global datadict
    global reqs
    all_data = ""
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
                if(z+2+num_bytes > len(m1)):
                    break
                m2 = m1[z+2:z+2+num_bytes]
                with datadict_lock:
                    datadict[offset] = m2
                    all_data = m1[z+2+num_bytes::]
                element = [offset, num_bytes]
                with reqs_lock:
                    if element in reqs:
                        offset_time[offset] = time.time() - start_time
                        reqs.remove(element)
            
        except socket.timeout:
            continue

def sending_thread(client):
    global time_out
    global datadict
    global reqs
    global num_packets

    i = 0
    while True:
        with reqs_lock:
            if len(reqs) == 0:
                break
        with reqs_lock:
            x = i % len(reqs)
            i = i + 1
            print(x)
            req_msg = "Offset: "+str(reqs[x][0])+"\n"+"NumBytes: "+str(reqs[x][1])+"\n\n"
            M.append((time.time()-start_time,reqs[x][0]))
        client.sendto(req_msg.encode(),serverAddressPort)
        time.sleep(0.01)
        
    

def main():
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    UDPClientSocket.settimeout(time_out)
    alpha = b"SendSize\n\n"
    UDPClientSocket.sendto(alpha, serverAddressPort)
    while True:
        try:
            UDPClientSocket.sendto(alpha, serverAddressPort)
            msgFromServer = UDPClientSocket.recvfrom(bufferSize)
            msg = msgFromServer[0]
            break
        except socket.timeout:
            continue
    msg = msg.decode("utf-8")
    msg.rstrip()
    msg = msg[5::]
    msg.lstrip()
    bytes_to_rcv = int(msg)
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
    start_time = time.time()
    rec_thread = threading.Thread(target=recieving_thread, args=(UDPClientSocket,))
    rec_thread.start()
    send_thread = threading.Thread(target=sending_thread, args=(UDPClientSocket,))
    send_thread.start()
    send_thread.join()
    rec_thread.join()
    submit = ""
    for i in range(num_packets):
        submit += datadict[1448*i]

    # print(submit)
    md5_hash = hashlib.md5(submit.encode('utf-8'))
    md5_hex = md5_hash.hexdigest()
    print(md5_hex)

    submit_cmd = "Submit: Doof\n" + "MD5: " + md5_hex + "\n\n"
    UDPClientSocket.sendto(submit_cmd.encode(), serverAddressPort)
    UDPClientSocket.close()
    
    L = []
    for i in range(num_packets):
        L.append((offset_time[1448*i]*1000,1448*i))
    # print(L)        
    # print(M)
        
if __name__ == "__main__":
    main()