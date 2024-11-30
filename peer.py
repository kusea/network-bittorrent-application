from math import ceil
import socket
import threading
import pickle
import os
import logging
import shutil
import subprocess
from piece import TorrentPieceManager



PEERS_DIR = './Peers/'
PEER_TIMEOUT = 2


class File:
    chunk_size = 2048

    def __init__(self, filename: str, owner: str):
        self.filename = filename
        self.path = os.path.join(PEERS_DIR, owner, filename)

    def __str__(self):
        return self.filename


class IncompleteFile:
    def __init__(self, filename, owner, size, src_folder=None, dest_folder=None):
        # File attributes
        self.filename = filename
        self.owner = owner
        self.size = size
        self.chunk_size = 1024  # Define your chunk size (or pass it as an argument)
        self.n_chunks = ceil(self.size / self.chunk_size)
        self.needed_chunks = [i for i in range(self.n_chunks)]  # All chunks are initially needed
        self.received_chunks = {}  # To store chunks indexed by chunk number
        self.fp = open(self.filename, 'wb')  # Open the file for writing
        # Additional folder information for downloading the file
        self.src_folder = src_folder
        self.dest_folder = dest_folder

    def get_needed(self):
        # Recalculate the needed chunks list (for optimization)
        self.needed_chunks = [i for i in range(self.n_chunks) if i not in self.received_chunks]
        return self.needed_chunks

    def write_chunk(self, buf, chunk_no):
        # Write the chunk at the correct position (using seek)
        self.fp.seek(chunk_no * self.chunk_size)
        self.fp.write(buf)
        self.received_chunks[chunk_no] = buf  # Track the received chunk

    def write_file(self):
        # Only write the file if all chunks are received
        if len(self.received_chunks) == self.n_chunks:
            # Sort the chunks by chunk number and write them in the correct order
            with open(self.filename, 'wb') as filep:
                for i in range(self.n_chunks):
                    filep.write(self.received_chunks[i])  # Write chunks in order
            print(f"File '{self.filename}' has been successfully written.")
            if self.src_folder and self.dest_folder:
                download_file(self.src_folder, self.dest_folder, self.filename)
            return True  # Return True indicating the file is complete
        else:
            print(f"File '{self.filename}' is still incomplete. {len(self.received_chunks)}/{self.n_chunks} chunks received.")
            return False  # Return False if not all chunks are received

    def request_missing_chunks(self):
        # Identify the missing chunks
        missing_chunks = self.get_needed()
        print(f"Missing chunks for {self.filename}: {missing_chunks}")

        # Request the missing chunks from the peer (simulated request)
        for chunk_no in missing_chunks:
            print(f"Requesting chunk {chunk_no} from peer {self.owner}")
            # Simulating peer chunk request (you can replace this with real network logic)
            chunk_data = self.request_chunk_from_peer(chunk_no)
            self.write_chunk(chunk_data, chunk_no)

    def request_chunk_from_peer(self, chunk_no):
        # Simulate requesting a chunk from the peer
        # In a real application, you would send a request to the peer to send the chunk
        print(f"Simulating chunk {chunk_no} being sent by peer {self.owner}")
        return b'0' * self.chunk_size  # Simulated chunk data (e.g., 0s or real data)


