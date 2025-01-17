#!/usr/bin/python

import io         # used to create file streams
from io import open
import fcntl      # used to access I2C parameters like addresses
from time import strftime
import time # used for sleep delay and timestamps
import string     # helps parse strings
import socket #Server forms the listener socket while client reaches out to the server.
import struct
import sys
import threading #for sending the data to the server
import csv

class AtlasI2C:
    long_timeout = 1.5          # the timeout needed to query readings and calibrations
    short_timeout = .5          # timeout for regular commands
    default_bus = 1             # the default bus for I2C on the newer Raspberry Pis, certain older boards use bus 0
    default_address = 99        # the default address for the sensor
    current_addr = default_address

    def __init__(self, address=default_address, bus=default_bus):
        # open two file streams, one for reading and one for writing
        # the specific I2C channel is selected with bus
        # it is usually 1, except for older revisions where its 0
        # wb and rb indicate binary read and write
        self.file_read = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
        self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

        # initializes I2C to either a user specified or default address
        self.set_i2c_address(address)

    def set_i2c_address(self, addr):
        # set the I2C communications to the slave specified by the address
        # The commands for I2C dev using the ioctl functions are specified in
        # the i2c-dev.h file from i2c-tools
        I2C_SLAVE = 0x703
        fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
        fcntl.ioctl(self.file_write, I2C_SLAVE, addr)
        self.current_addr = addr

    def write(self, cmd):
        # appends the null character and sends the string over I2C
        cmd += "\00"
        self.file_write.write(cmd.encode('latin-1'))

    def read(self, num_of_bytes=5):
        # reads a specified number of bytes from I2C, then parses and displays the result
        res = self.file_read.read(num_of_bytes)         # read from the board
        if type(res[0]) is str:                 # if python2 read
            response = [i for i in res if i != '\x00']
            if ord(response[0]) == 1:             # if the response isn't an error
                # change MSB to 0 for all received characters except the first and get a list of characters
                # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                char_list = list(map(lambda x: chr(ord(x) & ~0x80), list(response[1:])))
                return ''.join(char_list)     # convert the char list to a string and returns it
            else:
                return "Error " + str(ord(response[0]))
                
        else:                                   # if python3 read
            if res[0] == 1: 
                # change MSB to 0 for all received characters except the first and get a list of characters
                # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
                char_list = list(map(lambda x: chr(x & ~0x80), list(res[1:])))
                return ''.join(char_list)     # convert the char list to a string and returns it
            else:
                return "Error " + str(res[0])


    def close(self):
        self.file_read.close()
        self.file_write.close()

    def list_i2c_devices(self):
        prev_addr = self.current_addr # save the current address so we can restore it after
        i2c_devices = []
        for i in range (0,128):
            try:
                self.set_i2c_address(i)
                self.read(1)
                i2c_devices.append(i)
            except IOError:
                pass
        self.set_i2c_address(prev_addr) # restore the address we were using
        return i2c_devices

    def query(self, string):
        # write a command to the board, wait the correct timeout, and read the response
        self.write(string)
        
        # the read and calibration commands require a longer timeout
        if((string.upper().startswith("R")) or 
           (string.upper().startswith("1"))):
            time.sleep(self.long_timeout)
        elif((string.upper().startswith("SLEEP"))):
            return "sleep mode"
        else:
            time.sleep(self.short_timeout)
            
        return self.read()

    
# creates the I2C port object, specify the address or bus if necessary, d stands for device
dpH = AtlasI2C(99) #pH
dORP = AtlasI2C(98) #ORP
dTemp = AtlasI2C(102) #Temperature
dDO = AtlasI2C(97) #D.O
dEC = AtlasI2C(100) #E.C




# #send data through websockets, to use for NodeRed
# server_ip = "" # Symbolic name meaning all available interfaces
# server_port = 9999 # Arbitrary non-privileged port
# server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# print ('Socket created')


# try: # Bind socket to local host and port
#     server.bind((server_ip,server_port))
# except socket.error as msg:
#     print ('Bind error: ' + str(msg[0]) + ' Message ' + msg[1])
#     sys.exit()

# print ("[*] UDP_Server started on %s:%s" % server.getsockname())
while True: # receive data from client (data, addr)
    # data, addr = server.recvfrom(1024)
    #to give the value of the device
    pH = dpH.query("R") #pH
    ORP = dORP.query("R") #ORP
    Temp = dTemp.query("R") #Temperature
    DO = dDO.query("R") #D.O
    EC = dEC.query("R") #E.C
    result = pH + ", " + ORP + ", " + Temp + ", " + DO + ", " + EC
    print(result)
    # addr1 = (addr[0], 9998)
    # #addr[1]=9999 #we send send the response to another port
    # # send back a response: value ASCII encoded
    # server.sendto(result,addr1)

    with open("/home/pi/ProTerra/gauge/Test_OneWire/cpu.csv", "a") as log:
        log.write("{0},{1},{2},{3},{4},{5},\n".format(strftime("%Y-%m-%d %H:%M:%S"),float(pH),float(ORP),float(Temp),float(DO),float(EC)))
        time.sleep(5)

#   # main loop
#   while True:
#       user_cmd = real_raw_input("Enter command: ")

#       if user_cmd.upper().startswith("LIST_ADDR"):
#           devices = device.list_i2c_devices()
#           for i in range(len (devices)):
#               print( devices[i])

#       # address command lets you change which address the Raspberry Pi will poll
#       elif user_cmd.upper().startswith("ADDRESS"):
#           addr = int(user_cmd.split(',')[1])
#           device.set_i2c_address(addr)
#           print("I2C address set to " + str(addr))

#       # continuous polling command automatically polls the board
#       elif user_cmd.upper().startswith("POLL"):
#           delaytime = float(string.split(user_cmd, ',')[1])

#           # check for polling time being too short, change it to the minimum timeout if too short
#           if delaytime < AtlasI2C.long_timeout:
#               print("Polling time is shorter than timeout, setting polling time to %0.2f" % AtlasI2C.long_timeout)
#               delaytime = AtlasI2C.long_timeout

#           # get the information of the board you're polling
#           info = string.split(device.query("I"), ",")[1]
#           print("Polling %s sensor every %0.2f seconds, press ctrl-c to stop polling" % (info, delaytime))

#           try:
#               while True:
#                   print(device.query("R"))
#                   time.sleep(delaytime - AtlasI2C.long_timeout)
#           except KeyboardInterrupt:       # catches the ctrl-c command, which breaks the loop above
#               print("Continuous polling stopped")

#       # if not a special keyword, pass commands straight to board
#       else:
#           if len(user_cmd) == 0:
#               print( "Please input valid command.")
#           else:
#               try:
#                   print(device.query(user_cmd))
#               except IOError:
#                   print("Query failed \n - Address may be invalid, use List_addr command to see available addresses")


# if __name__ == '__main__':
#   main()
