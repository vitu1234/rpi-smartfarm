import os
import random
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import RPi.GPIO as gp  
import json
from paho.mqtt import client as mqtt_client

import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

#mcp module and soil sensor
import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
from pprint import pprint

#set soil sensor values
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D5)
mcp = MCP.MCP3008(spi, cs)
channel = AnalogIn(mcp, MCP.P0) #soil sensor connected to channel 0

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT11(board.D4) 
relay_ch = 17
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_ch, GPIO.OUT)


#Calibraton values
min_moisture = 26880
max_moisture = 65472

broker = os.getenv("MQTT_BROKER_ADDR", "127.0.0.1") #set to default localhost to avoid program crashing
port = 1883
# topic = "python/mqtt"
# generate client ID with pub prefix randomly
LOCATION = "data" 
random_id = random.randint(0, 1000)
client_id = f'sensor-mqtt-dht'
topic = f'sensors/'+LOCATION
topic_hum = f'sensor-mqtt-dht-humid-{random_id}'
device_id = os.getenv("DEVICE_ID", "env_device_id_not_set")

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


def publish():
    
    client = connect_mqtt()
    client.loop_start()
    
    while True:
        try:
            time.sleep(3)
            temperature_c = dhtDevice.temperature
            temperature_f = temperature_c * (9 / 5) + 32
            humidity = dhtDevice.humidity
            moisture = (max_moisture-channel.value)*100/(max_moisture-min_moisture) 
            adc_value = channel.value
            moisture2 = ""
            if moisture >= 100:
                moisture2 = 100
            else:
                moisture2 = "" + "%.1f" % moisture

            if humidity is not None and temperature_c is not None:
                data = {
                    "flotta_egdedevice_id": device_id,
                    "temperature": temperature_c,
                    "humidity": humidity,
                    "soil_moisture": int(float(moisture2))
                }
                payload = json.dumps(data)
                result = client.publish(topic, payload)
                # result: [0, 1]
                status = result[0]
                if status == 0:
                    print(f"Send `{payload}` to topic `{topic}`")
                else:
                    print(f"Failed to send message to topic {topic}")
            else:
                print(f"Failed to send message to topic, data not collected {topic}")
           
            
        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read, just keep going
            print(error.args[0])
            time.sleep(2.0)
            continue
        except Exception as error:
            GPIO.cleanup()
            dhtDevice.exit()
            time.sleep(2.0)
            raise error

        client.loop_stop()    
        time.sleep(7)
    
if __name__ == '__main__':
    publish()