def download_file(src_folder, dest_folder, filename):
    # Create destination folder if it doesn't exist
    os.makedirs(dest_folder, exist_ok=True)

    # Define the full source and destination file paths
    src_path = os.path.join(src_folder, filename)
    dest_path = os.path.join(dest_folder, filename)

    try:
        # Copy the file from source to destination
        shutil.copy(src_path, dest_path)
        print(f"File '{filename}' successfully copied from {src_folder} to {dest_folder}")
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found in {src_folder}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_files_action(p):  # Add `p` as a parameter
    """Get the file action from a peer and initiate file transfer or torrent download."""

    # Prompt user for the action
    action = input("Do you want to (1) receive a file or (2) download a torrent? Enter the number: ")

    if action == '1':
        # Handle file transfer as in the old code
        peer_name = input("Enter the name of the peer you want to get files from: ")

        # Check if the peer directory exists
        peer_directory = os.path.join(PEERS_DIR, peer_name)
        try:
            # Prompt for the file name to receive
            file_name = input("Enter the file name you want to receive: ")

            # Construct the path to the file in the peer's directory
            file_path = os.path.join(peer_directory, file_name)

            # Check if the file already exists in the current directory
            dest_path = os.path.join(p.dest_folder, file_name)
            if os.path.exists(dest_path):
                print(f"File '{file_name}' already exists in your folder. Overwriting.")

            # Create an IncompleteFile instance and handle chunking for the file
            incomplete_file = IncompleteFile(filename=file_name, owner=peer_name, size=os.path.getsize(file_path),
                                             src_folder=peer_directory, dest_folder=p.dest_folder)

            # Simulate receiving all chunks (for testing)
            with open(file_path, 'rb') as f:
                chunk_no = 0
                while chunk := f.read(incomplete_file.chunk_size):
                    incomplete_file.write_chunk(chunk, chunk_no)
                    chunk_no += 1

            # Once all chunks are received, call write_file
            incomplete_file.write_file()

            # Request any missing chunks
            incomplete_file.request_missing_chunks()

            print(f"File '{file_name}' received successfully!")

        except Exception as e:
            print(f"An error occurred while receiving the file: {e}")


    elif action == '2':

        # Handle torrent download

        peer_name = input("Enter the name of the peer you want to get the torrent file from: ")
        peer_directory = os.path.join(PEERS_DIR, peer_name)
        torrent_file_name = input("Enter the name of the torrent file (e.g., he.torrent): ")

        # Construct the full path to the torrent file in the peer's directory

        torrent_file_path = os.path.join(peer_directory, torrent_file_name)

        # Check if the torrent file exists

        if not os.path.exists(torrent_file_path):

            print(f"Error: The torrent file '{torrent_file_path}' does not exist.")

        else:

            # Define the destination directory for the download

            destination_directory = p.dest_folder

            # Call the method to download the torrent

            success = download_torrent_with_transmission(peer_name, torrent_file_path, destination_directory)

            if success:

                print(f"Torrent file '{torrent_file_path}' download initiated.")

            else:

                print(f"Failed to download torrent file '{torrent_file_path}'.")

    else:
        print("Invalid action. Please enter '1' or '2'.")


