
import random
import os
from paho.mqtt import client as mqtt_client
import json
import RPi.GPIO as GPIO

random_id = random.randint(1000, 9000)
relay_ch = 17
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_ch, GPIO.OUT)


broker = os.getenv("MQTT_BROKER_ADDR", "127.0.0.1")
topic = os.getenv("MQTT_TOPIC", "sensors/data")
this_edge_device = os.getenv("DEVICE_ID", "sub_env_device_id_not_set")
port = 1883
# topic = "python/mqtt"
# generate client ID with pub prefix randomly
client_id = this_edge_device+str(random_id) # concatenate 4 numbers to uniquely identify this device
# username = 'emqx'
# password = 'public'


def connect_mqtt() -> mqtt_client:
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


def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        decoded_message=str(msg.payload.decode("utf-8"))

        try:
                    
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
                        if(not msg_json['devices_details'][0]['user_claim']):
                            print("device is not claimed")
                            
                        else:
                            print("claim")
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
        except ValueError as e:
            print("RECEIVED READINGS SENSOR BUT STRING") 

    client.subscribe(topic)
    client.on_message = on_message

#read from mounted storage to get device id
def get_device_id_from_files():
    # Open the JSON file
    # with open("/etc/yggdrasil/device/device-config.json", "r") as json_file:
    with open("device-config.json", "r") as json_file:
        # Load the JSON data from the file
        json_data = json.load(json_file)
    # Now you can access the data in the JSON file as a Python dictionary
    return json_data['device_id']

def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if __name__ == '__main__':
    run()
