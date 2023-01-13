import time
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D5)
mcp = MCP.MCP3008(spi, cs)
channel = AnalogIn(mcp, MCP.P0)

#Calibraton values
min_moisture = 26880
max_moisture = 65472


while True:
    print('Raw ADC Value: ', channel.value)
    print('ADC Voltage: ' + str(channel.voltage) + 'V')
    moisture = (max_moisture-channel.value)*100/(max_moisture-min_moisture) 
    print("moisture: " + "%.2f" % moisture +"% (adc: "+str(channel.value)+")")

    time.sleep(0.5)