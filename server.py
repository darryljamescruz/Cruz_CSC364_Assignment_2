# server.py

# imports
import socket
import struct
import threading
import time

# server config
HOST = 'localhost'
PORT = 5000
ADDR = (HOST,PORT)

# constants for message types
LOGIN = 0
LOGOUT = 1
JOIN = 2
LEAVE = 3
SAY = 4
LIST = 5
WHO = 6
KEEP_ALIVE = 7
ERROR = 3       # send to client if an error occurs

# dictionaries to keep users and channels structured
users = {}      # username -> (address, last_active)
channels = {}   # channel_name -> set of usernames

# server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(ADDR)

def send_packet(address, message_type, content=b''):
    """sends a structured packet to a client."""
    packet = struct.pack("!I", message_type) + content
    server_socket.sendto(packet, address)
    
def handle_keep_alive():
    """periodicaly check for inactive users and remove them."""
    pass

def handle_login(username, address):
    """handles user login."""
    pass

def handle_logout(username):
    """handle user logout."""
    if username in users:
        del users[username]
        for channel in channels.values():
            channel.discard(username)
        print(f"Username {username} logged out.")
