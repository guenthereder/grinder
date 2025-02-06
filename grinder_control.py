import time
import json
import paho.mqtt.client as mqtt
from gpiozero import Button, OutputDevice
from flask import Flask, request, render_template

# MQTT Configuration
MQTT_BROKER = "192.168.178.25"  # Update with your MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC_SINGLE = "buttons/grinder/1"
MQTT_TOPIC_DOUBLE = "buttons/grinder/2"

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

def start_grinder(grind_time, topic):
    print(f"[start_grinder] Sending MQTT message to {topic} and activating relay for {grind_time} ms")
    mqtt_client.publish(topic, "on")
    relay.on()
    time.sleep(grind_time / 1000.0)  # Convert milliseconds to seconds
    relay.off()
    mqtt_client.publish(topic, "off")

# Assign button actions
single_button.when_held = lambda: start_grinder(grind_times["single"], MQTT_TOPIC_SINGLE)
double_button.when_held = lambda: start_grinder(grind_times["double"], MQTT_TOPIC_DOUBLE)

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "action" in request.form:
            action = request.form["action"]
            if action == "single":
                start_grinder(grind_times["single"], MQTT_TOPIC_SINGLE)
            elif action == "double":
                start_grinder(grind_times["double"], MQTT_TOPIC_DOUBLE)
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
