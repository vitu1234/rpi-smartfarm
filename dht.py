
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
import RPi.GPIO as gp  

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

gp.setmode(gp.BOARD)  
gp.setup(8,gp.IN)  


# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT11(board.D4) 
relay_ch = 17


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
        
        print('\nSoil Moisture\n')
        if (GPIO.input(8))==0:
            print('\n Soil is Wet - turn off pump\n')
            GPIO.setup(relay_ch, GPIO.OUT)
            GPIO.output(relay_ch, GPIO.HIGH)
            time.sleep(5)
            
        elif (GPIO.input(8))==1:
            print('\n Soil is Dry - turn on pump\n')
            GPIO.setup(relay_ch, GPIO.OUT)
            GPIO.output(relay_ch, GPIO.LOW)
            time.sleep(5)

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

