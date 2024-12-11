import socket
import struct
import threading

# Message types
LOGIN, LOGOUT, LIST, JOIN, SAY, WHO, LEAVE, KEEP_ALIVE = range(8)

HOST = "localhost"
PORT = 5000
ADDR = (HOST, PORT)

# Server state
users = {}  # username -> address
channels = {"Common": set()}

# Create UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(ADDR)

def send_packet(address, message_type, content=b''):
    """Send a structured packet to a client."""
    packet = struct.pack("!I", message_type) + content
    server_socket.sendto(packet, address)

def process_request(data, address):
    """Process a single client request."""
    if len(data) < 4:
        print(f"Invalid packet from {address}: {data}")
        return

    message_type = struct.unpack("!I", data[:4])[0]
    if message_type == LOGIN and len(data) >= 36:
        username = data[4:36].strip().decode()
        users[username] = address
        channels["Common"].add(username)
        print(f"User {username} logged in.")
    elif message_type == LIST:
        channel_list = "\n".join(channels.keys()).encode()
        send_packet(address, LIST, channel_list)
    elif message_type == JOIN and len(data) >= 68:
        username = data[4:36].strip().decode()
        channel_name = data[36:68].strip().decode()
        channels.setdefault(channel_name, set()).add(username)
        print(f"User {username} joined channel {channel_name}.")
    else:
        print(f"Unknown message type: {message_type}")

def server_main():
    """Start the server."""
    print("Server is running...")
    while True:
        data, address = server_socket.recvfrom(1024)
        process_request(data, address)

if __name__ == "__main__":
    server_main()