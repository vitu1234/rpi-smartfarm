import random
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import RPi.GPIO as gp  
import json
from paho.mqtt import client as mqtt_client

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT11(board.D4) 
relay_ch = 17
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_ch, GPIO.OUT)

import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

broker = '192.168.13.203'
port = 1883
# topic = "python/mqtt"
# generate client ID with pub prefix randomly
LOCATION         = "location" 
random_id = random.randint(0, 1000)
client_id = f'sensor-mqtt-dht'
topic = f'sensors/'+LOCATION
topic_hum = f'sensor-mqtt-dht-humid-{random_id}'
# username = 'emqx'
# password = 'public'

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set("mqtt", "mqtt")
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def publish(client):
    msg_count = 0
    while True:
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity
        payload = '{"location":"' + LOCATION + '","temperature":' + str(temperature_c) + ',"humidity":' + str(humidity) + '}'
        # payload = '{"location":"'+LOCATION+', "}'
        data = {
            "location": LOCATION,
            "temperature": temperature_c,
            "humidity": humidity
        }
        payload = json.dumps(data)

        if humidity is not None and temperature_c is not None:
            result = client.publish(topic, payload)
            # result: [0, 1]
            status = result[0]
            if status == 0:
                print(f"Send `{payload}` to topic `{topic}`")
            else:
                print(f"Failed to send message to topic {topic}")
        else:
            result = client.publish(topic, "Failed")
        msg_count += 1
        time.sleep(10)
def run():
    while True:
        try:
            client = connect_mqtt()
            client.loop_start()
            publish(client)
        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read, just keep going
            print(error.args[0])
            time.sleep(2.0)
            continue
        except Exception as error:
            GPIO.cleanup()
            dhtDevice.exit()
            raise error

if __name__ == '__main__':
    run()