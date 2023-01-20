
import random
import os
from paho.mqtt import client as mqtt_client
import json

random_id = random.randint(0, 10000)

broker = os.getenv("MQTT_BROKER_ADDR", "127.0.0.1")
topic = os.getenv("MQTT_TOPIC", "sensors/data")
this_edge_device = os.getenv("DEVICE_ID", "sub_env_device_id_not_set"+str(random_id))
port = 1883
# topic = "python/mqtt"
# generate client ID with pub prefix randomly
client_id = this_edge_device
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
        print(msg_json['humidity'])

        
        #check if the published message is for this device
        if(msg_json['flotta_egdedevice_id'] == this_edge_device):
            print('message for this edge device')
            #check command sent from publisher to turn on pump or not
        else:
            print('message not for this edge device')
    client.subscribe(topic)
    client.on_message = on_message


def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if __name__ == '__main__':
    run()
