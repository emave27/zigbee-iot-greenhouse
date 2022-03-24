from datetime import date, datetime
from decimal import Decimal

import functions
import threading

from digi import xbee
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice
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

SAMPLING_RATE=5 #sampling rate in seconds

first_remote=second_remote=third_remote=None
fan_ison=False
on_duty=False
auto=True

local_device=XBeeDevice(SERIAL_PORT, BAUD_RATE)

def reset_digital_out():
    third_remote.set_dio_value(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_HIGH)
    third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)

def check_temp(temp_c, fan_stat):
    global fan_ison
    if temp_c > 20.5 and fan_stat==False:
        fan_ison=True
        print("Fan is on")
        third_remote.set_dio_value(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_LOW)
    elif temp_c < 20.0 and fan_stat==True:
        fan_ison=False
        third_remote.set_dio_value(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_HIGH)
        print("Fan is off")

def pump_callback(duty_time):
    global on_duty
    if on_duty:
        print('Water pump is already running!')
    else:
        on_duty=True
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_LOW)
        sleep(duty_time)
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)
        print("Water pump is off")
        on_duty=False

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
    first_remote.set_io_sampling_rate(SAMPLING_RATE)

    second_remote.set_dest_address(local_device.get_64bit_addr())
    second_remote.set_io_configuration(LINE_TWO, IOMode.ADC)
    second_remote.set_io_sampling_rate(SAMPLING_RATE)

    third_remote.set_io_configuration(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_HIGH)

    for rem_dev in remote_devices:
        print("Device found: ", rem_dev)

def sample_callback(sample, remote, time):
    today=str(date.today())
    now=datetime.now()
    current_time=now.strftime("%H-%M-%S")

    if str(remote.get_64bit_addr()) == FIRST_NODE_ADDRESS:
        print('--')
        temp_c=((sample.get_analog_value(LINE_ONE) * 1200.0/1024.0)-500.0) / 10.0
        #temp_c=((sample.get_analog_value(LINE_ONE)/1023.0*1.2 - 0.5)*100.0)
        print("Temperature is {0} Celsius".format(round(temp_c, 2)))

        functions.upload_data_double(today, current_time, Decimal(temp_c), True)
        check_temp(temp_c, fan_ison)

    elif str(remote.get_64bit_addr()) == SECOND_NODE_ADDRESS:
        print('--')
        humidity=sample.get_analog_value(LINE_TWO)
        hum_converted=functions.convert_interval(int(humidity), MAX, MIN, 100, 0)
        
        print("Humidity is {0}".format(round(hum_converted, 2)))

        functions.upload_data_double(today, current_time, Decimal(humidity), False)
        if hum_converted < 50 and on_duty==False:
            pump_thread = threading.Thread(target=pump_callback, args=(10,))
            pump_thread.start()
            print('Water pump is running')
    
try:
    print("Read and upload data")
    local_device.open()
    local_device.flush_queues()
    print(local_device.get_protocol())
    get_remote_device()

    local_device.add_io_sample_received_callback(sample_callback)
    while auto:
        pass

except KeyboardInterrupt:
    if local_device is not None and local_device.is_open():
        reset_digital_out()
        local_device.del_io_sample_received_callback(sample_callback)
        print('Callback deleted')
        local_device.reset()
        local_device.close()
        print("Execution stopped by the user, device closed and resetted")
