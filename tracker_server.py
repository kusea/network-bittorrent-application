import socket
import time
import threading
import json

IP = "192.168.214.205"
PORT = 4456
SIZE = 1024
FORMAT = "utf-8"

# This can be done with list (not sure about array) 
# They all have upsides and disadvantages
client_list = {}    
file_list = {} 

# Func to send message to client
def send_message(message, conn):
    conn.send(message.encode())

def remove_client(username):
    # Remove the client from client_list and get the client details
    client_details = client_list.pop(username, None)
    
    if client_details is None:
        print(f"User {username} not found.")
        return
    # Remove values of deleted username from file_list
    for file, client_with_file in list(file_list.items()):
        file_list[file] = [client for client in client_with_file if client[0] != username]
        if not file_list[file]:
            file_list.pop(file)

    print(f"User {username} has been removed.")


# Function to return client's name, ip and client_server_port

def get_client_information(username):
    # This function should return the client information for the given username
    return client_list.get(username)

def ping_client(hostname):
    if not client_list:
        print("There's no user connecting right now.\n")
        return
    try:
        # Find the client
        client_info = get_client_information(hostname)
        # If client is not found print error and return
        if not client_info:
            print(f"{hostname} is not in the client list.")
            return
        
        client_port = client_info[0]
        user_ip = client_info[1]
        client_server_port = int(client_info[2])

        # Server will create a client socket to connect to 
        # the client_server_port where client has its own binding socket
        connect_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connect_socket.connect((user_ip, client_server_port))
        connect_socket.settimeout(5)

        # Ping and wait
        connect_socket.send("Ping".encode())
        time.sleep(5)
        data = connect_socket.recv(SIZE).decode(FORMAT)

        # If client doesn't respond remove client
        if not data:
            remove_client(hostname)
        else:
            print(f"User {hostname} still connecting.")
        # End connection
        connect_socket.close()
    except socket.error as e:
        remove_client(hostname)
        return
    except Exception as e:
        return

# LEGACY CODE
def send_avail_sender_list(receiver_id, fname):
    conn = client_list[receiver_id]
    sender_list = file_list.get(fname, [])
    send_message(receiver_id, str(sender_list))
    return (len(sender_list) > 0)

# LEGACY CODE
def check_valid_sender(client_id, fname):
    sender_list = file_list[fname]
    if (client_id in sender_list) and ping_client(client_id):
        return True
    else:
        return False

def handle_download_file(client_conn, file_name):
    list_name = file_list.get(file_name)
    if not list_name :
        client_conn.send("none".encode())
        print(f"File {file_name} not found.") 
    else:
        # This line of code encapsulates my insanity solving this
        # https://stackoverflow.com/questions/17796446/convert-a-list-to-a-string-and-back
        send_msg = json.dumps(list_name)
        client_conn.send(send_msg.encode())

def handle_inform(file_name, username, size):
    # Retrieve client details using the username
    client_details = client_list.get(username)
    
    if not client_details:
        print(f"User {username} not found.")
        return

    client_port, client_ip, client_server_port = client_details

    # Add the file to the file_list
    file_list[file_name] = file_list.get(file_name, []) + [(username, client_ip, client_server_port, size)]
    print(f"Peer {username} downloaded file {file_name}")    

def handle_scrape(client_conn):
    online_clients = {username: [] for username in client_list}  # Initialize all online clients

    # Gather information about online clients and their files
    for file_name, clients in file_list.items():
        for client in clients:
            username = client[0]
            file_size = client[3]
            if username in online_clients:  # Check if the client is online
                online_clients[username].append((file_name, file_size))

    # Prepare the message to send
    message = f"Number of peers online: {len(online_clients)}\n"
    message += "Online peers with their files:\n"
    for username, files in online_clients.items():
        if files:
            files_str = ', '.join([f"{file_name} ({float(file_size):.2f} KB)" for file_name, file_size in files])
        else:
            files_str = "No files"
        message += f"[{username}]: {files_str}\n"

    # Send the message to the client
    client_conn.send(message.encode('utf-8'))

    print("Sent online peers and their files to the peer.")