def download_torrent_with_transmission(peer_name, torrent_file_path, destination_folder):
    """
    Use transmission-remote to add the torrent and manage download speed.
    """
    try:
        # Convert the destination folder to an absolute path
        absolute_destination_folder = os.path.abspath(destination_folder)

        # Construct the command to add a torrent and set a download limit (e.g., 500 KB/s)
        command = [
            "transmission-remote", "-a", torrent_file_path,
            "--downlimit", "500",  # Set the download speed limit to 500 KB/s
            "--download-dir", absolute_destination_folder  # Set the download directory as absolute path
        ]

        # Execute the command and capture the output
        result = subprocess.run(command, capture_output=True, text=True)

        # Print the output and error for debugging
        print(f"Command executed: {' '.join([str(item) for item in command])}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        print(f"Exit code: {result.returncode}")


        # Check if the command was successful
        if result.returncode == 0:
            print(f"Torrent added successfully. Output:\n{result.stdout}")
            return True
        else:
            print(f"Error adding torrent: {result.stderr}")
            return False

    except Exception as e:
        print(f"An error occurred while downloading the torrent: {e}")
        return False


class CompleteFile(File):
    def __init__(self, filename: str, owner: str):
        try:
            # Debug: Print input filename and owner
            print(f"Initializing CompleteFile with filename: {filename}, owner: {owner}")

            super().__init__(filename, owner)

            # Debug: Check and print file path
            print(f"Checking file path: {self.path}")
            if not os.path.exists(self.path):
                raise FileNotFoundError(f"File not found at path: {self.path}")

            # Get file size
            self.size = self.get_size(self.path)
            print(f"File size for {self.path}: {self.size} bytes")

            # Calculate number of chunks
            self.n_chunks = ceil(self.size / self.chunk_size)
            print(f"Number of chunks: {self.n_chunks}")

            # Open file for reading
            self.fp = open(self.path, 'rb')
            print(f"File {self.path} opened successfully")

        except FileNotFoundError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error during initialization: {e}")

    def get_chunk_no(self, chunk_no):
        return self._get_chunk(chunk_no * self.chunk_size)

    def _get_chunk(self, offset):
        self.fp.seek(offset, 0)
        chunk = self.fp.read(self.chunk_size)
        return chunk


    @staticmethod
    def get_size(path):
        print(f"Checking size for file at: {path}")
        if os.path.exists(path):
            return os.path.getsize(path)
        else:
            print(f"File not found: {path}")
            return 0



class Peer:
    s: socket.socket
    peers: list[(str, int)]  # list of all peers
    peers_connections: dict[(str, int), socket.socket]
    port: int
    manager_port = 1233
    addr: (str, int)
    available_files: dict[str, CompleteFile]
    files_in_progress: set

    def __init__(self, port_no: int, name: str, ip_addr='127.0.0.1'):
        self.port = port_no
        self.name = name
        self.directory = os.path.join(PEERS_DIR, name)
        self.s = socket.socket()
        self.addr = (ip_addr, port_no)
        self.peers_connections = {}
        self.my_socket = socket.socket()
        self.ip_addr = ip_addr;

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

            # Update destination folder based on the username (self.name)
        self.dest_folder = os.path.join(PEERS_DIR, self.name)  # Destination folder for the current peer
        if not os.path.exists(self.dest_folder):
            os.makedirs(self.dest_folder)  # Create the folder if it doesn't exist

        self.available_files = {}
        for f in os.listdir(self.directory):
            self.available_files[f] = CompleteFile(f, self.name)
        self.files_in_progress = set()  # Track files currently being downloaded

        if self.port <= 1024:
            raise ValueError("Port number must be above 1024")

        # Step 1: Kill any existing process using the port
        self.kill_process_using_port(self.port)
        # Step 2: Create and configure the socket
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Step 3: Bind the socket to the address
        try:
            self.my_socket.bind((self.ip_addr, self.port))
            print(f"Successfully bound to {self.ip_addr}:{self.port}")
        except OSError as e:
            raise Exception(f"Failed to bind to {self.ip_addr}:{self.port}. Error: {e}")

        # Step 4: Start listening for connections
        self.my_socket.listen(5)
        print(f"Listening on {self.ip_addr}:{self.port}...")

        # Initialize other attributes
        self.files_in_progress = set()  # Track files currently being downloaded


    def kill_process_using_port(self, port):
        import os
        import signal
        import subprocess

        try:
            # Find the process using the port
            command = f"lsof -ti:{port}"
            process = subprocess.check_output(command, shell=True).decode().strip()

            if process:
                os.kill(int(process), signal.SIGKILL)
                print(f"Killed process using port {port}.")
        except subprocess.CalledProcessError:
            print(f"No process found using port {port}.")

    def connect_manager(self):
        """
        Connect to manager
        """
        self.s.connect(('localhost', self.manager_port))
        msg = self.s.recv(512).decode()
        if msg == 'Send port':
            self.s.send(pickle.dumps(self.addr))

    def receive(self):
        """
        Receive the other peers and update the list.
        """
        while True:
            try:
                msg = self.s.recv(512)

                msg = pickle.loads(msg)
                if msg != "testing conn":
                    self.peers = msg['peers']
                    logging.info(f"available peers are {self.peers}")
                    print(f"available peers are {self.peers}")
            except ConnectionAbortedError:
                print("connection with manager is closed")
                break

    def update_peers(self):
        try:
            msg = b"get_peers"
            self.s.send(msg)
        except Exception:
            print("could not get the peers list")

    def __del__(self):
        self.s.close()
        self.my_socket.close()

    def disconnect(self):
        """
        Disconnect the connected socket.
        """
        self.s.send(b"close")
        self.s.close()
        self.my_socket.close()

    def connect_to_peers(self):
        """
        Listens to other peers and adds into peer connections
        """
        self.my_socket.listen(10)
        try:
            while True:
                c, addr = self.my_socket.accept()

                self.peers_connections[addr] = {
                    "connection": c
                }
                listen_peers_thread = threading.Thread(target=self.listen_to_peer, args=(c, addr))
                listen_peers_thread.start()
        except OSError as e:
            print(e.errno)

    def listen_to_peer(self, c: socket.socket, addr):
        """
        Listen to peer and give responses when requested.
        Enhanced with better error handling and proper connection management.
        """
        logging.info(f"Listening to peer at {addr}")
        try:
            while True:
                try:
                    # Receive and process a message
                    msg = pickle.loads(c.recv(2048))

                    if not msg:  # Handle case where peer sends an empty message
                        logging.warning(f"Received an empty message from {addr}. Closing connection.")
                        break

                    if msg['type'] == 'request_file':
                        req_file_name = msg['data']
                        if req_file_name in self.available_files:
                            file_details = pickle.dumps({
                                "type": "available_file",
                                "data": {
                                    "filesize": str(self.available_files[req_file_name].size)
                                }
                            })
                            c.send(file_details)
                            logging.info(f"Sent file details for '{req_file_name}' to {addr}")
                        else:
                            logging.warning(f"Requested file '{req_file_name}' not available. Sending error.")
                            error_msg = pickle.dumps({
                                "type": "error",
                                "data": "File not available"
                            })
                            c.send(error_msg)

                    elif msg['type'] == 'request_chunk':
                        file_name = msg['data']['filename']
                        chunk_no = msg['data']['chunk_no']
                        if file_name in self.available_files:
                            chunk = self.available_files[file_name].get_chunk_no(chunk_no)
                            ret_msg = pickle.dumps({
                                "type": "response_chunk",
                                "data": {
                                    "chunk_no": chunk_no,
                                    "filename": file_name,
                                    "chunk": chunk
                                }
                            })
                            c.send(ret_msg)
                            logging.info(f"Sent chunk {chunk_no} of file '{file_name}' to {addr}")
                        else:
                            logging.warning(
                                f"Requested file '{file_name}' for chunk {chunk_no} not available. Sending error.")
                            error_msg = pickle.dumps({
                                "type": "error",
                                "data": "File not available"
                            })
                            c.send(error_msg)

                    else:
                        logging.warning(f"Received unknown message type '{msg.get('type')}' from {addr}.")
                        error_msg = pickle.dumps({
                            "type": "error",
                            "data": "Unknown request type"
                        })
                        c.send(error_msg)
                except (EOFError, ConnectionResetError):
                    logging.info(f"Connection with {addr} closed by peer.")
                    break
                except pickle.UnpicklingError:
                    logging.error(f"Received invalid or corrupted message from {addr}. Ignoring.")
                except Exception as e:
                    logging.error(f"Unexpected error while communicating with {addr}: {e}")

        finally:
            c.close()
            logging.info(f"Connection with {addr} closed.")

    def connect_to_peer(self, addr):
        """
        Connect to the peer through new and return the connection.
        Includes verification that the peer is reachable and valid.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(addr)
            # Verify the connection by sending a simple handshake message
            handshake_msg = pickle.dumps({"type": "handshake", "data": "ping"})
            sock.send(handshake_msg)
            response = pickle.loads(sock.recv(512))  # Wait for a handshake response
            if response.get("type") == "handshake" and response.get("data") == "pong":
                logging.info(f"Successfully connected and verified Peer {addr}")
            else:
                logging.error(f"Peer {addr} failed to respond with a valid handshake.")
                sock.close()
                return None
        except socket.timeout:
            logging.error(f"Connection to {addr} timed out.")
            return None
        except ConnectionRefusedError:
            logging.error(f"Peer {addr} refused the connection.")
            return None
        except Exception as e:
            logging.error(f"Could not connect to {addr} due to an unexpected error: {e}")
            return None
        return sock

    def get_peers_with_file(self, file_name: str):
        """
        Check which peers have the file and what parts of it they have.
        Details of the file such as size are also sent.
        """
        running_threads = []
        file_details = {
            "size": None,
            "peers_with_file": []
        }

        lock = threading.Lock()  # Create a lock to prevent race conditions

        def update_file_details(p, file_name, file_details):
            """Fetch file details from a specific peer."""
            # Ensure the correct peer folder is being accessed (e.g., peer1 or peer3)
            peer_folder = f"Peers/{p}"
            file_path = os.path.join(peer_folder, file_name)

            # Check if the file exists in the correct folder (peer1, peer3, etc.)
            if os.path.exists(file_path):
                with lock:  # Ensure thread-safe access to shared file_details
                    file_details["size"] = os.path.getsize(file_path)
                    file_details["peers_with_file"].append(p)

        # First check if peer1 has the file, then fall back to other peers
        for peer in ['peer1', 'peer3']:  # Prioritize peer1, then check others
            thread = threading.Thread(target=update_file_details, args=(peer, file_name, file_details))
            running_threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in running_threads:
            thread.join()

        # If file is found in any peer, return the details
        if file_details["size"] is None:
            print(f"File '{file_name}' is unavailable.")
        else:
            print(f"File '{file_name}' found with peers: {file_details['peers_with_file']}")

        return file_details

    def receive_file(self, file_path):
        file_name = os.path.basename(file_path)
        print(f"Looking for file: {file_name}")  # Debugging print
        file_details = self.get_peers_with_file(file_name)
        print(f"File details: {file_details}")  # Debugging print

        if file_details['size'] is None:
            print(f"File '{file_name}' is unavailable.")
            return

        if file_name in self.files_in_progress:  # Skip if the file is already being downloaded
            print(f"File '{file_name}' is already in progress.")
            return

        self.files_in_progress.add(file_name)  # Mark the file as being downloaded
        incomplete_file = IncompleteFile(file_name, self.name, file_details['size'])

        for peer in file_details['peers_with_file']:
            self._fetch_file_chunks(peer, incomplete_file)

        incomplete_file.write_file()
        self.files_in_progress.remove(file_name)  # File download completed

    def _fetch_file_chunks(self, peer, incomplete_file):
        for chunk_no in incomplete_file.get_needed():
            c = self.connect_to_peer(peer)
            msg = pickle.dumps({
                "type": "request_chunk",
                "data": {
                    "filename": incomplete_file.filename,
                    "chunk_no": chunk_no
                }
            })
            c.send(msg)
            c.settimeout(PEER_TIMEOUT)

            try:
                response = pickle.loads(c.recv(2048))
                if response['type'] == 'response_chunk':
                    chunk_data = response['data']['chunk']
                    incomplete_file.write_chunk(chunk_data, response['data']['chunk_no'])
            except socket.timeout:
                print(f"Timed out while downloading chunk {chunk_no} from {peer}")
            finally:
                c.close()

# Add the transmission-remote command
def monitor_torrent_status(torrent_id=1):
    try:
        command = f"transmission-remote -t {torrent_id} -si"
        os.system(command)
    except Exception as e:
        print(f"Error while monitoring torrent: {e}")


def seeder(torrent_file_path, download_dir):
    """
    Simulate seeding by adding a torrent with a download limit and setting the download directory.
    """
    command = [
        "transmission-remote",
        "--add", torrent_file_path,
        "--downlimit", "500",  # Set download speed limit to 500 KB/s
        "--download-dir", download_dir  # Set download directory
    ]

    # Execute the seeder command
    subprocess.run(command)
    print(f"Seeder started with torrent: {torrent_file_path}")


def leecher(torrent_file_path, download_dir):
    """
    Simulate leeching by adding a torrent with a download limit and setting the download directory.
    """
    command = [
        "transmission-remote",
        "--add", torrent_file_path,
        "--downlimit", "500",  # Set download speed limit to 500 KB/s
        "--download-dir", download_dir  # Set download directory
    ]

    # Execute the leecher command
    subprocess.run(command)
    print(f"Leecher started with torrent: {torrent_file_path}")


def seed_torrent_with_transmission(peer_name, file_name, peers_dir, dest_folder):
    """
    Use transmission-remote to start seeding a torrent for a given peer.
    Assumes the torrent file is already fully downloaded in the given directory.
    """
    try:
        # Construct the full path to the peer's directory
        peer_directory = os.path.join(PEERS_DIR, peer_name)

        # Check if the peer directory exists
        if not os.path.exists(peer_directory):
            print(f"Error: Peer directory '{peer_directory}' does not exist.")
            return False

        # Construct the path to the file in the peer's directory
        file_path = os.path.join(peer_directory, file_name)

        # Check if the file exists in the peer's directory
        if not os.path.exists(file_path):
            print(f"Error: File '{file_name}' does not exist in the peer's directory.")
            return False

        # Convert the destination folder to an absolute path
        absolute_destination_folder = os.path.abspath(dest_folder)

        # First, add the torrent to transmission using -a (this is necessary before seeding)
        command_add = [
            "transmission-remote", "-a", file_path,  # Add the torrent file
            "--download-dir", absolute_destination_folder  # Set the download directory as the absolute path
        ]

        # Execute the command to add the torrent
        result_add = subprocess.run(command_add, capture_output=True, text=True)

        # Print the output and error for adding the torrent
        print(f"Command executed: {' '.join([str(item) for item in command_add])}")
        print(f"Stdout: {result_add.stdout}")
        print(f"Stderr: {result_add.stderr}")
        print(f"Exit code: {result_add.returncode}")

        # Check if adding the torrent was successful
        if result_add.returncode != 0:
            print(f"Error adding torrent: {result_add.stderr}")
            return False

        # Ask the user to enter the torrent ID (hash)
        torrent_hash = input("Enter the torrent ID (hash) to start seeding: ").strip()

        # Validate the torrent hash
        if not torrent_hash:
            print("Error: No torrent hash entered.")
            return False

        # Now, start seeding the torrent using the -s option with the user-provided torrent hash
        command_seed = [
            "transmission-remote", "-t", torrent_hash,  # Use -t first to specify the torrent by its hash
            "-s",  # Start seeding the torrent
            "--download-dir", absolute_destination_folder  # Set the download directory as absolute path
        ]
        # Execute the command to start seeding the torrent
        result_seed = subprocess.run(command_seed, capture_output=True, text=True)

        # Print the output and error for seeding the torrent
        print(f"Command executed: {' '.join([str(item) for item in command_seed])}")
        print(f"Stdout: {result_seed.stdout}")
        print(f"Stderr: {result_seed.stderr}")
        print(f"Exit code: {result_seed.returncode}")

        # Check if the seeding command was successful
        if result_seed.returncode == 0:
            print(f"Torrent seeding started successfully. Output:\n{result_seed.stdout}")
            return True
        else:
            print(f"Error starting seeding: {result_seed.stderr}")
            return False

    except Exception as e:
        print(f"An error occurred while starting seeding: {e}")
        return False

if __name__ == "__main__":
    try:
        port_no = int(input("Enter Port Number: "))
        name = input("Enter your name: ")
        logging.basicConfig(filename="logs/" + name + '.log', encoding='utf-8', level=logging.DEBUG)
        p = Peer(port_no, name)
        connected = 1
        print(f"our available files are: {list(p.available_files.keys())}")
        print("Give one of the commands:")
        print("0|cls: Close the connection with manager")
        print("1|conn: connect to manager")
        print("2|get_peers: update the peers list")
        print("3|get_files: get files from peers")
        print("4|sharable_files: get the list of sharable files")
        print("5|monitor_torrent: Monitor torrent status (default id = 1)")
        print("6|end: End the program\n\n")

        # Connect to manager and retrieve peers
        p.connect_manager()

        # Start the receive thread (non-blocking)
        receive_thread = threading.Thread(target=p.receive)
        receive_thread.daemon = True  # Ensures the thread exits when the main program exits
        receive_thread.start()

        while True:
            inp = input(">")
            if inp == 'cls' or inp == '0':
                if connected:
                    p.disconnect()
                    del p
                    connected = 0
                else:
                    print("peer is not connected!")

            if inp == "conn" or inp == '1':
                if not connected:
                    p = Peer(port_no, name)
                    connected = 1
                else:
                    print("peer is already connected to manager")

            if inp == "get_peers" or inp == '2':
                p.update_peers()  # Request for peer update manually
                print(f"available peers are: {p.peers}")

            if inp == "3" or inp == "get_files":
                get_files_action(p)

            if inp == 'sharable_files' or inp == '4':
                print(f"our available files are: {list(p.available_files.keys())}")

            if inp == 'monitor_torrent' or inp == '5':
                monitor_torrent_status()

            if inp == '7':
                # Get user input for peer name and file name
                peer_name = input("Enter the name of the peer: ")
                file_name = input("Enter the file name to seed: ")
                dest_folder = os.path.join(PEERS_DIR, name)

                # Call the function to start seeding the torrent
                success = seed_torrent_with_transmission(peer_name, file_name, PEERS_DIR, dest_folder)

                if success:
                    print("Seeding started successfully.")
                else:
                    print("Failed to start seeding.")

            elif inp == '0':
                print("Exiting the program.")
                break
            else:
                print("Invalid option. Please try again.")

            if inp == 'end' or inp == '6':
                os._exit(0)
    except KeyboardInterrupt:
        os._exit(0)