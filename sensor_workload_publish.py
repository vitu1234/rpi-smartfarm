import os
import random
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import RPi.GPIO as gp  
import json
from paho.mqtt import client as mqtt_client
import requests
from requests.exceptions import HTTPError
from pymongo import MongoClient
from datetime import datetime
import pymongo
from pymongo.errors import ConnectionFailure



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
random_id = random.randint(100, 1000)

#MQTT SETUP
broker = os.getenv("MQTT_BROKER_ADDR", "127.0.0.1") #set to default localhost to avoid program crashing
topic = os.getenv("MQTT_TOPIC", "sensors/data")
# device_id = os.getenv("DEVICE_ID", "pub_env_device_id_not_set"+str(random_id))
ML_SERVICE_ADDR = os.getenv("ML_SERVICE_ADDR", "127.0.0.1")
port = 1883

DEVICE_TYPE = os.getenv("DEVICE_TYPE", "sensor")
# topic = "python/mqtt"
# generate client ID with pub prefix randomly
# client_id = device_id

#MONGODB SETUP
MONGO_ADDR = os.getenv("MONGO_ADDR", "127.0.0.1")
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "not_set_username")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "not_set_password")
MONGO_DB = os.getenv("MONGO_DB", "env_not_set_mongo_db")
# Provide the mongodb atlas url to connect python to mongodb using pymongo
CONNECTION_STRING = "mongodb://"+MONGO_USERNAME+":"+MONGO_PASSWORD+"@"+MONGO_ADDR

#MQTT CONNECT
def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(get_device_id_from_files())
    client.username_pw_set("mqtt", "mqtt")
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

#read from mounted storage to get device id
def get_device_id_from_files():
    # Open the JSON file
    # with open("/etc/yggdrasil/device/device-config.json", "r") as json_file:
    with open("device-config.json", "r") as json_file:
        # Load the JSON data from the file
        json_data = json.load(json_file)
    # Now you can access the data in the JSON file as a Python dictionary
    return json_data['device_id']

#returns true of false if registered or not
def register_device_in_db(my_mqtt_client):
    # sending get request and saving the response as response object
    #if register file exists it means device already registered, so skip - otherwise it means its the initial turn on

    if(os.path.exists("device_register.json")):
        print("device already registered, skip registration")
    else:
        device_id = get_device_id_from_files()
        data_array ={
            "flotta_egdedevice_id": device_id,
            "device_type":DEVICE_TYPE,
            "mqtt_request_for":"register_device"
        }
        payload = json.dumps(data_array)
        result = my_mqtt_client.publish(topic, payload)
        status = result[0]
        if status == 0:
            print("Published register device to MQTT BROKER: "+broker+"on PORT: "+str(port))
        else:
            print("Failed to publish register device to MQTT BROKER: "+broker+"on PORT: "+str(port))

#get device details in db
def get_device_details(my_mqtt_client):
    #if device file exists, it means user claimed the device otherwise get details to trigger create file if created
    if(os.path.exists("device_claim.json")):
        print("device already registered, skip registration")
    else:
        device_id = get_device_id_from_files()
        data_array ={
            "flotta_egdedevice_id": device_id,
            "mqtt_request_for":"device_details"
        }
        payload = json.dumps(data_array)
        result = my_mqtt_client.publish(topic, payload)
        status = result[0]
        if status == 0:
            print("Published get device details to MQTT BROKER: "+broker+"on PORT: "+str(port))
        else:
            print("Failed to publish get device details to MQTT BROKER: "+broker+"on PORT: "+str(port))     

#read from sensors and publish to mqtt
def read_sensor_values():
    data_string =""
    try:
        time.sleep(3)
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity

        if humidity is not None and temperature_c is not None:
            data = {
                "flotta_egdedevice_id": get_device_id_from_files(),
                "temperature": temperature_c,
                "humidity": humidity,
            }
            payload = json.dumps(data)
            data_string = "flotta_edgedevice_id,temperature,humidity"+get_device_id_from_files()+","+str(temperature_c)+","+str(humidity)
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
    except Exception as error:
        GPIO.cleanup()
        dhtDevice.exit()
        raise error
    
    return data_string


def publish_sensor_readings(my_mqtt_client, readings):
    #only send sensor values if both device register and claim files exists
    if(os.path.exists("device_claim.json") and os.path.exists("device_register.json")):
        device_id = get_device_id_from_files()
        payload = readings
        result = my_mqtt_client.publish(topic, payload)
        status = result[0]
        if status == 0:
            print("Published device readings ID: "+device_id+" to MQTT BROKER: "+broker+"on PORT: "+str(port))
        else:
            print("Failed to publish readings ID: "+device_id+" to MQTT BROKER: "+broker+"on PORT: "+str(port))
    else:
        print("device not yet registered or claimed, cannot publish anything")
    
def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        decoded_message=str(msg.payload.decode("utf-8"))
        msg_json=json.loads(decoded_message)

        #if this is a response to a request made earlier
        if("device_id" in msg_json and "mqtt_response_for" in msg_json):
            #if the response received is for this device
            if(msg_json['device_id'] == get_device_id_from_files()):
                #handle the response response type
                if(msg_json['mqtt_response_for'] == "devices_details"):
                    print("Got device details response")
                    print(msg_json['devices_details'])
                    # print(msg_json['devices_details'][0]['user_claim'])

                    #if device is claimed, create claim file if it does not exist
                    if(msg_json['devices_details'][0]['user_claim']):
                        print("device is claimed")
                    else:
                        if(os.path.exists("device_claim.json")):
                            print("claim file exists")
                        else:
                            print("claim file not exits, creating it")
                            f = open("device_claim.json", "a")
                            f.close()

                elif(msg_json['mqtt_response_for'] == "register_device"):
                    #if file exists device is registered already
                    print("Got device register response")
                    if(os.path.exists("device_register.json")):
                        print("register file exists")
                    else:
                        print("register file not exits, creating it")
                        f = open("device_register.json", "a")
                        f.close()
                elif(msg_json['mqtt_response_for'] =="registered_device_user_claim"):
                    if(os.path.exists("device_claim.json")):
                        print("claim file exists")
                    else:
                        print("claim file not exits, creating it")
                        f = open("device_claim.json", "a")
                        f.close()
                    
                else:
                    print("Got unknown device response type")

                    
            else:
                print("Messaged received | not for this device")
        else:
            print("Messaged received | not a response")        

    client.subscribe(topic)
    client.on_message = on_message


def run():
    client = connect_mqtt()
    while True:
        subscribe(client)
        register_device_in_db(client)
        time.sleep(5)
        get_device_details(client)
        time.sleep(5)
        readings = read_sensor_values()
        if(readings !=""):
            publish_sensor_readings(client, readings)
        
        
        time.sleep(3)
    # client.loop_start()


if __name__ == '__main__':
   run()