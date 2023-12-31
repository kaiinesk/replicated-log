from flask import Flask, request, jsonify
import requests
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
messages = []
message_counter = 0
secondaries = ["http://secondary1:5000", "http://secondary2:5000"]
executor = ThreadPoolExecutor(max_workers = len(secondaries))
secondaries_status = {url: "healthy" for url in secondaries}
read_only_mode = False

logging.basicConfig(level = logging.INFO)

def deliver_message(secondary, message_id, message):
    exponential_backoff = 1
    while True:
        try:
            response = requests.post(f"{secondary}/messages", json = {"id": message_id, "message": message}, timeout = 5)
            if response.status_code == 200:
                logging.info(f"MESSAGE {message_id} - {message} DELIVERED TO {secondary}")
                break
            else:
                logging.error(f"ERROR FROM {secondary}: {response.status_code}")
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            logging.error(f"DELIVERY FAILED TO {secondary}: {e}")
        time.sleep(exponential_backoff)
        exponential_backoff *= 2

def replicate_to_secondary(secondary, message_id, message, acknowledgement_event):
    deliver_message(secondary, message_id, message)
    acknowledgement_event.set()

def heartbeat():
    global read_only_mode
    while True:
        for secondary in secondaries:
            try:
                response = requests.get(f"{secondary}/health")
                if response.status_code == 200:
                    secondaries_status[secondary] = "healthy"
                else:
                    secondaries_status[secondary] = "suspected"
                    logging.warning(f"{secondary} IS SUSPECTED ({response.status_code})")
            except requests.exceptions.RequestException as exception:
                secondaries_status[secondary] = "dead"
                logging.error(f"{secondary} IS DEAD ({exception})")        
        healthy_count = list(secondaries_status.values()).count("healthy")
        if healthy_count <= len(secondaries) // 2:
            read_only_mode = True
            logging.warning("READ-ONLY MODE")
        else:
            read_only_mode = False
        time.sleep(5)

threading.Thread(target = heartbeat, daemon = True).start()

@app.route("/health", methods = ["GET"])
def health_check():
    return jsonify(secondaries_status), 200

@app.route("/messages", methods = ["POST"])
def post_message():
    global message_counter, read_only_mode
    if read_only_mode:
        return jsonify({"status": "error", "message": "master is in read-only mode"}), 503
    data = request.json
    message = data.get("message")
    write_concern = int(data.get("write_concern", 1))   
    if not message:
        return jsonify({"status": "error", "message": "no message"}), 400
    message_id = message_counter
    message_data = {"id": message_id, "message": message}
    messages.append(message_data)
    message_counter += 1    
    acknowledgement_events = []
    for secondary in secondaries:
        acknowledgement_event = threading.Event()
        acknowledgement_events.append(acknowledgement_event)
        threading.Thread(target = replicate_to_secondary, args = (secondary, message_id, message, acknowledgement_event)).start()
    for item in range(write_concern - 1):
        acknowledged = any(event.wait(5) for event in acknowledgement_events)
        if not acknowledged:
            logging.error("TIMEOUT - WAITING FOR ACKNOWLEDGEMENTS")
            return jsonify({"status": "error", "message": "timeout - waiting for acknowledgements"}), 500    
    return jsonify({"status": "success", "message": "message replicated"}), 200

@app.route("/messages", methods = ["GET"])
def get_messages():
    return jsonify([{"id": message["id"], "message": message["message"]} for message in messages]), 200

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000)