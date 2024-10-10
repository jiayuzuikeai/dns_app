import socket
import threading
from flask import Flask, request, jsonify
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
dns_records = {}
app = Flask(__name__)
       
# Start the UDP server for DNS registration and queries
def start_udp_server():
    try:
        logging.debug("Attempting to start UDP server...") 
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logging.debug("UDP socket created successfully.")
        
        server_socket.bind(("0.0.0.0", 53533))
        print("Authoritative Server successfully started, listening on UDP port 53533")
    except Exception as e:
        print("Failed to start Authoritative Server: {}".format(e))
        return

    # Main loop for receiving messages
    while True:
        try:
            # Receive message from client
            print("Waiting for incoming messages...")
            data, addr = server_socket.recvfrom(4096)
            message = data.decode().strip()
            print("Received message from {}: {}".format(addr, message))

            # Split the message into lines
            lines = message.split("\n")

            # Check if it's a DNS Registration request
            if len(lines) >= 3 and lines[0] == "TYPE=A" and "VALUE=" in lines[2]:
                # Handling a registration request
                hostname = lines[1].split("=")[1].strip()
                ip_address = lines[2].split("=")[1].strip()

                # Register the hostname with the provided IP address
                dns_records[hostname] = ip_address
                print("Registered DNS record: {} -> {}".format(hostname, ip_address))

                # Send confirmation response to client
                server_socket.sendto(b"Registration successful", addr)

            # Check if it's a DNS Query request
            elif len(lines) == 2 and lines[0] == "TYPE=A":
                # Handling a query request
                hostname = lines[1].split("=")[1].strip()

                # If the hostname is registered, respond with its IP address
                if hostname in dns_records:
                    response = "TYPE=A\nNAME={}\nVALUE={}\nTTL=10\n".format(hostname, dns_records[hostname])
                    server_socket.sendto(response.encode(), addr)
                    print("Sent response to {}: {}".format(addr, response))
                else:
                    response = "TYPE=A\nNAME={}\nVALUE=\nTTL=10\n".format(hostname)
                    server_socket.sendto(response.encode(), addr)
                    print("No record found for hostname: {}. Sent empty response.".format(hostname))

            else:
                # If message format doesn't match either registration or query, print an error
                print("Invalid message format received.")

        except Exception as e:
            print("Error handling request: {}".format(e))

# Flask API for handling registration via HTTP
app = Flask(__name__)

@app.route('/register', methods=['POST'])
def register():
    # Extract data from the request
    data = request.get_json()

    if not data:
        return "Bad Request: Missing JSON body", 400

    # Extract hostname and IP from the JSON
    hostname = data.get('hostname')
    ip = data.get('ip')
    as_ip = data.get('as_ip')
    as_port = data.get('as_port')

    # Ensure all necessary fields are provided
    if not hostname or not ip or not as_ip or not as_port:
        return "Bad Request: Missing required parameters", 400

    # Register the hostname and IP in the DNS records
    dns_records[hostname] = ip

    # Send registration to authoritative server via UDP
    message = "TYPE=A\nNAME={}\nVALUE={}\nTTL=10\n".format(hostname, ip).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(message, (as_ip, int(as_port)))
        print("Registered hostname {} with IP {} to AS {}:{}".format(hostname, ip, as_ip, as_port))
    except Exception as e:
        return "Failed to send registration to authoritative server: {}".format(str(e)), 500

    return jsonify({"message": "Hostname {} registered successfully".format(hostname)}), 201

# Run both servers: UDP in a separate thread, Flask in the main thread
if __name__ == "__main__":
    # Start the UDP server in a separate thread
    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    udp_thread.start()

    # Start the Flask HTTP server
    app.run(port=8080, host='0.0.0.0')

