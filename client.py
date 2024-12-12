from client_util import *

CLIENT_NAME = input("Enter your name: ")

def handle_incoming_request(conn, addr):
    try:
        data = conn.recv(BYTE).decode(FORMAT)
        if not data:
            return
        # Process and handle the request from the other client
        parts = data.split()
        if parts[0].upper() == "FETCH":
            # Handle FETCH request here
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
    # Client connects to the server and starts sending request
    # but before that they have to process their request (publish, fetch)
    while True:
        command = input("Enter a command (publish, fetch, diconnect, print_scrape): ").lower().strip().split()
        if command[0] == "publish":
            # Publish file in name user desired
            # command[1] : client file name
            # command[2] : client's desired name for the file
            try:
                publish_file(command[1], command[2])
            except Exception as e:
                print(f"Error publishing file: {e}")
                
        elif command[0] == "fetch":
            # Fetch client has file
            # command[1] : file
            try:
                fetch_file(command[1])
            except Exception as e:
                print(f"Error requesting to fetch file: {e}")
        elif command[0] == "disconnect":
            print("Disconnecting from server...")
            msg = "disconnect"
            client_socket.send(msg.encode())
            client_socket.close()
            break
        elif command[0] == "print_scrape":
            print("Scraping...")
            try:
                scrape = send_request("PRINT_SCRAPE")
                print(scrape)
            except Exception as e:
                print(f"Error scraping: {e}")
            
        else:
            print("Invalid command. Supported commands: DISCONNECT, PUBLISH, FETCH, PRINT_SCRAPE")

# Function to process client's fetching file
def fetch_file(file_name):
    # Client ask server about file and server returns clients with name's having the file
    # Format [(username1, client_ip1, client_server_port1),(username2, client_ip2, client_server_port2),etc.]
    target_clients = fetch_from_clients(file_name)
  
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
        sender_client = input("Which user do you want to fetch? (type \"Quit\" to quit.)")
        # if user want to quit
        if sender_client.lower() == "quit":
            break
        for client in client_list:
            # if client is found then thread is open to get file
            if sender_client.lower() == client[0]:
                fetch_handler = threading.Thread(target=fetch_and_receive_file, args=(file_name, client))
                fetch_handler.start()
                loop_break = True
                client_found = True
                break
        if not client_found:
            print("User not found, try again.\n")
        if loop_break:
            break

# Function for client to connect to a different client and ask for file
def fetch_and_receive_file(file_name, client_server):
    try:
        ip_address = client_server[1]
        port = int(client_server[2])
        client_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_client_socket.connect((ip_address, port))
        client_client_socket.settimeout(5)
        
        # Send request name FETCH for handle_incoming_request
        fetch_request = f"FETCH {file_name}"
        client_client_socket.send(fetch_request.encode())

        # Create repository with username if not existed
        repository_path = CLIENT_NAME + "/"
        repository_path = os.path.join(repository_path, file_name)
        os.makedirs(os.path.dirname(repository_path), exist_ok=True)
        with open(repository_path, 'wb') as file:
            while True:
                data = client_client_socket.recv(20480)  # Receive 1 KB at a time (adjust as needed)
                if not data:
                    break 
                file.write(data)

        print("FETCH SUCCESSFUL")
        print(f"File received and saved to {repository_path}")
        inform_fetched_file(file_name)
    except socket.error as e:
        print(f"Error on socket while fetching file: {e}")
        return
    except Exception as e:
        print(f"Error between client fetching file: {e}")
        return
    

# Function to publish a file
def publish_file(lname, fname):
    # Check if the file exists in the specified local path (lname)
    if os.path.exists(lname):
        # Copy the file to the client's repository

        # Create a folder with name CLIENT_NAME
        # or ignore if it already exists
        repository_path = CLIENT_NAME + "/"
        os.makedirs(repository_path, exist_ok=True)

        # The existing or newly created folder directory will merge with the file, 
        # making it in the directory
        target_file_path = os.path.join(repository_path, fname)

        with open(lname, "rb") as source_file, open(target_file_path, "wb") as target_file:
            target_file.write(source_file.read())
        
        # Send a "PUBLISH" request to inform the server

        request = f"PUBLISH {fname}"
        while True:
            recv_msg = send_request(request)
            if recv_msg.upper() == "SUCCESS":
                break
                
        print (f"Publish {fname} succesful!")
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