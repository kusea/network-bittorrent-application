import time
import select
from threading import Thread
import pub
import logging
import message
import peer
import errno
import socket
import random

MAX_PEERS_CONNECTED = 30  # Define the maximum number of peers to connect to

class PeersManager(Thread):
    def __init__(self, torrent, pieces_manager):
        Thread.__init__(self)
        self.peers = []
        self.torrent = torrent
        self.pieces_manager = pieces_manager
        self.pieces_by_peer = [[0, []] for _ in range(pieces_manager.number_of_pieces)]
        self.is_active = True
        self.request_queues = {}  # Added: request queues for each peer
        self.global_requested_blocks = {}  # Added: global tracking for requested blocks

        # Events
        pub.subscribe(self.peer_requests_piece, 'PeersManager.PeerRequestsPiece')
        pub.subscribe(self.peers_bitfield, 'PeersManager.updatePeersBitfield')

    def add_peers(self, peers):
        for peer in peers:
            if peer not in self.peers:
                self.peers.append(peer)
                logging.info(f"New peer added: {peer.ip}:{peer.port}")
        logging.info('Connected to %d/%d peers' % (len(self.peers), MAX_PEERS_CONNECTED))

    def get_random_peer_having_piece(self, piece_index):
        available_peers = [peer for peer in self.peers if peer.has_piece(piece_index)]
        if available_peers:
            return random.choice(available_peers)
        return None

    def unchoked_peers_count(self):
        return len([peer for peer in self.peers if peer.is_unchoked()])

    def manage_requests(self):
        for piece_index in range(self.pieces_manager.number_of_pieces):
            if not self.pieces_manager.is_piece_downloaded(piece_index):
                peer = self.get_random_peer_having_piece(piece_index)
                if peer:
                    for block_offset, block_length in self.pieces_manager.get_missing_blocks(piece_index):
                        if (piece_index, block_offset) not in self.global_requested_blocks:
                            self.add_request_to_queue(peer, piece_index, block_offset, block_length)
                            peer.request_block(piece_index, block_offset, block_length)

    def run(self):
        while self.is_active:
            self.manage_requests()
            read = [peer.socket for peer in self.peers]
            read_list, _, _ = select.select(read, [], [], 1)

            for socket in read_list:
                peer = self.get_peer_by_socket(socket)
                messages = peer.get_messages()
                for message in messages:
                    self.handle_message(peer, message)

    def peer_requests_piece(self, request=None, peer=None):
        if not request or not peer:
            return

        piece_index, block_offset, block_length = request.piece_index, request.block_offset, request.block_length

        # Check if the block is already downloaded
        if self.pieces_manager.is_block_downloaded(piece_index, block_offset):
            return

        block = self.pieces_manager.get_block(piece_index, block_offset, block_length)
        if block:
            peer.send_to_peer(message.Piece(piece_index, block_offset, block_length, block).to_bytes())

    def peers_bitfield(self, bitfield=None):
        # Update pieces by peer
        for i in range(len(self.pieces_by_peer)):
            if bitfield[i] == 1 and peer not in self.pieces_by_peer[i][1]:
                self.pieces_by_peer[i][1].append(peer)

    def add_request_to_queue(self, peer, piece_index, block_offset, block_length):
        # Add a request to the peer's queue
        if peer not in self.request_queues:
            self.request_queues[peer] = []
        self.request_queues[peer].append((piece_index, block_offset, block_length))

        # Track globally requested blocks
        self.global_requested_blocks[(piece_index, block_offset)] = peer

    def get_peer_by_socket(self, socket):
        for peer in self.peers:
            if socket == peer.socket:
                return peer
        raise Exception("Peer not present in peer_list")

    def remove_peer(self, peer):
        if peer in self.peers:
            try:
                peer.socket.close()
            except Exception:
                pass
            self.peers.remove(peer)
            # Remove peer from global tracking
            self.global_requested_blocks = {k: v for k, v in self.global_requested_blocks.items() if v != peer}

    def has_unchoked_peers(self):
        return any(peer.is_unchoked() for peer in self.peers)

class Run(object):
    def start(self):
        peers_dict = self.tracker.get_peers_from_trackers()
        self.peers_manager.add_peers(peers_dict.values())

        print("PEER - Downloading")  # Print the required output

        while not self.pieces_manager.all_pieces_completed():
            if not self.peers_manager.has_unchoked_peers():
                time.sleep(1)
                logging.info("No unchoked peers")
                continue

            for piece in self.pieces_manager.pieces:
                index = piece.piece_index

                if self.pieces_manager.pieces[index].is_full:
                    continue

                peer = self.peers_manager.get_random_peer_having_piece(index)
                if not peer:
                    continue

                self.pieces_manager.pieces[index].update_block_status()

                data = self.pieces_manager.pieces[index].get_empty_block()
                if not data:
                    continue

                piece_index, block_offset, block_length = data
                piece_data = message.Request(piece_index, block_offset, block_length).to_bytes()
                peer.send_to_peer(piece_data)

            self.display_progression()

            time.sleep(0.1)

        logging.info("File(s) downloaded successfully.")
        self.display_progression()

        self.start_seeding()

        self._exit_threads()

    def start_seeding(self):
        logging.info("Starting seeding...")
        while True:
            time.sleep(10)  # Keep the client running to seed the file