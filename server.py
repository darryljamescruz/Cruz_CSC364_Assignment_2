import socket
import struct
import sys
import time
import threading

# Message types
LOGIN, LOGOUT, LIST, JOIN, SAY, WHO, LEAVE, KEEP_ALIVE = range(8)

HOST = "localhost"
PORT = 5000
ADDR = (HOST, PORT)

# Server state
users = {}  # username -> (address, last_active_time)
channels = {"Common": set()}  # channel_name -> set of usernames

# Create UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(ADDR)


def send_packet(address, message_type, content=b''):
    """Send a structured packet to a client."""
    packet = struct.pack("!I", message_type) + content
    server_socket.sendto(packet, address)


def server_command_listener():
    """Listen for server-side commands to control the server."""
    while True:
        command = input().strip().lower()
        if command == "quit":
            print("Shutting down the server...")
            notify_clients_of_shutdown()
            server_socket.close()
            sys.exit(0)  # Exit the server program
            
            
def timeout_users():
    """Periodically check for inactive users and log them out."""
    while True:
        time.sleep(120)  # Check every 2 minutes
        current_time = time.time()
        for username, (address, last_active) in list(users.items()):
            if current_time - last_active > 120:  # User inactive for 2 minutes
                print(f"User {username} timed out.")
                handle_logout(username)


def handle_logout(username):
    """Handle user logout."""
    if username in users:
        address = users[username][0]
        send_packet(address, LOGOUT, b"Server: You have been disconnected due to inactivity.")
        del users[username]
        for channel_name in list(channels.keys()):
            channels[channel_name].discard(username)
            if not channels[channel_name]:  # Remove empty channel
                del channels[channel_name]
        print(f"User {username} logged out.")
        
        
def notify_clients_of_shutdown():
    """Notify all connected clients about the server shutdown."""
    for username, (address, _) in users.items():
        send_packet(address, LOGOUT, b"Server is shutting down. You have been disconnected.")
    print("All clients have been notified of server shutdown.")


def process_request(data, address):
    """Process a single client request."""
    if len(data) < 4:
        print(f"Invalid packet from {address}: {data}")
        return

    message_type = struct.unpack("!I", data[:4])[0]
    username = data[4:36].strip().decode()

    # Handle LOGIN
    if message_type == LOGIN and len(data) >= 36:
        users[username] = (address, time.time())
        channels["Common"].add(username)
        print(f"User {username} logged in.")

    # Handle LOGOUT
    elif message_type == LOGOUT:
        handle_logout(username)

    # Handle LIST (list all channels)
    elif message_type == LIST:
        channel_list = "\n".join(channels.keys()).encode()
        send_packet(address, LIST, channel_list)

    # Handle JOIN (join a channel)
    elif message_type == JOIN and len(data) >= 68:
        channel_name = data[36:68].strip().decode()
        channels.setdefault(channel_name, set()).add(username)
        print(f"User {username} joined channel {channel_name}.")

    # Handle LEAVE (leave a channel)
    elif message_type == LEAVE and len(data) >= 68:
        channel_name = data[36:68].strip().decode()
        if channel_name in channels:
            channels[channel_name].discard(username)
            if not channels[channel_name]:  # Remove empty channel
                del channels[channel_name]
            print(f"User {username} left channel {channel_name}.")

    # Handle SAY (send a message to a channel)
    elif message_type == SAY and len(data) >= 132:
        channel_name = data[4:36].strip().decode()  # Extract channel name correctly
        username = data[36:68].strip().decode()     # Extract username correctly
        message = data[68:132].strip().decode()     # Extract message content
        if channel_name in channels:
            for user in channels[channel_name]:
                if user in users:
                    send_packet(users[user][0], SAY, f"[{channel_name}][{username}]: {message}".encode())
            print(f"[{channel_name}][{username}]: {message}")

    # Handle WHO (list users in a channel)
    elif message_type == WHO and len(data) >= 68:
        channel_name = data[36:68].strip().decode()
        if channel_name in channels:
            if username in channels[channel_name]:
                user_list = ", ".join(channels[channel_name]).encode()
                send_packet(address, WHO, f"Users in {channel_name}: {user_list.decode()}".encode())
            else:
                send_packet(address, WHO, f"Error: You are not in the channel '{channel_name}'.".encode())
        else:
            send_packet(address, WHO, f"Error: Channel '{channel_name}' not found.".encode())
            
    # Handle KEEP_ALIVE
    elif message_type == KEEP_ALIVE and len(data) >= 36:
        if username in users:
            users[username] = (address, time.time())  # Update activity time
            print(f"Keep Alive received from {username}.")
            
# Handle users who were timed out and send a logout packet.
    if username not in users and message_type != LOGIN:
        print(f"Ignoring packet from inactive user: {username}")
        send_packet(address, LOGOUT, b"Error: You have been disconnected. Please log in again.")
        return

    # Update activity time for all valid packets
    if username in users:
        users[username] = (address, time.time())


def server_main():
    """Start the server."""
    threading.Thread(target=timeout_users, daemon=True).start()
    threading.Thread(target=server_command_listener, daemon=True).start()
    print("Server is running... Type 'quit' to shut down.")
    while True:
        try:
            data, address = server_socket.recvfrom(1024)
            process_request(data, address)
        except OSError:
            break  # Exit the loop if the socket is closed


if __name__ == "__main__":
    server_main()