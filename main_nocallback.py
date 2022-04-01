from datetime import date, datetime
from decimal import Decimal

import functions
import threading

from digi import xbee
from digi.xbee.devices import XBeeDevice
from digi.xbee.io import IOLine, IOMode
from time import sleep

from digi.xbee.models.status import NetworkDiscoveryStatus

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

#sampling rate in seconds
#deprecated, use upload_interval
SAMPLING_RATE=15

first_remote=second_remote=third_remote=None
threshold=20
duty_time=5
upload_interval=15
mode=True
fan_ison=False
upload=False
#internal bool var to check if pump is running (auto mode)
#set to False to let the pump run on code start-up
pump_duty=True

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
    global pump_duty
    if pump_duty:
        print('Water pump is already running!')
    else:
        pump_duty=True
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_LOW)
        sleep(d_t)
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)
        print('Water pump off after {0} seconds'.format(d_t))
        pump_duty=False

def discover_remote_device(network, device):
    device_list=[]

    try:
        network.set_deep_discovery_timeouts(20)
        network.clear()

        def callback_device_found(remote):
            print('Device discovered: %s' % remote)
            device_list.append(remote.get_node_id())

        def callback_discovery_over(status):
            if status==NetworkDiscoveryStatus.SUCCESS:
                print('Discovery process finished successfully')
            else:
                print('Error: %s' % status.description)
        
        network.add_device_discovered_callback(callback_device_found)
        network.add_discovery_process_finished_callback(callback_discovery_over)

        network.start_discovery_process()

        while network.is_discovery_running():
            sleep(1)
    finally:
        if device is not None and device.is_open():
            print('All discovered nodes: ', sorted(device_list))
            return sorted(device_list)

def connect_remote_device(network, devices):
    global first_remote, second_remote, third_remote

    print("Connecting device")

    first_remote=network.discover_device(devices[0])
    second_remote=network.discover_device(devices[1])
    third_remote=network.discover_device(devices[2])

    remote_devices=[first_remote, second_remote, third_remote]

    if remote_devices is None:
        print("Error: nodes ids not found")
        exit(1)

    first_remote.set_dest_address(local_device.get_64bit_addr())
    first_remote.set_io_configuration(LINE_ONE, IOMode.ADC)

    second_remote.set_dest_address(local_device.get_64bit_addr())
    second_remote.set_io_configuration(LINE_TWO, IOMode.ADC)

    third_remote.set_io_configuration(DIGITAL_OUT_ZERO, IOMode.DIGITAL_OUT_HIGH)

    for rem_dev in remote_devices:
        print("Device connected: ", rem_dev)

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

    if hum_converted < 50 and pump_duty==False:
        pump_thread = threading.Thread(target=pump_callback, args=(duty_time,))
        pump_thread.start()
        print('Water pump (should be) running')
    
    print('--')
    
try:
    print("Read and upload data")
    local_device.open()
    local_device.flush_queues()
    zigbee_network=local_device.get_network()
    print(local_device.get_protocol())

    discovered_devices=discover_remote_device(zigbee_network, local_device)
    connect_remote_device(zigbee_network, discovered_devices)

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
