
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
        msg_json=json.loads(decoded_message)
        # print(msg_json['humidity'])
        if("pump_flotta_egdedevice_id" in msg_json):
            #remove last 4 randomly generated characters
            print('message for this edge device id: '+this_edge_device)
            if(msg_json['pump_flotta_egdedevice_id'] ==  this_edge_device):
                
                print("pump action is "+ str(msg_json['pump_action']))
                #check command sent from publisher to turn on pump or not
                if(msg_json['pump_action'] ==1):
                    GPIO.output(relay_ch, GPIO.HIGH) #turn on
                else:
                    GPIO.output(relay_ch, GPIO.LOW) #turn off
            else:
                print('message not for this edge device')
            
        
        
        # #check if the published message is for this device
        # if(msg_json['flotta_egdedevice_id'] == this_edge_device):
        #     print('message for this edge device')
        #     #check command sent from publisher to turn on pump or not
        # else:
        #     print('message not for this edge device')
    client.subscribe(topic)
    client.on_message = on_message


def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if __name__ == '__main__':
    run()
