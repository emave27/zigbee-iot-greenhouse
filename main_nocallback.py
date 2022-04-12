from datetime import date, datetime
from decimal import Decimal
from time import sleep
import threading
import struct


#import external files
import functions
from mqttpi_class import PiMQTT

#import from the digi xbee python library
from digi.xbee.util import utils
from digi.xbee.devices import XBeeDevice
from digi.xbee.io import IOLine, IOMode

from digi.xbee.models.status import NetworkDiscoveryStatus

MIN=360
MAX=1023

#raspberry pi GPIO serial
SERIAL_PORT=""
BAUD_RATE=115200

#deprecated, nodes are automatically discovered by the script
REMOTE_NODE_IDS=["FirstR", "SecondR", "ThirdR"]
FIRST_NODE_ADDRESS=""
SECOND_NODE_ADDRESS=""
THIRD_NODE_ADDRESS=""

#remote xbee IO line
LINE_ONE=IOLine.DIO3_AD3 #first node, temperature
LINE_TWO=IOLine.DIO1_AD1 #second node, soil humidity

#third node digital output
DIGITAL_OUT_ONE=IOLine.DIO1_AD1 #pump
DIGITAL_OUT_TWO=IOLine.DIO2_AD2 #fan

#deprecated, use upload_interval
SAMPLING_RATE=15 #sampling rate in seconds

#variables to handle remote nodes
first_remote=second_remote=third_remote=None

#default values
threshold=20
hum_thresh=50
duty_time=5
upload_interval=10
mode=True #True --> auto, False --> manual
fan_ison=False
pump_ison=False
upload=False
reset=True
mqtt_pi=None

#internal bool var to check if pump is running (auto mode)
#if True, the pump will never start
#set to False to let the pump run on code start-up
pump_duty=False

#initialize the local device (coordinator)
local_device=XBeeDevice(SERIAL_PORT, BAUD_RATE)

#function used to reset the remote digital output
def reset_digital_out():
    #check the (global) reset variable status
    global reset
    if reset:
        third_remote.set_dio_value(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_HIGH)
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)
        print('Digital output resetted')
        reset=False
    else:
        print('No need to reset')

#function to manually control fan and pump (manual mode)
def manual_control(fan, pump):
    if fan and pump:
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_LOW)
        third_remote.set_dio_value(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_LOW)
    if fan and pump==False:
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)
        third_remote.set_dio_value(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_LOW)
    if fan==False and pump:
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_LOW)
        third_remote.set_dio_value(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_HIGH)
    if fan==False and pump==False:
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)
        third_remote.set_dio_value(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_HIGH)
        
#function to activate the fan if temperature is above a certain threshold
#fan_ison (global) is used to check if the fan is already running
def check_temp(temp_c):
    global fan_ison
    if temp_c > threshold and fan_ison==False:
        fan_ison=True
        print("Fan is on")
        third_remote.set_dio_value(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_LOW)
    elif temp_c < (threshold+0.5) and fan_ison==True:
        fan_ison=False
        third_remote.set_dio_value(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_HIGH)
        print("Fan is off")

#function to activate the water pump, pump_duty variable is used to check if the
#pumpm is already running
def pump_callback(d_t):
    global pump_duty
    if pump_duty:
        print('Water pump is already running!')
    else:
        pump_duty=True
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_LOW) #start
        sleep(d_t) #sleep for a defined time
        third_remote.set_dio_value(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH) #stop
        print('Water pump off after {0} seconds'.format(d_t))
        pump_duty=False

#function to automatically discover nodes in the network
def discover_remote_device(network, device):
    device_list=[]

    try:
        network.set_deep_discovery_timeouts(20)
        network.clear()

        #append device to device_list list if a remote device is found
        def callback_device_found(remote):
            print('Device discovered: %s' % remote)
            device_list.append(remote.get_node_id())

        #discovery over callback
        def callback_discovery_over(status):
            if status==NetworkDiscoveryStatus.SUCCESS:
                print('Discovery process finished successfully')
            else:
                print('Error: %s' % status.description)
        
        #add the callback and start discovery process
        network.add_device_discovered_callback(callback_device_found)
        network.add_discovery_process_finished_callback(callback_discovery_over)
        network.start_discovery_process()

        while network.is_discovery_running():
            sleep(1)
    finally:
        if device is not None and device.is_open():
            #show and return all the discovered nodes
            print('Nodes discovered: ', sorted(device_list))
            return sorted(device_list)

