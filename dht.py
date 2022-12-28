
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import RPi.GPIO as gp  
import datetime

#influxdb
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS



GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
# Nf8h0NO5xQZMKx6nCcK0OtfLozuFngoREmynFKkIK_Zum3kcNw0F7AIjxWFAu5QwoO5Nz1N3RYgbxKD6zSOysA==

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT11(board.D4) 
relay_ch = 17
soil_sensor = 8

# soil moisture
# gp.setmode(gp.BOARD)  
gp.setup(soil_sensor,gp.IN)   

# you can pass DHT22 use_pulseio=False if you wouldn't like to use pulseio.
# This may be necessary on a Linux single board computer like the Raspberry Pi,
# but it will not work in CircuitPython.
# dhtDevice = adafruit_dht.DHT22(board.D18, use_pulseio=False)

# As RPi has only digital pin, we can only detect 0 or 1 means HIGH or LOW signal 
# from sensor. So when a High signal is encountered on Pi pin 8, 
# it means there is no moisture in the soil. It is so because soil moisture 
# sensor works on inverting output circuit op-amp. Using this circuit reverses
# the output on the digital data pin of soil moisture sensor.

while True:
    try:
        # Print the values to the serial port
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity
        print(
            "Temp: {:.1f} F / {:.1f} C    Humidity: {}% ".format(
                temperature_f, temperature_c, humidity
            )
        )

        #InfluxDB Connection Details
        bucket = "firstbucket"
        org = "primary"
        token = "Nf8h0NO5xQZMKx6nCcK0OtfLozuFngoREmynFKkIK_Zum3kcNw0F7AIjxWFAu5QwoO5Nz1N3RYgbxKD6zSOysA=="
        # Store the URL of your InfluxDB instance
        url="http://192.168.13.43:9003"

        client = influxdb_client.InfluxDBClient(
            url=url,
            token=token,
            org=org
        )

        write_api = client.write_api(write_options=SYNCHRONOUS)


        p = influxdb_client.Point("TemperatureSensor").tag("location", "sensor1").field("temperature", temperature_c)
        write_api.write(bucket=bucket, org=org, record=p)
        client.close()

        p = influxdb_client.Point("TemperatureSensor").tag("location", "sensor1").field("humidity", humidity)
        write_api.write(bucket=bucket, org=org, record=p)
        client.close()
        
        
        print('\nSoil Moisture\n')

        print(GPIO.input(soil_sensor))
        print(not gp.input(soil_sensor))

        if (not gp.input(soil_sensor))==0:
            print('\n Soil is Wet - turn off pump\n')
            GPIO.setup(relay_ch, GPIO.OUT)
            GPIO.output(relay_ch, GPIO.HIGH)
            # time.sleep(5)
            
        elif (not gp.input(soil_sensor))==1:
            print('\n Soil is Dry - turn on pump\n')
            GPIO.setup(relay_ch, GPIO.OUT)
            GPIO.output(relay_ch, GPIO.LOW)
            # time.sleep(5)

    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
        time.sleep(2.0)
        continue
    except Exception as error:
        GPIO.cleanup()
        dhtDevice.exit()
        raise error
    except KeyboardInterrupt:  
        GPIO.cleanup()
    time.sleep(5.0)

