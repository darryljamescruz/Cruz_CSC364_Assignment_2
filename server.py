# server.py

import socket
import struct
import threading
import time

# server configuration
HOST = 'localhost'
PORT = 5000
ADDR = (HOST, PORT)

# constants for message types
LOGIN, LOGOUT, JOIN, LEAVE, SAY, LIST, WHO, KEEP_ALIVE, ERROR = range(9)

# dictionaries for users and channels
users = {}  # username -> (address, last_active)
channels = {}  # channel_name -> set of usernames

# server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(ADDR)

def send_packet(address, message_type, content=b''):
    """Send a structured packet to a client."""
    packet = struct.pack("!I", message_type) + content
    server_socket.sendto(packet, address)

def handle_keep_alive():
    """Periodically check for inactive users and remove them."""
    while True:
        time.sleep(120)
        current_time = time.time()
        for user, (address, last_active) in list(users.items()):
            if current_time - last_active > 120:
                print(f"User {user} timed out.")
                handle_logout(user)

def handle_login(username, address):
    """Handle user login."""
    if username in users:
        send_packet(address, ERROR, b"Username already taken.".ljust(64))
        return
    users[username] = (address, time.time())
    channels.setdefault("Common", set()).add(username)
    print(f"User {username} logged in.")
    send_packet(address, LIST, struct.pack("!I", len(channels)) + b''.join(name.ljust(32).encode() for name in channels))

def handle_logout(username):
    """Handle user logout."""
    if username in users:
        del users[username]
        for channel in channels.values():
            channel.discard(username)
        print(f"User {username} logged out.")

def handle_join(username, channel_name):
    """Add user to the specified channel."""
    print(f"Handling join: username={username}, channel={channel_name}")
    channels.setdefault(channel_name, set()).add(username)
    print(f"User {username} joined channel {channel_name}")

def handle_leave(username, channel_name):
    """Remove user from the specified channel."""
    if channel_name in channels and username in channels[channel_name]:
        channels[channel_name].remove(username)
        if not channels[channel_name]:  # delete empty channel
            del channels[channel_name]
        print(f"User {username} left channel {channel_name}")

def handle_say(username, channel_name, text):
    """Broadcast a message to all users in a channel."""
    if channel_name in channels:
        for user in channels[channel_name]:
            user_address = users[user][0]
            send_packet(user_address, SAY, channel_name.ljust(32).encode() + username.ljust(32).encode() + text.ljust(64).encode())
        print(f"[{channel_name}][{username}]: {text}")

def handle_list(address):
    """Send a list of channels to the client."""
    content = struct.pack("!I", len(channels)) + b''.join(name.ljust(32).encode() for name in channels)
    send_packet(address, LIST, content)

def handle_who(address, channel_name):
    """Send a list of users in a channel to the client."""
    if channel_name in channels:
        user_list = b''.join(user.ljust(32).encode() for user in channels[channel_name])
        content = struct.pack("!I", len(channels[channel_name])) + channel_name.ljust(32).encode() + user_list
        send_packet(address, WHO, content)

def process_request(data, address):
    """Process a single request from a client."""
    if len(data) < 4:
        print(f"Invalid packet received from {address}")
        return

    message_type = struct.unpack("!I", data[:4])[0]
    
    #try block included for error handling
    try:
        if message_type == LOGIN and len(data) >= 36:
            username = data[4:36].strip().decode()
            handle_login(username, address)
        elif message_type == LOGOUT:
            username = data[4:36].strip().decode()
            handle_logout(username)
        elif message_type == JOIN and len(data) >= 68:
            username = data[4:36].strip().decode()
            channel_name = data[36:68].strip().decode()
            handle_join(username, channel_name)
        elif message_type == LEAVE and len(data) >= 68:
            username = data[4:36].strip().decode()
            channel_name = data[36:68].strip().decode()
            handle_leave(username, channel_name)
        elif message_type == SAY and len(data) >= 132:
            username = data[4:36].strip().decode()
            channel_name = data[36:68].strip().decode()
            text = data[68:132].strip().decode()
            handle_say(username, channel_name, text)
        elif message_type == LIST:
            handle_list(address)
        elif message_type == WHO and len(data) >= 36:
            channel_name = data[4:36].strip().decode()
            handle_who(address, channel_name)
        elif message_type == KEEP_ALIVE:
            username = data[4:36].strip().decode()
            if username in users:
                users[username] = (users[username][0], time.time())
        else:
            print(f"Unknown message type: {message_type}")
    except Exception as e:
        print(f"Error processing packet: {e}")

def start_server():
    """Start the server to receive and process client messages."""
    threading.Thread(target=handle_keep_alive, daemon=True).start()
    print("Server is running...")

    while True:
        data, address = server_socket.recvfrom(1024)
        process_request(data, address)

if __name__ == "__main__":
    start_server()