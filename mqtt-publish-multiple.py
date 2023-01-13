import random
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import RPi.GPIO as gp  
import datetime
from paho.mqtt import client as mqtt_client

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT11(board.D4) 
relay_ch = 17
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_ch, GPIO.OUT)

import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

broker = '192.168.13.43'
port = 1883
# topic = "python/mqtt"
# generate client ID with pub prefix randomly
random_id = random.randint(0, 1000)
client_id = f'sensor-mqtt-dht'
topic_temp = f'sensor-mqtt-dht-temp-{random_id}'
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
        time.sleep(10)
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity
        
        if humidity is not None and temperature_c is not None:
            result = client.publish(topic_temp, temperature_c)
            result1 = client.publish(topic_hum, humidity)
            # result: [0, 1]
            status = result[0]
            status1 = result1[0]
            if status == 0:
                print(f"Send `{temperature_c}` to topic `{topic_temp}`")
            else:
                print(f"Failed to send message to topic {topic_temp}")

            if status1 == 0:
                print(f"Send `{humidity}` to topic `{topic_hum}`")
            else:
                print(f"Failed to send message to topic {humidity}")
        else:
            result1 = client.publish(topic_hum, "Failed")
            result = client.publish(topic_temp, "Failed")
        msg_count += 1

def run():
    while True:
        try:
            client = connect_mqtt()
            client.loop_start()
            # publish(client)
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