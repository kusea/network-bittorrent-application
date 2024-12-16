import socket
import os
import threading
import json

'''
Client Configuration
''' 
SERVER_IP = "192.168.214.205"
SERVER_PORT = 4456

BYTE = 1024
FORMAT = 'utf-8'

# Main socket to connect to server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))

# 2nd socket for client host (file sharing)
client_host_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

hostname = socket.gethostname()
server_ip_address = socket.gethostbyname(hostname)
client_host_socket.bind((server_ip_address, 0))  
# limit to 5 concurrent users
client_host_socket.listen(5)

# Function to send requests to the server
def send_request(request):
    client_socket.send(request.encode())
    response = client_socket.recv(1024).decode(FORMAT)
    # print("Server response:", response)
    return response

def send_file(conn, file_path):
    with open(file_path, 'rb') as file:
        data = file.read(1048576)  # Read 20 KB at a time (adjust as needed)
        while data:
            conn.send(data)
            data = file.read(1048576)

# Function to fetch target clients for a file
# Returns: dict of available client username and their ports
def download_from_peers(file_name):
    request = f"DOWNLOAD {file_name}"
    return send_request(request)


def inform_downloaded_file(file_name, file_size_str):
    request = f"INFORM {file_name} {file_size_str}"
    client_socket.send(request.encode())

# LEGACY CODE
def retrieve_connect_port(msg):
    haddr, paddr = msg[1:-1].split(", ")
    haddr = haddr[1:-1]
    paddr = int(paddr)
    return paddr

# (127.0.0.1:12345)
# h 127.0.0.1
# p 12345