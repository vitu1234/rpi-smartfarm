import pymysql
import pymysql.cursors

import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import RPi.GPIO as gp  
import datetime

#mcp module and soil sensor

import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn

#set soil sensor values
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D5)
mcp = MCP.MCP3008(spi, cs)
channel = AnalogIn(mcp, MCP.P0) #soil sensor connected to channel 0

#Calibraton values
min_moisture = 26880
max_moisture = 65472

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT11(board.D4) 
relay_ch = 17
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_ch, GPIO.OUT)

# db = pymysql.connect("192.168.13.200:3306","all","","iot-project" )
# Connect to the database


while True:
    try:
        connection = pymysql.connect(host='192.168.13.200',
                             user='root1',
                             password='1',
                             database='iot-project',
                             cursorclass=pymysql.cursors.DictCursor)
        temperature_c = dhtDevice.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dhtDevice.humidity
        moisture = (max_moisture-channel.value)*100/(max_moisture-min_moisture) 
        adc_value = channel.value
        print("Temp: {:.1f} F / {:.1f} C    Humidity: {}% ".format(temperature_f, temperature_c, humidity))
        
        print('Raw ADC Value: ', channel.value)
        print('ADC Voltage: ' + str(channel.voltage) + 'V')
        print("moisture: " + "%.2f" % moisture +"% (adc: "+str(channel.value)+")")
        moisture2 = ""
        if moisture >= 100:
            moisture2 = 100
        else:
            moisture2 = "" + "%.2f" % moisture
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = "INSERT INTO `sensor_readings` (`temperature`, `humidity`, `soil_moisture`, `adc_value`) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (temperature_c, humidity, moisture2, adc_value))
                connection.commit()

            # connection is not autocommit by default. So you must commit to save
            # your changes.
            # connection.commit()

            # with connection.cursor() as cursor:
                # Read a single record
                # sql = "SELECT `id`, `password` FROM `users` WHERE `email`=%s"
                # cursor.execute(sql, ('webmaster@python.org',))
                # result = cursor.fetchone()
                # print(result)
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
        time.sleep(2.0)
        continue
    except Exception as error:
        GPIO.cleanup()
        dhtDevice.exit()
        raise error

    time.sleep(30.0)
