# creating a tracker for Peer to Peer network
import socket
import threading
import time
import pickle
import os

CONN_TEST_TIME = 1


def is_socket_closed(sock: socket.socket) -> bool:
    """
    for a given socket see if it is closed.
    """
    try:
        # this will try to read bytes without blocking and also without removing them from buffer (peek only)
        # sock.settimeout(0.5)
        try:
            obj = pickle.dumps('testing conn')
            sock.send(obj)
        except socket.error:
            return True
        return False

    except BlockingIOError:
        return False  # socket is open and reading from it would block
    except ConnectionResetError:
        return True  # socket was closed for some other reason
    except Exception as e:
        # logger.exception("unexpected exception when checking if a socket is closed")
        return True
    return False


class Tracker:
    """
    Manages the network
    """
    #Types of each attribute
    s: socket.socket
    connections: dict[(str, int), (socket.socket, (str, int))]
    accept_thread: threading.Thread
    broadcast_peers_thread: threading.Thread
    recv_msg_thread: threading.Thread

    server_ip = '127.0.0.1'
    port = 1233
    connections = dict()

    def __init__(self):
        self.s = socket.socket()
        self.s.bind((self.server_ip, self.port))
        self.s.listen(10)
        print("running. 'close' to stop")

    def __del__(self):
        self.s.close()

    def accept_connections(self):
        """
        accepts connections from peers and adds them into a list

        """
        while True:
            conn, addr = self.s.accept()
            conn.send(b'Send port')
            conn.settimeout(2)
            try:
                peer_addr = pickle.loads(conn.recv(512))
                self.connections[addr] = (conn, peer_addr)
                print(f"Got connection from {addr, peer_addr}")

                self.recv_msg_thread = threading.Thread(target=self.recv_msg, args=(conn, addr))
                self.recv_msg_thread.start()

                self.start_broadcast_peers_thread()
            except Exception as e:
                print(f"Got exception {e} while receiving from addr {addr}")
                break

    def recv_msg(self, c: socket.socket, addr):
        """
        revive msgs from the peers
        """
        while True:
            c.settimeout(10000)
            try:
                msg = c.recv(512).decode()
                if msg == 'close':
                    print(addr)
                    self.connections.pop(addr)
                    self.start_broadcast_peers_thread()
                    break

                if msg == 'get_peers':
                    conn = pickle.dumps({
                        "type": "peers",
                        "peers": [x[1] for a, x in self.connections.items()]
                    })
                    c.send(conn)

            except Exception as e:
                print(f"Got exception {e} while receiving from addr {addr}")
                break

    def periodic_conn_test(self):
        """
        see if the connected peers are reachable.
        If not, remove them from the peers list and broadcast.
        """
        while True:
            closed_connections = []  # stores the keys for closed connections
            for addr, c in self.connections.items():
                if is_socket_closed(c[0]):
                    closed_connections.append(addr)

            n_closed = len(closed_connections)
            for addr in closed_connections:
                self.connections.pop(addr)

            if n_closed > 0:
                self.start_broadcast_peers_thread()

            time.sleep(CONN_TEST_TIME)

    def start_broadcast_peers_thread(self):
        """
        start the broadcast thread
        """
        self.broadcast_peers_thread = threading.Thread(target=self.broadcast_peers)
        self.broadcast_peers_thread.start()

    def broadcast_peers(self):
        """
        sends the details about peers to other peers
        """
        conn = pickle.dumps({
            "type": "peers",
            "peers": [ x[1] for a, x in self.connections.items() ]
        })
        for addr in self.connections:
            self.connections[addr][0].send(conn)

    def run(self):

        self.accept_thread = threading.Thread(target=self.accept_connections)
        self.accept_thread.start()
        self.periodic_conn_test_thread = threading.Thread(target=self.periodic_conn_test)
        self.periodic_conn_test_thread.start()

    def connect_tracker():
        try:
            tracker_ip = '127.0.0.1'
            tracker_port = 1233
            with socket.create_connection((tracker_ip, tracker_port), timeout=1) as s:
                print(f"Connected to tracker at {tracker_ip}:{tracker_port}")
                # Send initial message or perform handshake if needed
                s.sendall(b'Hello, Tracker')
                response = s.recv(1024)
                print(f"Received from tracker: {response.decode()}")
        except (socket.timeout, ConnectionRefusedError) as e:
            print(f"Failed to connect to tracker: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    try:
        manager = Tracker()
        manager.run()
        inp = input()
        if inp == 'c' or inp == 'close':
            os._exit(0)

    except KeyboardInterrupt:
        os._exit(0)