def handle_share_file(client_conn, file_name, username, size):
    # Find the username associated with the client connection
    client_details = client_list.get(username)
    if not client_details:
        print(f"User {username} not found.")
        return

    client_port, client_ip, client_server_port = client_details
    # Add the file to the file_list
    file_list[file_name] = file_list.get(file_name, []) + [(username, client_ip, client_server_port, size)]

    send_message("Success", client_conn)
    print(f"Peer {username} shared file {file_name}")

# Function for server to discover and ping clients
def handle_commands():
    while True:
        # func : action
        # hostname : username
        command = input()
        if command:
            func, hostname = command.split()

            # Discover client 
            if func == 'discover':
                try:
                    files =  []
                    for file_name, list_name in file_list.items():
                        for client in list_name:
                            if client[0] == hostname:
                                files.append(file_name)
                    print(f"Files of current hostname {hostname}:")
                    print(files)
                except Exception as e:
                    print(f"Error discovering user: {e} ")
            
            elif func == 'ping':
                try:
                    ping_client(hostname)
                except Exception as e:
                    print(f"Error pinging user: {e} ")

            elif func == 'list' and hostname == 'all':
                try:
                    if not client_list:
                        print("No users are currently connected.")
                    else:
                        print("List of all connected peers:")
                        for client in client_list.keys():
                            username = client
                            print(f"[{username}]")
                except Exception as e:
                    print(f"Error listing all peers: {e}")

def handle_peer_connection(client_conn, username):
    try:
        while True:
            message_length = client_conn.recv(SIZE).decode(FORMAT) 
            if message_length:
                if len(message_length.split()) == 2:
                    func, name = message_length.split()
                elif len(message_length.split()) == 1:
                    func = message_length
                elif len(message_length.split()) == 3:
                    func, name, size = message_length.split()

                if func.lower() == 'share':
                    try:
                        handle_share_file(client_conn, name, username, size)
                    except Exception as e:
                        print(f"Error while sharing: {e}")
                elif func.lower() == 'download':
                    try:
                        handle_download_file(client_conn, name)  
                    except Exception as e:
                        print(f"Error while downloading: {e}")
                elif func.lower() == 'disconnect':
                    try:
                        remove_client(username)
                    except Exception as e:
                        print(f"Error while disconnecting: {e}")
                elif func.lower() == 'scrape':
                    try:
                        handle_scrape(client_conn)
                    except Exception as e:
                        print(f"Error while scraping: {e}")
                elif func.lower() == 'inform':
                    try:
                        handle_inform(name, username, size)
                    except Exception as e:
                        print(f"Error while informing: {e}")
    # Handle exception, remove_client and disconnect them
    except Exception as e:
        print("Client disconnected.")
        remove_client(username)
        client_conn.close()
                  
    

def main():
    # Text
    print("[STARTING] Tracker Server is starting.\n")

    # Server creates a socket with static IP and PORT for connection 
    # IP = https://www.tutorialspoint.com/python-program-to-find-the-ip-address-of-the-client
    # PORT = 4456
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hostname = socket.gethostname()
    server_ip_address = socket.gethostbyname(hostname)
    server_socket.bind((server_ip_address, PORT))

    print(server_socket.getsockname()[0])

    # Limits listening clients to 20
    server_socket.listen(20)

    # Text
    print("[LISTENING] Server is waiting for clients.")

    # A thread is created for server's self command (ping, discover)
    command_thread = threading.Thread(target=handle_commands)
    command_thread.start()

    while True:
        client_conn, client_addr = server_socket.accept()
        client_ip = client_conn.getpeername()[0]
        client_port = client_conn.getpeername()[1]
        # Client send their name and 2nd server's port (i hate pier-to-pier)
        username = client_conn.recv(SIZE).decode(FORMAT)
        while username in client_list:
            send_message("Invalid", client_conn)
            print(f"User {username} already exists. Please enter a different username.")
            username = client_conn.recv(SIZE).decode(FORMAT)
        send_message("Valid", client_conn)
        client_server_port = int(client_conn.recv(SIZE).decode(FORMAT))
        client_list[username] = (client_port, client_ip, client_server_port)

        # finally server will notify in terminal
        print(f"User {username}, IP: {client_ip}, Port: {client_port} connected.")

        client_thread = threading.Thread(target=handle_peer_connection, args=(client_conn, username))
        client_thread.start()


if __name__ == "__main__":
    main()
