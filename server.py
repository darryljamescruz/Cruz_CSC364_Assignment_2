import socket
import struct

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
    elif message_type == LEAVE and len(data) >= 68:
        username = data[4:36].strip().decode()
        channel_name = data[36:68].strip().decode()
        if channel_name in channels:
            channels[channel_name].discard(username)
            if not channels[channel_name]:  # Remove empty channel
                del channels[channel_name]
            print(f"User {username} left channel {channel_name}.")
    elif message_type == SAY and len(data) >= 132:
        channel_name = data[4:36].strip().decode()
        username = data[36:68].strip().decode()
        message = data[68:132].strip().decode()
        if channel_name in channels:
            for user in channels[channel_name]:
                if user in users:
                    send_packet(users[user], SAY, f"[{channel_name}][{username}]: {message}".encode())
            print(f"[{channel_name}][{username}]: {message}")
    elif message_type == WHO and len(data) >= 36:
        channel_name = data[4:36].strip().decode()
        if channel_name in channels:
            user_list = ", ".join(channels[channel_name]).encode()
            send_packet(address, WHO, f"Active users: {user_list.decode()}".encode())
        else:
            send_packet(address, WHO, b"Error: Channel not found.")
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