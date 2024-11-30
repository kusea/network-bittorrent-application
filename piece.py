import os

class TorrentPieceManager:
    def __init__(self, torrent_file_path, total_pieces, download_dir):
        self.torrent_file_path = torrent_file_path
        self.total_pieces = total_pieces
        self.download_dir = download_dir
        self.downloaded_pieces = set()  # To track downloaded pieces

    def is_piece_downloaded(self, piece_index):
        """
        Check if the piece has already been downloaded by checking its existence on disk.
        """
        # For simplicity, we'll assume each piece has a corresponding file in the download directory
        piece_file_path = os.path.join(self.download_dir, f"piece_{piece_index}")
        return os.path.exists(piece_file_path)

    def mark_piece_downloaded(self, piece_index):
        """
        Mark a piece as downloaded.
        """
        self.downloaded_pieces.add(piece_index)

    def get_next_piece(self):
        """
        Get the index of the next piece that needs to be downloaded.
        If a piece is already downloaded, skip it.
        """
        for piece_index in range(self.total_pieces):
            if not self.is_piece_downloaded(piece_index):
                return piece_index
        return None  # All pieces downloaded