from datetime import date, datetime
from decimal import Decimal

import functions
import threading

from digi import xbee
from digi.xbee.devices import XBeeDevice
from digi.xbee.io import IOLine, IOMode
from time import sleep

from digi.xbee.models.address import XBee64BitAddress

MIN=360
MAX=1023

SERIAL_PORT="/dev/ttyS0"
BAUD_RATE=115200
REMOTE_NODE_IDS=["FirstR", "SecondR", "ThirdR"]
FIRST_NODE_ADDRESS=""
SECOND_NODE_ADDRESS=""
THIRD_NODE_ADDRESS=""

LINE_ONE=IOLine.DIO3_AD3
LINE_TWO=IOLine.DIO1_AD1
DIGITAL_OUT_ZERO=IOLine.DIO0_AD0
DIGITAL_OUT_ONE=IOLine.DIO1_AD1

SAMPLING_RATE=15 #sampling rate in seconds

first_remote=second_remote=third_remote=None
threshold=20
duty_time=5
upload_interval=15
mode=True
fan_ison=False
pump_ison=False
upload=False

local_device=XBeeDevice(SERIAL_PORT, BAUD_RATE)

def reset_digital_out():
    third_remote.set_dio_value(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_HIGH)
    third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)

def check_temp(temp_c, fan_stat):
    global fan_ison
    if temp_c > threshold and fan_stat==False:
        fan_ison=True
        print("Fan is on")
        third_remote.set_dio_value(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_LOW)
    elif temp_c < (threshold+0.5) and fan_stat==True:
        fan_ison=False
        third_remote.set_dio_value(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_HIGH)
        print("Fan is off")

def pump_callback(d_t):
    global pump_ison
    if pump_ison:
        print('Water pump is already running!')
    else:
        pump_ison=True
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_LOW)
        sleep(d_t)
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)
        print('Water pump off after {0} seconds'.format(d_t))
        pump_ison=False

def get_remote_device():
    global first_remote, second_remote, third_remote
    xbee_network=local_device.get_network()

    print("Discovering device")

    first_remote=xbee_network.discover_device(REMOTE_NODE_IDS[0])
    second_remote=xbee_network.discover_device(REMOTE_NODE_IDS[1])
    third_remote=xbee_network.discover_device(REMOTE_NODE_IDS[2])

    remote_devices=[first_remote, second_remote, third_remote]

    if remote_devices is None:
        print("Error: nodes ids not found")
        exit(1)

    first_remote.set_dest_address(local_device.get_64bit_addr())
    first_remote.set_io_configuration(LINE_ONE, IOMode.ADC)
    #first_remote.set_io_sampling_rate(SAMPLING_RATE)

    second_remote.set_dest_address(local_device.get_64bit_addr())
    second_remote.set_io_configuration(LINE_TWO, IOMode.ADC)
    #second_remote.set_io_sampling_rate(SAMPLING_RATE)

    third_remote.set_io_configuration(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_HIGH)

    for rem_dev in remote_devices:
        print("Device found: ", rem_dev)

def get_data():
    today=str(date.today())
    now=datetime.now()
    current_time=now.strftime("%H-%M-%S")

    temp_c=((first_remote.get_adc_value(LINE_ONE) * 1200.0/1024.0)-500.0) / 10.0
    humidity=second_remote.get_adc_value(LINE_TWO)
    hum_converted=functions.convert_interval(int(humidity), MAX, MIN, 100, 0)

    print('--')
    print("Temperature is {0}C".format(round(temp_c, 2)), "Humidity is {0}%".format(round(hum_converted, 2)))

    check_temp(temp_c, fan_ison)
    functions.upload_data_single(today, current_time, Decimal(temp_c), Decimal(humidity), upload)

    if hum_converted < 50 and pump_ison==False:
        pump_thread = threading.Thread(target=pump_callback, args=(duty_time,))
        pump_thread.start()
        print('Water pump (should be) running')
    
    print('--')
    
try:
    print("Read and upload data")
    local_device.open()
    local_device.flush_queues()
    print(local_device.get_protocol())
    get_remote_device()

    while True:
        threshold, duty_time, upload_interval, mode, _, _, upload=functions.get_settings() 
        if mode: #auto
            get_data()
            sleep(upload_interval)

except KeyboardInterrupt:
    if local_device is not None and local_device.is_open():
        reset_digital_out()
        
        local_device.reset()
        local_device.close()
        print("Execution stopped by the user, device closed and resetted")
