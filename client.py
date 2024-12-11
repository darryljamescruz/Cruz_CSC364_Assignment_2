import socket
import struct
import threading
import sys
import time

# constants for message types
LOGIN, LOGOUT, JOIN, LEAVE, SAY, LIST, WHO, KEEP_ALIVE, ERROR = range(9)

HOST = 'localhost'
PORT = 5000
ADDR = (HOST, PORT)

username = input("Enter your username: ").strip()

# Socket for communication
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Client state
joined_channels = {"Common"}
active_channel = "Common"
current_input = ""  # Track the current input text


def send_packet(message_type, content=b''):
    """Send a structured packet to the server."""
    print(f"Sending packet: type={message_type}, content={content}")
    packet = struct.pack("!I", message_type) + content
    client_socket.sendto(packet, ADDR)
    print("Packet sent.")


def receive_messages():
    """Receive and display messages from the server."""
    global current_input
    while True:
        data, _ = client_socket.recvfrom(1024)
        msg_type = struct.unpack("!I", data[:4])[0]
        if msg_type == SAY:
            channel = data[4:36].strip().decode()
            user = data[36:68].strip().decode()
            text = data[68:132].strip().decode()
            # Erase the current input
            sys.stdout.write('\r' + ' ' * 80 + '\r')
            print(f"[{channel}][{user}]: {text}")
            # Redisplay the prompt with the current input
            sys.stdout.write(f"> {current_input}")
            sys.stdout.flush()


def start_keep_alive():
    """Send a Keep Alive packet every minute."""
    while True:
        time.sleep(60)
        send_packet(KEEP_ALIVE, username.ljust(32).encode())


def handle_command(command):
    """Handle user commands."""
    global active_channel, current_input
    current_input = ""  # Clear input after processing
    if command.startswith("/exit"):
        send_packet(LOGOUT, username.ljust(32).encode())
        sys.exit()
    elif command.startswith("/list"):
        send_packet(LIST)
    elif command.startswith("/join"):
        channel_name = command.split(maxsplit=1)[1].strip()
        send_packet(JOIN, username.ljust(32).encode() + channel_name.ljust(32).encode())
        joined_channels.add(channel_name)
        active_channel = channel_name
    elif command.startswith("/leave"):
        channel_name = command.split(maxsplit=1)[1].strip()
        send_packet(LEAVE, username.ljust(32).encode() + channel_name.ljust(32).encode())
        joined_channels.discard(channel_name)
        if active_channel == channel_name:
            active_channel = "Common"
    elif command.startswith("/switch"):
        channel_name = command.split(maxsplit=1)[1].strip()
        if channel_name in joined_channels:
            active_channel = channel_name
            print(f"Switched to channel: {channel_name}")
        else:
            print(f"Error: You have not joined the channel '{channel_name}'.")
    elif command.startswith("/who"):
        channel_name = command.split(maxsplit=1)[1].strip()
        send_packet(WHO, channel_name.ljust(32).encode())
    elif not command.startswith("/"):
        send_packet(SAY, active_channel.ljust(32).encode() + username.ljust(32).encode() + command.ljust(64).encode())


def input_handler():
    """Handle user input."""
    global current_input
    while True:
        print("Waiting for user input...")
        current_input = input("> ")
        print(f"User input: {current_input}")
        handle_command(current_input)


def main():
    """Main client program."""
    send_packet(LOGIN, username.ljust(32).encode())
    threading.Thread(target=receive_messages, daemon=True).start()
    threading.Thread(target=start_keep_alive, daemon=True).start()
    print("Client script is running...")
    input_handler()


if __name__ == "__main__":
    main()