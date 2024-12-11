import socket
import struct
import sys
import threading

# Message types
LOGIN, LOGOUT, LIST, JOIN, SAY, WHO, LEAVE, KEEP_ALIVE = range(8)

HOST = "localhost"
PORT = 5000
ADDR = (HOST, PORT)

username = input("Enter your username: ").strip()
joined_channels = {"Common"}
active_channel = "Common"

# Create UDP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_packet(message_type, content=b''):
    """Send a structured packet to the server."""
    packet = struct.pack("!I", message_type) + content
    client_socket.sendto(packet, ADDR)

def handle_command(command):
    """Process user commands."""
    global active_channel
    if command.startswith("/exit"):
        send_packet(LOGOUT, username.ljust(32).encode())
        sys.exit("Logged out.")
    elif command.startswith("/list"):
        send_packet(LIST)
    elif command.startswith("/join"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            print("Error: Channel name required for /join.")
            return
        channel_name = parts[1].strip()
        send_packet(JOIN, username.ljust(32).encode() + channel_name.ljust(32).encode())
        joined_channels.add(channel_name)
        active_channel = channel_name
    elif command.startswith("/say"):
        message = command[5:].strip()
        if not message:
            print("Error: Message cannot be empty.")
            return
        send_packet(SAY,  active_channel.ljust(32).encode() + username.ljust(32).encode() + message.ljust(64).encode())
    elif command.startswith("/switch"):
        pass
    elif command.startswith("/who"):
        pass
    else:
        print("Unknown or malformed command.")

def receive_messages():
    """Receive and print messages from the server."""
    while True:
        data, _ = client_socket.recvfrom(1024)
        print(f"Message from server: {data.decode()}")

def main():
    """Start the client."""
    send_packet(LOGIN, username.ljust(32).encode())
    threading.Thread(target=receive_messages, daemon=True).start()
    print(f"Logged in as {username}. Type /exit to quit.")
    while True:
        command = input("> ").strip()
        handle_command(command)

if __name__ == "__main__":
    main()