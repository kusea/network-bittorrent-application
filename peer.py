from math import ceil
import socket
import threading
import pickle
import os
import logging
import shutil
import subprocess
import libtorrent as lt



PEERS_DIR = './Peers/'
PEER_TIMEOUT = 2


class File:
    chunk_size = 2048

    def __init__(self, filename: str, owner: str):
        self.filename = filename
        self.path = os.path.join(PEERS_DIR, owner, filename)

    def __str__(self):
        return self.filename


def download_file(src_folder, dest_folder, filename):
    """Downloads the file from the source folder to the destination folder."""
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


class IncompleteFile:
    def __init__(self, filename, owner, size, src_folder=None, dest_folder=None):
        """Constructor for the IncompleteFile class, which handles file chunks."""
        self.filename = filename
        self.owner = owner
        self.size = size
        self.chunk_size = 1024  # Define your chunk size (or pass it as an argument)
        self.n_chunks = ceil(self.size / self.chunk_size)
        self.needed_chunks = [i for i in range(self.n_chunks)]
        self.received_chunks = {}  # To store chunks indexed by chunk number
        self.fp = open(self.filename, 'wb')  # Open the file for writing
        self.src_folder = src_folder
        self.dest_folder = dest_folder

    def get_needed(self):
        """Recalculate the needed chunks list."""
        self.needed_chunks = [i for i in range(self.n_chunks) if i not in self.received_chunks]
        return self.needed_chunks

    def write_chunk(self, buf, chunk_no):
        """Write a chunk of data to the correct position in the file."""
        self.fp.seek(chunk_no * self.chunk_size)
        self.fp.write(buf)
        self.received_chunks[chunk_no] = buf  # Track the received chunk

    def write_file(self):
        """Write the complete file once all chunks are received."""
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
            print(
                f"File '{self.filename}' is still incomplete. {len(self.received_chunks)}/{self.n_chunks} chunks received.")
            return False  # Return False if not all chunks are received


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


def get_files_action(p):
    """Get the file action from a peer and initiate file transfer."""

    # Prompt user for peer's username
    peer_name = input("Enter the name of the peer you want to get files from: ")

    # Check if the peer directory exists
    peer_directory = os.path.join(PEERS_DIR, peer_name)
    if not os.path.isdir(peer_directory):
        print(f"Peer {peer_name} does not exist.")
        return  # Exit the function if the peer directory does not exist

    # List files in the peer's directory
    files = os.listdir(peer_directory)
    if not files:
        print(f"No files available in {peer_name}'s directory.")
        return  # Exit if no files are present in the directory

    # Show the available files
    print(f"Files available in {peer_name}'s directory: {', '.join(files)}")

    # Prompt user for the file they want to receive
    file_name = input("Enter the file name you want to receive: ").strip()

    # Ensure the input file matches one of the available files
    if file_name not in files:
        print(f"File '{file_name}' does not exist in {peer_name}'s directory.")
        return

    # Check if the file is a torrent file
    if file_name.endswith('.torrent'):
        # If it's a torrent file, initiate the torrent download
        torrent_file_path = os.path.join(peer_directory, file_name)
        try:
            # Assuming p has a method to handle the torrent download
            p.download_torrent(torrent_file_path)
            print(f"Torrent file '{file_name}' download initiated.")
        except Exception as e:
            print(f"An error occurred while processing the torrent file: {e}")
        return

    # If the file is not a torrent file, handle it as a regular file
    try:
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

def download_torrent_with_libtorrent(torrent_file_path):
    ses = lt.session()

    # Add the torrent file to the session
    info = lt.torrent_info(torrent_file_path)
    h = ses.add_torrent({'ti': info, 'save_path': './downloads/'})

    print(f"downloading {torrent_file_path}...")

    # Downloading process
    while not h.is_seed():
        s = h.status()
        print(f"{s.name()} Down: {s.download_rate/1000} kB/s Up: {s.upload_rate/1000} kB/s "
              f"Peers: {s.num_peers} %Complete: {s.progress*100:.2f}%")
        time.sleep(1)

    print(f"Download of {torrent_file_path} complete!")

class CompleteFile(File):
    def __init__(self, filename: str, owner: str):
        super().__init__(filename, owner)
        self.size = self.get_size(self.path)
        self.n_chunks = ceil(self.size / self.chunk_size)
        self.fp = open(self.path, 'rb')

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

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        # Update destination folder based on the username (self.name)
        self.dest_folder = os.path.join(PEERS_DIR, self.name)  # Destination folder for the current peer
        if not os.path.exists(self.dest_folder):
            os.makedirs(self.dest_folder)  # Create the folder if it doesn't exist

        self.available_files = {}
        for f in os.listdir(self.directory):
            self.available_files[f] = CompleteFile(f, self.name)

        self.s = socket.socket()
        self.addr = (ip_addr, port_no)
        self.peers_connections = {}
        self.my_socket = socket.socket()
        if self.port <= 1024:
            raise ValueError("Port number must be above 1024")
        self.my_socket.bind((ip_addr, self.port))

        self.files_in_progress = set()  # Track files currently being downloaded

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
        Listen to peer and give response when asked.
        """
        while True:
            try:
                msg = pickle.loads(c.recv(2048))

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

                if msg['type'] == 'request_chunk':
                    file_name = msg['data']['filename']
                    chunk_no = msg['data']['chunk_no']
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
            except EOFError:  # Handle possible EOF errors
                pass

    def connect_to_peer(self, addr):
        """
        Connect to the peer through new and return the connection.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(addr)
            logging.info(f"Connected to Peer {addr}")
        except:
            print("could not connect to ", addr)
        return sock

    def connect_and_fetch_file_details(self, addr, file_name, file_details: dict[str, object]):
        c = self.connect_to_peer(addr)
        msg = pickle.dumps

if __name__ == "__main__":
    try:
        port_no = int(input("Enter Port Number: "))
        name = input("Enter your name: ")
        logging.basicConfig(filename="logs/" + name + '.log', encoding='utf-8', level=logging.DEBUG)
        p = Peer(port_no, name)
        connected = 1
        print(f"our available files are: {list(p.available_files.keys())}")
        print("2|get_peers: update the peers list")
        print("3|get_files: get files from peers")

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

            if inp == 'end' or inp == '5':
                os._exit(0)
    except KeyboardInterrupt:
        os._exit(0)