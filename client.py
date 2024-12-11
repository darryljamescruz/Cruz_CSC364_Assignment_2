import socket
import struct
import sys
import threading
import time

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

# Track current user input and keep-alive state
current_input = ""
last_packet_time = time.time()  # Track the last time a packet was sent

def send_packet(message_type, content=b''):
    """Send a structured packet to the server."""
    global last_packet_time
    packet = struct.pack("!I", message_type) + content
    client_socket.sendto(packet, ADDR)
    last_packet_time = time.time()

def display_message(message):
    """Handle displaying server messages while preserving user input."""
    global current_input
    # Clear the current input line
    sys.stdout.write("\r" + " " * 80 + "\r")
    # Print the server message
    print(message)
    # Redisplay the prompt and user's current input
    sys.stdout.write(f"> {current_input}")
    sys.stdout.flush()
    
def keep_alive():
    """Send a KEEP_ALIVE packet every 60 seconds if no other packets are sent."""
    while True:
        time.sleep(60)
        if time.time() - last_packet_time >= 60:
            send_packet(KEEP_ALIVE, username.ljust(32).encode())

def handle_command(command):
    """Process user commands."""
    global active_channel, current_input
    current_input = ""  # Clear input after processing
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
    elif command.startswith("/leave"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            print("Error: Channel name required for /leave.")
            return
        channel_name = parts[1].strip()
        send_packet(LEAVE, username.ljust(32).encode() + channel_name.ljust(32).encode())
        if active_channel == channel_name:
            active_channel = "Common"  # Default back to "Common"
        joined_channels.discard(channel_name)
        print(f"You have left channel: {channel_name}.")
    elif command.startswith("/say"):
        message = command[5:].strip()
        if not message:
            print("Error: Message cannot be empty.")
            return
        send_packet(SAY, active_channel.ljust(32).encode() + username.ljust(32).encode() + message.ljust(64).encode())
    elif command.startswith("/switch"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            print("Error: Channel name required for /switch.")
            return
        channel_name = parts[1].strip()
        if channel_name in joined_channels:
            active_channel = channel_name
            print(f"Switched to channel: {channel_name}")
        else:
            print(f"Error: You have not joined the channel '{channel_name}'.")
    elif command.startswith("/who"):
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            print("Error: Channel name required for /who.")
            return
        channel_name = parts[1].strip()
        send_packet(WHO, channel_name.ljust(32).encode())
    elif command.startswith("/help"):
        print("""
Available Commands:
/exit             - Logout and exit.
/list             - List all available channels.
/join [channel]   - Join a specified channel.
/leave [channel]  - Leave a specified channel.
/say [message]    - Send a message to the active channel.
/switch [channel] - Switch to a joined channel.
/who [channel]    - List users in a specified channel.
/help             - Display this help message.
        """)
    else:
        print("Unknown or malformed command.")

def receive_messages():
    """Receive and print messages from the server."""
    while True:
        data, _ = client_socket.recvfrom(1024)
        display_message(f"Message from server: {data.decode()}")

def main():
    """Start the client."""
    send_packet(LOGIN, username.ljust(32).encode())
    threading.Thread(target=receive_messages, daemon=True).start()
    print(f"Logged in as {username}. Type /help for commands.")
    while True:
        global current_input
        current_input = input("> ").strip()
        handle_command(current_input)

if __name__ == "__main__":
    main()