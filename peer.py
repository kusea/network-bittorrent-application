from peer_util import *

CLIENT_NAME = input("Enter your name: ")

def handle_incoming_request(conn, addr):
    try:
        data = conn.recv(BYTE).decode(FORMAT)
        if not data:
            return
        # Process and handle the request from the other client
        parts = data.split()
        if parts[0].upper() == "DOWNLOAD":
            file_path = CLIENT_NAME + "/" + parts[1]
            send_file(conn, file_path)
            pass
        elif parts[0].upper() == "PING":
            conn.send("PONG".encode())
            pass
        # Add more handlers for other request types
        conn.close()
    except Exception as e:
        conn.close()
    

def listen_for_server():
    while True:
        command = input("Enter a command (share, download, diconnect, scrape): ").lower().strip().split()
        if command[0] == "share":
            try:
                share_file(command[1], command[2])
            except Exception as e:
                print(f"Error sharing file: {e}")
                
        elif command[0] == "download":
            try:
                download_file(command[1])
            except Exception as e:
                print(f"Error requesting to download file: {e}")
        elif command[0] == "disconnect":
            print("Disconnecting from server...")
            msg = "disconnect"
            client_socket.send(msg.encode())
            client_socket.close()
            break
        elif command[0] == "scrape":
            print("Scraping...")
            try:
                scrape = send_request("SCRAPE")
                print(scrape)
            except Exception as e:
                print(f"Error scraping: {e}")
            
        else:
            print("Invalid command. Supported commands: DISCONNECT, SHARE, DOWNLOAD, SCRAPE")

# Function to process client's downloading file
def download_file(file_name):
    # Client ask server about file and server returns clients with name's having the file
    # Format [(username1, client_ip1, client_server_port1),(username2, client_ip2, client_server_port2),etc.]
    # Define the full path to the file
    repository_path = CLIENT_NAME + "/"
    repository_path = os.path.join(repository_path, file_name)
    
    if os.path.exists(repository_path):
        print(f"The file '{file_name}' already exists in the directory '{CLIENT_NAME}'.")
        return
    
    target_clients = download_from_peers(file_name)
  
    if(target_clients == "none"): 
        print("No users have the file.")
        return
    # Print only client name for user to see
    client_list = json.loads(target_clients)
    print("Currently available client:\n")
    for client in client_list:
        print(client[0], '\n')
    # ask user which user they want to get file from
    while True:
        loop_break = False
        client_found = False
        sender_client = input("Which user do you want to download? (type \"Quit\" to quit.)")
        # if user want to quit
        if sender_client.lower() == "quit":
            break
        for client in client_list:
            # if client is found then thread is open to get file
            if sender_client.lower() == client[0]:
                download_handler = threading.Thread(target=download_and_receive_file, args=(file_name, client))
                download_handler.start()
                loop_break = True
                client_found = True
                break
        if not client_found:
            print("User not found, try again.\n")
        if loop_break:
            break

# Function for client to connect to a different client and ask for file
def download_and_receive_file(file_name, client_server):
    try:
        ip_address = client_server[1]
        port = int(client_server[2])
        file_size_str = client_server[3]
        client_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_client_socket.connect((ip_address, port))
        client_client_socket.settimeout(5)
        
        try:
            file_size = float(file_size_str)
        except ValueError:
            print(f"Invalid file size: {file_size_str}")
            return

        # Send request name FETCH for handle_incoming_request
        download_request = f"DOWNLOAD {file_name}"
        client_client_socket.send(download_request.encode())

        # Create repository with username if not existed
        repository_path = CLIENT_NAME + "/"
        repository_path = os.path.join(repository_path, file_name)
        os.makedirs(os.path.dirname(repository_path), exist_ok=True)
        with open(repository_path, 'wb') as file:
            while True:
                data = client_client_socket.recv(1048576)  
                if not data:
                    break 
                file.write(data)
                #print(f"percent downloaded: {file.tell() / (file_size*1024) * 100:.2f}%")
                
        print("DOWNLOAD SUCCESSFUL")
        print(f"File received and saved to {repository_path}")
        inform_downloaded_file(file_name, file_size_str)
    except socket.error as e:
        print(f"Error on socket while downloading file: {e}")
        return
    except Exception as e:
        print(f"Error between client downloading file: {e}")
        return
    

# Function to publish a file
def share_file(lname, fname):
    # Check if the file exists in the specified local path (lname)
    if os.path.exists(lname):
        file_size = os.path.getsize(lname)
        file_size = file_size / 1024
        repository_path = CLIENT_NAME + "/"
        os.makedirs(repository_path, exist_ok=True)

        # The existing or newly created folder directory will merge with the file, 
        # making it in the directory
        target_file_path = os.path.join(repository_path, fname)
        if os.path.exists(target_file_path):
            print(f"The file '{fname}' already exists in the directory '{CLIENT_NAME}'.")
            return

        with open(lname, "rb") as source_file, open(target_file_path, "wb") as target_file:
            target_file.write(source_file.read())

        request = f"SHARE {fname} {file_size}"
        while True:
            recv_msg = send_request(request)
            if recv_msg.upper() == "SUCCESS":
                break
                
        print (f"SHARE {fname} succesful!")
    else:
        print("The specified file does not exist in the local path.")

def main():
    # Client create a Thread to listen_for_server
    global CLIENT_NAME
    recv_msg = send_request(CLIENT_NAME)
    while recv_msg.upper() == "INVALID":
        CLIENT_NAME = input("Enter your name again: ")
        recv_msg = send_request(CLIENT_NAME)


    connect_thread = threading.Thread(target=listen_for_server)
    connect_thread.start()

    client_socket.send(str(client_host_socket.getsockname()[1]).encode())
    while True:
        conn, addr = client_host_socket.accept()
        request_handler = threading.Thread(target=handle_incoming_request, args=(conn, addr))
        request_handler.start()

# Start the main thread to listen for incoming connections from other clients
if __name__ == "__main__":
    main()