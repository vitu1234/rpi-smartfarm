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
device_id = os.getenv("DEVICE_ID", "pub_env_device_id_not_set"+str(random_id))
ml_svc_url = os.getenv("ML_SERVICE_ADDR", "127.0.0.1")
port = 1883
# topic = "python/mqtt"
# generate client ID with pub prefix randomly
client_id = device_id

#MONGODB SETUP
MONGO_ADDR = os.getenv("MONGO_ADDR", "127.0.0.1")
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "not_set_username")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "not_set_password")
MONGO_DB = os.getenv("MONGO_DB", "env_not_set_mongo_db")
# Provide the mongodb atlas url to connect python to mongodb using pymongo
CONNECTION_STRING = "mongodb://"+MONGO_USERNAME+":"+MONGO_PASSWORD+"@"+MONGO_ADDR


def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client()
    client.username_pw_set("mqtt", "mqtt")
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

#connect to mongo database
def connect_mongo_database():
    
        # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
    dbname = 'error'
    if(MONGO_DB !='env_not_set_mongo_db'):
        try:
            client = MongoClient(CONNECTION_STRING)
            dbname = client[MONGO_DB]
        except ConnectionFailure as e:
            print(e)
            dbname = 'error'
    else:
        print('MONGO_DB env not set')
        dbname = 'error'
    return dbname

#check if device is registered in mongo database | if not register, register it
def register_device_mongodb():
    database = connect_mongo_database()
    
    # return
    if(database != 'error'):
        response = False
        try:
            collection = database["devices"]
            #check if device exists
            cursor2 = collection.find_one({"flotta_egdedevice_id":device_id}) 
            if(cursor2 is None):
                    # Creating Dictionary of records to be
                # inserted
                record = {
                        "flotta_egdedevice_id": device_id,
                        "user_claim": False,
                        "mode":"Auto"
                        }
                # Inserting the record1 in the collection
                # by using collection.insert_one()
                inserted = collection.insert_one(record)
                if(inserted):
                    response = True
                else:
                    response = False
            else:
                response = True
        except Exception as error:
            print("error")
            response = False
        finally:
            print("finally block")
            return response 
    else:
        return False

#check the preset device mode | return str:Manual or Auto
def get_preset_device_mode():
    database = connect_mongo_database()
    collection = database["devices"]

    #check if device exists
    cursor2 = collection.find_one({"flotta_egdedevice_id":device_id})
    if(cursor2 is not None):
        mode = cursor2['mode']
        return mode
    else:
        return 'error'    

#check last time pumps were turned on or off 
def last_device_actuators_activity():
    database = connect_mongo_database()
    collection = database["device_actuators_timing"]

    #check if device exists
    cursor2 = collection.find_one({"flotta_egdedevice_id":device_id, "is_irrigated":1}, sort=[( 'timestamp', pymongo.DESCENDING )])
    
    if(cursor2 is not None):
        date_time_str = str(cursor2['timestamp'])
        date_time_obj =datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
        date_time_str = date_time_obj.strftime('%Y-%m-%d %H:%M:%S')

        date_time_str2 = str(datetime.now())
        date_time_obj2 =datetime.strptime(date_time_str2, '%Y-%m-%d %H:%M:%S.%f')
        date_time_str2 = date_time_obj2.strftime('%Y-%m-%d %H:%M:%S')

        fmt = '%Y-%m-%d %H:%M:%S'
        tstamp1 = datetime.strptime(date_time_str, fmt)
        tstamp2 = datetime.strptime(date_time_str2, fmt)

        if tstamp1 > tstamp2:
            td = tstamp1 - tstamp2
        else:
            td = tstamp2 - tstamp1
        td_mins = int(round(td.total_seconds() / 60))
        return td_mins
    else:
        return 'first_time'    

#save actuators action;
def save_actuators_action(flotta_egdedevice_id,temperature, humidity,actual_soil_moisture, predicted_soil_moisture, is_irrigated):
    database = connect_mongo_database()

    # return
    if(database != 'error'):
        response = False
        try:
            collection1 = database["devices"]
            cursor2 = collection1.find_one({"flotta_egdedevice_id":device_id})
            mode =""
            if(cursor2 is not None):
                mode = cursor2['mode']
            else:
                mode = "Unknown Mode"
            record = {
                "flotta_egdedevice_id": flotta_egdedevice_id,
                "temperature":temperature,
                "humidity":humidity,
                "actual_soil_moisture": actual_soil_moisture,
                "predicted_soil_moisture":predicted_soil_moisture,
                "is_irrigated": is_irrigated,
                "mode": mode,
                "timestamp": datetime.now()
            }
            collection = database["device_actuators_timing"]
            # Inserting the record1 in the collection
            # by using collection.insert_one()
            inserted = collection.insert_one(record)
            if(inserted):
                response = True
            else:
                response = False
        except Exception as error:
            print("error")
            response = False
        finally:
            print("finally block - device_actuators_timing table")
            return response 
    else:
        return False


