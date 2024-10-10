from flask import Flask, request, jsonify
import requests
import socket
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/fibonacci', methods=['GET'])
def fibonacci_proxy():
    hostname = request.args.get('hostname')
    fs_port = request.args.get('fs_port')
    number = request.args.get('number')
    as_ip = request.args.get('as_ip')
    as_port = request.args.get('as_port')
    
    logging.debug("Received request with parameters: hostname={}, fs_port={}, number={}, as_ip={}, as_port={}".format(hostname, fs_port, number, as_ip, as_port))

        # Validate parameters
    if not all([hostname, fs_port, number, as_ip, as_port]):
        return "Missing parameters", 400

    try:
        as_port = int(as_port)
        fs_port = int(fs_port)
        number = int(number)
    except ValueError:
        return "Invalid number or port", 400

    # Perform DNS lookup via UDP
    query_message = "TYPE=A\nNAME={}\n".format(hostname).encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.sendto(query_message, (as_ip, as_port))
        logging.debug("Sent DNS query to {}:{}".format(as_ip, as_port))

        # Receive the response from Authoritative Server
        sock.settimeout(5)
        data, _ = sock.recvfrom(1024)
        logging.debug("Received DNS response: {}".format(data.decode()))

    except socket.timeout:
        logging.error("DNS query timeout")
        return "DNS query timeout", 500
    except socket.error as e:
        logging.error("Socket error: {}".format(e))
        return "Socket error occurred", 500
    finally:
        sock.close()

    # Parse response to extract IP address
    response_lines = data.decode().split('\n')
    ip_address = None
    for line in response_lines:
        if line.startswith("VALUE="):
            ip_address = line.split('=')[1]
            break

    if not ip_address:
        logging.error("Failed to resolve hostname: {}".format(hostname))
        return "Failed to resolve hostname", 500

    logging.debug("Resolved IP address: {}".format(ip_address))

    # Make a request to the Fibonacci Server
    try:
        fs_url = "http://{}:{}/fibonacci?number={}".format(ip_address, fs_port, number)
        logging.debug("Sending request to Fibonacci Server: {}".format(fs_url))
        response = requests.get(fs_url, timeout=5)
        
        if response.status_code == 200:
            logging.debug("Received response from Fibonacci Server: {}".format(response.text))
            return jsonify(response.json()), 200
        else:
            logging.error("Failed to retrieve Fibonacci number. Status code: {}".format(response.status_code))
            return "Failed to retrieve Fibonacci number. Status code: {}".format(response.status_code), response.status_code
    except requests.RequestException as e:
        logging.error("Error connecting to Fibonacci server: {}".format(str(e)))
        return "Error connecting to Fibonacci server: {}".format(str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