#connect the discovered nodes
def connect_remote_device(network, devices):
    #using the global variables
    global first_remote, second_remote, third_remote

    print("Connecting device")

    first_remote=network.discover_device(devices[0])
    second_remote=network.discover_device(devices[1])
    third_remote=network.discover_device(devices[2])

    remote_devices=[first_remote, second_remote, third_remote]
    
    #check the ADC voltage reference, 00 --> 1.25V, 01 --> 2.5V, 02 --> VCC
    #set to 02 (if needed) for a more accurate sensor read
    #first_remote.set_parameter('AV', utils.hex_string_to_bytes('02'))
    #second_remote.set_parameter('AV', utils.hex_string_to_bytes('02'))
    av1=utils.hex_to_string(first_remote.get_parameter('AV'))
    av2=utils.hex_to_string(second_remote.get_parameter('AV'))
    print('First and second node analog reference: ', av1, av2)

    if remote_devices is None:
        print("Error: nodes ids not found")
        exit(1)

    #set the destination address (coordinator address) for the remte devices and
    #initialize the remote IO lines
    first_remote.set_dest_address(local_device.get_64bit_addr())
    first_remote.set_io_configuration(LINE_ONE, IOMode.ADC)

    second_remote.set_dest_address(local_device.get_64bit_addr())
    second_remote.set_io_configuration(LINE_TWO, IOMode.ADC)

    third_remote.set_io_configuration(DIGITAL_OUT_ONE, IOMode.DIGITAL_OUT_HIGH)
    third_remote.set_io_configuration(DIGITAL_OUT_TWO, IOMode.DIGITAL_OUT_HIGH)

    for rem_dev in remote_devices:
        print("Device connected: ", rem_dev)

#function to get data from the remote nodes and upload to the DB
def get_data(is_auto):
    #get the current date and time in hour-minutes-seconds format
    today=str(date.today())
    now=datetime.now()
    current_time=now.strftime("%H-%M-%S")

    #read and convert the temperature from the remote node (first node)
    temp_c=((first_remote.get_adc_value(LINE_ONE) * 3200.0/1024.0)-500.0) / 10.0
    temp_r=round(temp_c, 2)

    #read and convert the humidity value from the remote node (first node)
    humidity=second_remote.get_adc_value(LINE_TWO)
    hum_converted=functions.convert_interval(int(humidity), MAX, MIN, 0, 100)

    print('--') #print the values
    print("Temperature is {0} °C".format(temp_r), "Humidity is {0}%".format(hum_converted))
    
    if is_auto:
        #use check temp function to check if the temperature is above the threshold
        check_temp(temp_r, fan_ison)
        #upload the data to the database
        functions.upload_data_single(today, current_time, Decimal(temp_c), Decimal(humidity), upload)

        #pack the data into a bytearray and send them to the dashboard using MQTT
        data_bytes=struct.pack('ff', temp_r, hum_converted)
        mqtt_pi.send_message('sensors', data_bytes)

        #check the humidity value
        if hum_converted < 0 and pump_duty==False:
            #start the pump callback using a separate thread, without blocking the main thread
            pump_thread=threading.Thread(target=pump_callback, args=(duty_time,))
            pump_thread.daemon=True
            pump_thread.start()
            print('Water pump running')
    
    #pack the data as bytes and send them via MQTT
    data_bytes=struct.pack('ff', temp_r, hum_converted)
    mqtt_pi.send_message('sensors', data_bytes)
    
    print('--')
    
try:
    print("Welcome!")
    #open the local device, clean the queues and get the network
    local_device.open()
    local_device.flush_queues()
    zigbee_network=local_device.get_network()
    #check the protocol
    print(local_device.get_protocol())

    #start node discovering
    discovered_devices=discover_remote_device(zigbee_network, local_device)

    if discovered_devices:
        #connect the remote device (if found)
        connect_remote_device(zigbee_network, discovered_devices)
        mqtt_pi=PiMQTT()
    else:
        #if not, close the local device and exit the script
        print('404: nodes not found')
        local_device.close()
        exit()

    while True:
        mqtt_mode=mqtt_pi.pass_mode()
        if mode==True and mqtt_mode==True: #auto mode
            #get the settings
            threshold, duty_time, upload_interval, _, upload=functions.get_settings()
            print('--\nAutomatic')
            get_data() #call get data (main function)
            sleep(upload_interval) #wait time defined by the user
        else: #manual mode, data will not be uploaded
            print('--\nManual')
            reset_digital_out() #reset (once) the digital output
            reset=False
            fan_man, pump_man=mqtt_pi.pass_data() #get the fan and pump stat from mqtt topic
            manual_control(fan_man, pump_man) #call manual_control() to start/stop the fan or the pump 
            sleep(5)

except KeyboardInterrupt: #handle KeyboardInterrupt event (ctrl+c)
    if local_device is not None and local_device.is_open():
        #reset the digital output and close the local device
        reset=True
        reset_digital_out()
        local_device.reset()
        local_device.close()
        #close mqtt connection
        mqtt_pi.on_keyboardinterrupt()
        
        print("Execution stopped by the user, device closed and resetted")
