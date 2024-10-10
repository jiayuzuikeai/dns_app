# Fibonacci Server (FS)

from flask import Flask, request, jsonify
import socket

app = Flask(__name__)

@app.route('/register', methods=['PUT'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Parse and validate data
    hostname = data.get("hostname")
    ip = data.get("ip")
    as_ip = data.get("as_ip")
    as_port = data.get("as_port")

    if not hostname or not ip or not as_ip or not as_port:
        return jsonify({"error": "Missing fields"}), 400

    try:
        as_port = int(as_port)
    except ValueError:
        return jsonify({"error": "Invalid port number"}), 400

    # Prepare DNS registration message using .format()
    registration_message = "TYPE=A\nNAME={}\nVALUE={}\nTTL=10\n".format(hostname, ip).encode()

    # Send registration message to Authoritative Server via UDP
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(registration_message, (as_ip, as_port))
        sock.close()
    except socket.error as e:
        return jsonify({"error": "Failed to register with AS: {}".format(str(e))}), 500

    return jsonify({"message": "Registration successful"}), 201

@app.route('/fibonacci', methods=['GET'])
def fibonacci():
    number = request.args.get('number')
    
    if not number:
        return "Missing number parameter", 400

    try:
        n = int(number)
    except ValueError:
        return "Invalid number", 400

    # Calculate Fibonacci number
    def calculate_fibonacci(num):
        if num == 0:
            return 0
        elif num == 1:
            return 1
        else:
            a, b = 0, 1
            for _ in range(2, num + 1):
                a, b = b, a + b
            return b

    result = calculate_fibonacci(n)
    return jsonify({"fibonacci": result}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090)

