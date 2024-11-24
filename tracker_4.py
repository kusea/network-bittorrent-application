import threading
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time

local_ip = "128.64.1.15"
local_port = 2400

class Tracker(BaseHTTPRequestHandler):
    tracker_data = {
        "peers" : {}, # ex: {"peer_id": {"info": {...}}, "last_seen": time}
        "files" : {}  # ex: {"file_hash": {"peer_id": [list_of_pieces]}}
    }
    lock = threading.Lock()

    def _respond(self, status_code, response_body):
        #Send an HTTP response with a given status code and JSON body.
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_body).encode('utf-8'))

    # Register peer and update file info
    def registerHandle(self, request_data):
        peer_info = request_data.get("peer_info")
        peer_id = peer_info.get("peer_id")
        file_hash = request_data.get("file_hash")
        file_pieces = request_data.get("file_pieces", [])

        self.tracker_data["peers"][peer_id] = {
                        "info": peer_info,
                        "last_seen": time.time()
                    }
        if file_hash and file_hash not in self.tracker_data["files"]:
            self.tracker_data["files"][file_hash] = {}
        self.tracker_data["files"][file_hash][peer_id] = file_pieces
        self._respond(200, {"message": "Peer registered successfully."})

    # Unregister peer
    def unregisterHandle(self, request_data):
        file_hash = request_data.get("file_hash")
        peer_id = request_data["peer_info"]["peer_id"]

        if peer_id in self.tracker_data["peers"]:
            del self.tracker_data["peers"][peer_id]
            if file_hash and file_hash in self.tracker_data["files"]:
                self.tracker_data["files"][file_hash].pop(peer_id, None)
        self._respond(200, {"message": "Peer unregistered successfully."})
        pass

    # Update last_seen timestamp
    def heartbeatHandle(self, request_data):
        peer_id = request_data["peer_info"]["peer_id"]
        if peer_id in self.tracker_data["peers"]:
            self.tracker_data["peers"][peer_id]["last_seen"] = time.time()
            self._respond(200, {"message": "Heartbeat received."})
        else:
            self._respond(404, {"error": "Peer not found."})
        pass

    # Provide list of peers for a given file hash
    def getpeersHandle(self, request_data):
        file_hash = request_data.get("file_hash")
        if file_hash in self.tracker_data["files"]:
            self._respond(200, {"peers": self.tracker_data["files"][file_hash]})
        else:
            self._respond(404, {"error": "File not found."})
        pass

    # Provide metadata about torrents
    def scrapeHandle(self, request_data):
        file_hashes = request_data.get("file_hashes", [])
        scrape_info = {}
        for file_hash in file_hashes:
            if file_hash in self.tracker_data["files"]:
                file_data = self.tracker_data["files"][file_hash]
                scrape_info[file_hash] = {
                    "seeders": len(file_data["peers"]),
                    "leechers": sum(
                        1
                        for peer_id in file_data["peers"]
                        if not self.tracker_data["peers"][peer_id]["info"]["completed"]
                    ),
                    "pieces": file_data["pieces"],
                }
        self._respond(200, {"scrape": scrape_info})
        pass

    def _post(self):
        ## Handle POST requests from peers
        content_length  = int(self.headers.get('Content-Length'))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            request_data = json.loads(post_data)
            action = request_data.get("action")
            with self.lock:  # Ensure thread-safe access to tracker_data
                if action == "register":
                    self.registerHandle(self, request_data)
                elif action == "unregister":
                    self.unregisterHandle(request_data)
                elif action == "heartbeat":
                    self.heartbeatHandle(request_data)
                elif action == "get_peers":
                    self.getpeersHandle(request_data)       
                elif action == "scrape":
                    self.scrapeHandle(request_data)
                else:
                    self._respond(400, {"error": "Invalid action."})
        except Exception as e:
            self._respond(500, {"error": f"Internal server error: {e}"})


def remove_inactive_peers(tracker_data, lock, time_out = 30):
    """Periodically remove inactive peers."""
    while True:
        time.sleep(time_out)
        current_time = time.time()
        with lock:
            inactive_peers = [
                peer_id for peer_id, data in tracker_data["peers"].items()
                if current_time - data["last_seen"] > time_out
            ]
            for peer_id in inactive_peers:
                print(f"Removing inactive peer: {peer_id}")
                del tracker_data["peers"][peer_id]
                for file_hash in tracker_data["files"].keys():
                    tracker_data["files"][file_hash].pop(peer_id)

def stop_server(server, delay):
    time.sleep(delay)
    server.shutdown()
    print('Server stopped.')

def run_tracker(time_out = 60, time_shutdown = 120):
    server = ThreadingHTTPServer((local_ip, local_port), Tracker)
    #Start background thread for removing inactive peers
    threading.Thread(
        target=remove_inactive_peers,
        args=(Tracker.tracker_data, Tracker.lock, time_out),
        daemon= True
    ).start()
    #shut down the thread after 2 minutes
    threading.Thread(
        target= stop_server, args=(server, time_shutdown), 
        daemon= True
    ).start()
    #Run the server
    print(f"Tracker running on {local_ip}:{local_port}")
    server.serve_forever()
    

if __name__ == "__main__":
    run_tracker()