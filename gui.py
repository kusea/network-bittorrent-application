import sys
import threading
import logging
import os
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QDialog, \
    QDialogButtonBox, QMessageBox, QListWidget
from tracker import Tracker  # Import Tracker class from tracker.py
from peer import Peer


class TrackerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("P2P Network Tracker")
        self.setGeometry(100, 100, 400, 200)

        # GUI elements
        layout = QVBoxLayout()

        self.connect_button = QPushButton("Connect to Tracker")
        self.connect_button.clicked.connect(self.connect_to_tracker)
        layout.addWidget(self.connect_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_tracker)
        layout.addWidget(self.stop_button)

        self.add_peer_button = QPushButton("Add Peer")
        self.add_peer_button.setEnabled(False)  # Initially disabled
        self.add_peer_button.clicked.connect(self.add_peer)
        layout.addWidget(self.add_peer_button)

        self.tracker_thread = None

        self.setLayout(layout)

        # Store references to peer windows
        self.peer_windows = []

    def connect_to_tracker(self):
        try:
            # Start the tracker in a separate thread so that the GUI doesn't freeze
            self.tracker_thread = threading.Thread(target=self.start_tracker, daemon=True)
            self.tracker_thread.start()
            self.show_message("Success", "Connected to Tracker!")
            self.add_peer_button.setEnabled(True)  # Enable Add Peer button after successful connection
        except Exception as e:
            self.show_message("Error", f"Failed to connect to tracker: {e}")

    def start_tracker(self):
        try:
            # Create and start the tracker
            manager = Tracker()
            manager.run()
        except Exception as e:
            print(f"Error starting tracker: {e}")

    def stop_tracker(self):
        try:
            # Stop the tracker and close the GUI when the user presses stop
            self.close()  # Close the Tracker window
            os._exit(0)  # Exit the process immediately, mimicking tracker.py behavior
        except Exception as e:
            print(f"Error while stopping tracker: {e}")

    def show_message(self, title, message):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def add_peer(self):
        # Open a dialog to add a new peer
        add_peer_dialog = AddPeerDialog(self)
        if add_peer_dialog.exec_():
            port_no, name = add_peer_dialog.get_input()
            if port_no and name:
                try:
                    # Set up logging for the peer
                    logging.basicConfig(filename="logs/" + name + '.log', encoding='utf-8', level=logging.DEBUG)

                    # Create the Peer object and run it
                    p = Peer(port_no, name)
                    p.connect_manager()

                    # Start the receive thread for the peer
                    receive_thread = threading.Thread(target=p.receive)
                    receive_thread.daemon = True  # Ensures the thread exits when the main program exits
                    receive_thread.start()

                    # Open the Peer window with info without closing the Tracker window
                    peer_window = PeerGUI(name, port_no)
                    peer_window.show()

                    # Store the reference to the peer window in the list
                    self.peer_windows.append(peer_window)
                except Exception as e:
                    self.show_message("Error", f"Failed to start peer: {e}")


class AddPeerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Add Peer")
        self.setGeometry(150, 150, 300, 150)

        layout = QVBoxLayout()

        # Port Number and Name Input
        port_label = QLabel("Enter Port Number:")
        self.port_entry = QLineEdit(self)
        layout.addWidget(port_label)
        layout.addWidget(self.port_entry)

        name_label = QLabel("Enter Your Name:")
        self.name_entry = QLineEdit(self)
        layout.addWidget(name_label)
        layout.addWidget(self.name_entry)

        # Dialog Buttons (OK and Cancel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_input(self):
        port_no = self.port_entry.text()
        name = self.name_entry.text()
        return int(port_no) if port_no.isdigit() else None, name


class PeerGUI(QWidget):
    def __init__(self, name, port_no):
        super().__init__()
        self.setWindowTitle(f"Peer - {name}")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        # Display the peer info
        self.peer_info_label = QLabel(f"Connected Peer: {name} on Port {port_no}")
        layout.addWidget(self.peer_info_label)

        # List of connected peers
        self.peer_list_label = QLabel("Peers Connected to Tracker:")
        layout.addWidget(self.peer_list_label)

        self.peer_list = QListWidget(self)
        self.peer_list.addItem(name)  # Add the current peer to the list of connected peers
        layout.addWidget(self.peer_list)

        # Download and Upload buttons
        self.download_button = QPushButton("Download Torrent File")
        self.upload_button = QPushButton("Upload Torrent File")
        layout.addWidget(self.download_button)
        layout.addWidget(self.upload_button)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    tracker_gui = TrackerGUI()
    tracker_gui.show()

    sys.exit(app.exec_())