import time
import json
import threading
import paho.mqtt.client as mqtt
from gpiozero import Button, OutputDevice
from flask import Flask, request, render_template

# MQTT Configuration
MQTT_BROKER = "192.168.178.25"  # Update with your MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "buttons/cafe"

# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Define GPIO pins
single_button = Button(17, hold_time=0.1)  # Require 100ms hold time
double_button = Button(27, hold_time=0.1)  # Require 100ms hold time
relay = OutputDevice(18)

# Default grind times in milliseconds
grind_times = {
    "single": 5000,  # 5 seconds
    "double": 10000  # 10 seconds
}

# Load settings from file if available
try:
    with open("settings.json", "r") as f:
        grind_times = json.load(f)
except FileNotFoundError:
    pass

def start_grinder(grind_time, grinder_id):
    message = json.dumps({"grinder": grinder_id})
    print(f"[start_grinder] Sending MQTT message: {message} to topic {MQTT_TOPIC}")
    mqtt_client.publish(MQTT_TOPIC, message)

# Global variables to manage grinder state
grinder_thread = None
grinder_stop_event = None

def grinder_worker(grind_time, grinder_id):
    """Run the grinder for the specified time unless stopped early."""
    relay.on()
    start = time.time()
    while (time.time() - start) * 1000 < grind_time:
        if grinder_stop_event and grinder_stop_event.is_set():
            break
        time.sleep(0.1)
    relay.off()
    print(f"[grinder_worker] Grinder {grinder_id} finished or stopped")

def toggle_grinder(grind_time, grinder_id):
    """Start the grinder if not running, otherwise stop it early."""
    global grinder_thread, grinder_stop_event
    if grinder_thread and grinder_thread.is_alive():
        # Stop the currently running grinder
        grinder_stop_event.set()
        grinder_thread.join()
        grinder_thread = None
        grinder_stop_event = None
        print(f"[toggle_grinder] Stopped grinder {grinder_id}")
    else:
        # Start a new grinder thread
        grinder_stop_event = threading.Event()
        grinder_thread = threading.Thread(target=grinder_worker, args=(grind_time, grinder_id))
        grinder_thread.start()
        print(f"[toggle_grinder] Started grinder {grinder_id} for {grind_time} ms")

# Assign button actions
single_button.when_held = lambda: toggle_grinder(grind_times["single"], 1)
double_button.when_held = lambda: toggle_grinder(grind_times["double"], 2)

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "action" in request.form:
            action = request.form["action"]
            if action == "single":
                start_grinder(grind_times["single"], 1)
            elif action == "double":
                start_grinder(grind_times["double"], 2)
        else:
            single_time = request.form.get("single_time", type=int)
            double_time = request.form.get("double_time", type=int)
            if single_time and double_time and 0 < single_time <= 100000 and 0 < double_time <= 100000:
                grind_times["single"] = single_time
                grind_times["double"] = double_time
                # Save settings to file
                with open("settings.json", "w") as f:
                    json.dump(grind_times, f)
    return render_template("index.html", single_time=grind_times["single"], double_time=grind_times["double"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
