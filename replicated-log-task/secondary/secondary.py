from flask import Flask, request, jsonify
import logging
import random

app = Flask(__name__)
messages = {}
last_processed_id = -1

logging.basicConfig(level = logging.INFO)

def process_message(message_id, message):
    global last_processed_id
    messages[message_id] = message
    if message_id == last_processed_id + 1:
        while last_processed_id + 1 in messages:
            last_processed_id += 1
            logging.info(f"PROCESSING MESSAGE: {messages[last_processed_id]}")

@app.route("/messages", methods = ["POST"])
def replicate_message():
    if random.random() < 0.1:
        return jsonify({"status": "error", "message": "replication error simulation"}), 500   
    data = request.json
    message_id = data.get("id")
    message = data.get("message")
    process_message(message_id, message)
    return jsonify({"status": "success", "message": "message received"}), 200

@app.route("/health", methods = ["GET"])
def health_check():
    if random.random() < 0.1:
        return jsonify({"status": "unhealthy error simulation"}), 500
    return jsonify({"status": "healthy"}), 200

@app.route("/messages", methods = ["GET"])
def get_messages():
    ordered_messages = [{"id": message_id, "message": messages[message_id]} for message_id in sorted(messages.keys()) if message_id <= last_processed_id]
    return jsonify(ordered_messages), 200

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)