def publish_switch_trigger(client):
    #check edge device registration status
    registered = register_device_mongodb()
    client = connect_mqtt()
    if(registered):
        #check if system mode is Auto or Manual first
        device_mode = get_preset_device_mode()
        if device_mode == 'Auto':
            #get this device predictions from the ML service
            # sending get request and saving the response as response object
            try:
                response = requests.get(url = ml_svc_url+'/prediction_by_device/'+device_id)
                # If the response was successful, no Exception will be raised
                response.raise_for_status()
            except HTTPError as http_err:
                print(f'HTTP error occurred: {http_err}')  
            except Exception as err:
                print(f'Other error occurred: {err}')  
            else:
                    # extracting data in json format
                if response.status_code == 200:
                    data = response.json()
                    if(data['error'] is not True):
                        #publish to turn pump on or off
                        print("publish to turn pump on or off")
                        temperature = data['temperature']
                        humidity = data['humidity']
                        actual_soil_moisture = data['actual_soil_moisture']
                        predicted_soil_moisture = data['predicted_soil_moisture']
                        
                        #pumps have to run if moisture is less than 50%
                        if(predicted_soil_moisture <= 50):
                        #check last time irrigated: if time is less than 1 hour, do not turn on actuators
                            last_activity = last_device_actuators_activity() #response is in minutes

                            if(last_activity != 'first_time'):
                                print('Last activitiy in mins: '+str(last_activity))
                                #turn on pump if last activity is gearer than 1hr; last activity is in minutes
                                if(last_activity >= 60):
                                    save_actuators_action(device_id,temperature, humidity,actual_soil_moisture, predicted_soil_moisture,1)
                                    #publish turn on pumps
                                    data = {
                                        "pump_flotta_egdedevice_id": device_id,
                                        "pump_action": 1
                                    }
                                    payload = json.dumps(data)
                                    result = client.publish(topic, payload)
                                    # result: [0, 1]
                                    status = result[0]
                                    if status == 0:
                                        print(f"Send action message `{payload}` to topic `{topic}`")
                                    else:
                                        print(f"Failed to send pump action message to topica {topic}")
                                    
                                    #wait for 5mins and shutdown pump
                                    time.sleep(300)

                                    save_actuators_action(device_id,temperature, humidity,actual_soil_moisture, predicted_soil_moisture,0)
                                    data = {
                                        "pump_flotta_egdedevice_id": device_id,
                                        "pump_action": 0
                                    }
                                    payload = json.dumps(data)
                                    result = client.publish(topic, payload)
                                    # result: [0, 1]
                                    status = result[0]
                                    if status == 0:
                                        print(f"Send action message `{payload}` to topic `{topic}`")
                                    else:
                                        print(f"Failed to send pump action message to topic {topic}")
                                else:
                                    save_actuators_action(device_id,temperature, humidity,actual_soil_moisture, predicted_soil_moisture,0)
                            else:
                                save_actuators_action(device_id,temperature, humidity,actual_soil_moisture, predicted_soil_moisture,1)
                                #publish turn on pumps
                                data = {
                                    "pump_flotta_egdedevice_id": device_id,
                                    "pump_action": 1
                                }
                                payload = json.dumps(data)
                                result = client.publish(topic, payload)
                                # result: [0, 1]
                                status = result[0]
                                if status == 0:
                                    print(f"Send action message `{payload}` to topic `{topic}`")
                                else:
                                    print(f"Failed to send pump action message to topic {topic}")
                                
                                #wait for 5mins and shutdown pump
                                time.sleep(300) #for now this is 5s for testing

                                save_actuators_action(device_id,temperature, humidity,actual_soil_moisture, predicted_soil_moisture,0)
                                data = {
                                    "pump_flotta_egdedevice_id": device_id,
                                    "pump_action": 0
                                }
                                payload = json.dumps(data)
                                result = client.publish(topic, payload)
                                # result: [0, 1]
                                status = result[0]
                                if status == 0:
                                    print(f"Send action message `{payload}` to topic `{topic}`")
                                else:
                                    print(f"Failed to send pump action message to topic {topic}")
                        else:
                            save_actuators_action(device_id,temperature, humidity,actual_soil_moisture, predicted_soil_moisture,0)
                    else:
                        print("error on the ML service")
                else:
                    print('Did not get response from the ML service')
        else:
            print("device mode is "+ device_mode +" no need to auto trigger irrigation" )
    else:
        print("Do nothing, device registration in mongodb failed")

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
                    client.loop_stop()
                    client = connect_mqtt() 
                    print(f"Failed to send message to topic {topic}")
            else:
                print(f"Failed to send message to topic, data not collected {topic}")
           
            if(MONGO_ADDR != '127.0.0.1' and MONGO_USERNAME !='not_set_username' and MONGO_PASSWORD !='not_set_password'):
                publish_switch_trigger(client)
            else:
                print('MONGO_ADDR ,MONGO_USERNAME or MONGO_USERNAME Variable not set properly')

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