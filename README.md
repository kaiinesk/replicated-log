# Replicated Log Task

This repository currently contains the implementation of the **Replicated Log Task** using Python.

To execute the code, please run `docker-compose up --build` from the project's directory.

To test on MAC:
* posts a message __"Hello, World!"__ to the master server with write concern 1
`curl -X POST http://localhost:5000/messages -H "Content-Type: application/json" -d '{"message": "Hello, World!", "write_concern": 1}'`;
* checks the messages on the master
`curl http://localhost:5000/messages`;
* checks the messages on the 1st secondary
`curl http://localhost:5001/replicated_messages`;
* checks the messages on the 2nd secondary
`curl http://localhost:5002/replicated_messages`.

Functions:
* **deliver_message** - sends a message to a secondary server with the exponential backoff strategy for retries if the request fails implemented;
* **replicate_to_secondary** - calls **deliver_message** to replicate the message to the secondaries, and sets an acknowledgement_event after successful delivery;
* **heartbeat** - checks the health of each secondary and switches the app to the read_only_mode;
* **process_message** - processes and stores incoming messages in order on the secondaries.
