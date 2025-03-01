import socket
import struct
import sys
import time
import threading

# Message types
LOGIN, LOGOUT, LIST, JOIN, SAY, WHO, LEAVE, KEEP_ALIVE = range(8)
SHUTDOWN = 8

HOST = "localhost"
PORT = 5000
ADDR = (HOST, PORT)

# Server state
users = {}  # username -> (address, last_active_time)
channels = {"Common": set()}  # channel_name -> set of usernames
inactive_users = set()  # Track usernames of inactive users

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
        inactive_users.discard(username)  # Remove from inactive users
        for channel_name in list(channels.keys()):
            channels[channel_name].discard(username)
            if not channels[channel_name]:  # Remove empty channel
                del channels[channel_name]
        print(f"User {username} logged out.")


def notify_clients_of_shutdown():
    """Notify all connected clients about the server shutdown."""
    for username, (address, _) in users.items():
        send_packet(address, SHUTDOWN, b"Server is shutting down. Goodbye!")
    inactive_users.clear()  # Clear inactive users
    print("All clients have been notified of server shutdown.")


def process_request(data, address):
    """Process a single client request."""
    global inactive_users
    if len(data) < 4:
        print(f"Invalid packet from {address}: {data}")
        return

    message_type = struct.unpack("!I", data[:4])[0]
    
    # Debugging logs for packet parsing
    print(f"Packet received: type={message_type}, data={data}")
    
    username = None # Default to None

    # Handle LOGIN
    if message_type == LOGIN and len(data) >= 36:
        username = data[4:36].strip().decode()
        users[username] = (address, time.time())  # Update last_active_time on login
        channels["Common"].add(username)
        print(f"User {username} logged in.")
        send_packet(address, LOGIN, b"Welcome to the server!")
        return

    # Extract username for all other message types dynamically
    if message_type in (LOGOUT, JOIN, LEAVE, KEEP_ALIVE):
        username = data[4:36].strip().decode()
        
    # Special case for SAY
    if message_type == SAY and len(data) >= 132:
        channel_name = data[4:36].strip().decode()
        username = data[36:68].strip().decode()  # SAY packet username is in a different position
        message = data[68:132].strip().decode()
        
    # Check if username was properly extracted
    if username is None and message_type not in {LIST, WHO}:
        print(f"Error: Could not extract username for message type {message_type}.")
        return

    # Ignore packets from inactive users
    if username is None or username not in users:
        if message_type not in {LIST, WHO}:  # Skip username checks for LIST and WHO
            if username and username not in inactive_users:
                print(f"Ignoring packet from inactive user: {username}")
                inactive_users.add(username)  # Add user to inactive_users
            send_packet(address, LOGOUT, b"Error: You have been disconnected. Please log in again.")
            return
    
    if username:
        inactive_users.discard(username)  # Mark user as active again

    # Handle LOGOUT
    if message_type == LOGOUT:
        handle_logout(username)

    # Handle LIST (list all channels)
    elif message_type == LIST:
        # Construct the list of channels, padded to 32 bytes each
        channel_list = "Existing channels:\n" + "\n ".join(channels.keys())
        send_packet(address, LIST, channel_list.encode())
        print(f"Processed LIST request. Sent channels: {channels.keys()}")

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
        if channel_name in channels:
            for user in channels[channel_name]:
                if user in users:
                    send_packet(users[user][0], SAY, f"[{channel_name}][{username}]: {message}".encode())
            print(f"[{channel_name}][{username}]: {message}")
        else:
            print(f"Error: Channel '{channel_name}' not found.")

    # Handle WHO (list users in a channel)
    elif message_type == WHO and len(data) >= 36:
        channel_name = data[4:36].strip().decode()
        if channel_name in channels:
            # Get users in the channel
            user_list = ", ".join(channels[channel_name])
            response = f"Users on channel {channel_name}:\n {user_list}"
            send_packet(address, WHO, response.encode())
            print(f"Processed WHO request for channel {channel_name}. Users: {user_list}")
        else:
            error_msg = f"Error: Channel '{channel_name}' not found."
            send_packet(address, WHO, error_msg.encode())
            print(f"WHO request error: {error_msg}")

    # Handle KEEP_ALIVE
    elif message_type == KEEP_ALIVE and len(data) >= 36:
        if username in users:
            users[username] = (address, time.time())  # Update activity time
            print(f"Keep Alive received from {username}.")
        else:
            print(f"Keep Alive ignored from inactive user: {username}")

    # Catch-all for unexpected message types
    else:
        print(f"Unexpected message type: {message_type} from {username} at {address}")

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