# This is the Python code for the final project of ECE-M119 class. This code is
# Raspberry Pi 3 


#Importing the different packages required for the project like BluePy, azure
#Numpy CSV
import bluepy.btle
from bluepy.btle import Scanner, DefaultDelegate, ScanEntry, Peripheral, AssignedNumbers
import struct
import time
import ntplib
import random
import os, uuid, sys
from azure.storage.blob import BlockBlobService, PublicAccess
import threading
import numpy as np  
import pandas as pd 
import csv


# Function for sending data to Hexiwear after the user requests the data of 
#the other members in the family
# The different users data are stored and updated in different CSV fileincsv
# We also perform basic analytics on the data 
def sendDatatoHexi():
    
    filename = "./datapost.csv"
    if flag==1:
        filename='./datapost.csv'
    elif flag==2:
        filename='./data2post.csv' 
    elif flag==3:
        filename='./data3post.csv' 
    f = open(filename)
    csv_f = csv.reader(f)
    for row in csv_f:
        mean_hr=row[0]
        max_hr=row[1]
        min_hr=row[2]
        steps=row[3]
    
    tempS = "%s:%s:%s:%s" % (mean_hr,max_hr,min_hr,steps)

    if len(tempS) < 20:
        i = len(tempS)
        while i < 20:
            tempS = tempS + '_'
            i = i+1
    print str(len(tempS)) + tempS
    return tempS


# pushing the data that we're changing up to the cloud, The blob storage is
# used to get the data in terms of files
    try:
        # Create the BlockBlockService that is used to call the Blob service for the storage account
        block_blob_service = BlockBlobService(account_name='luluhexiwear',account_key='UvcSpRM59hEC22DYnRAzd6HZOlHG7RBsseZw8XvDrOef+2JRg2Q/N79DBRWrPK1mgNkv5TxMUPk5lTU+8Op7Ng==')
        container_name ='hexiweardata'
        local_path = os.path.expanduser("./")
        local_file_name ="data.txt"
        full_path_to_file =os.path.join(local_path, local_file_name)
        print("Temp file = " + full_path_to_file)
        print("\nUploading to Blob storage as blob" + local_file_name)
        block_blob_service.create_blob_from_path(container_name, local_file_name, full_path_to_file)
    except Exception as e:
        print(e)


#Function that downloads the data from cloud peridodically and save it locally
def DownloadData():
    block_blob_service = BlockBlobService(account_name='luluhexiwear', account_key='UvcSpRM59hEC22DYnRAzd6HZOlHG7RBsseZw8XvDrOef+2JRg2Q/N79DBRWrPK1mgNkv5TxMUPk5lTU+8Op7Ng==')
    local_path=os.path.expanduser("./")

    local_file_name=["data.txt","data2.txt","data3.txt"]
    container_name ='hexiweardata'
    for file_name in local_file_name:
        full_path_to_file =os.path.join(local_path, file_name)
        full_path_to_file2 = os.path.join(local_path, str.replace(file_name ,'.txt', '_DOWNLOADED.txt'))
        print("\nDownloading blob to " + full_path_to_file2)
        block_blob_service.get_blob_to_path(container_name, file_name, full_path_to_file2)
        downloadfile = os.path.join(str.replace(file_name ,'.txt', '_DOWNLOADED.txt'))
        txt = np.loadtxt(downloadfile ,delimiter = ',')  
        txtDF = pd.DataFrame(txt)  
        fileincsv  = os.path.join(str.replace(file_name ,'.txt', '.csv'))
        txtDF.to_csv(fileincsv,index=False)
        colnames = ['heartrate','steps']
        data = pd.read_csv(fileincsv, names=colnames)
        heartrate = data.heartrate.tolist()
        steps = data.steps.tolist()
        mean_heart = str(int(np.mean(heartrate)))
        max_heart = str(int(np.max(heartrate)))
        min_heart = str(int(np.min(heartrate)))
        steps_for_now = str(int(np.max(steps)))
        postdatafile = os.path.join(str.replace(file_name ,'.txt', 'post.csv'))
        with open(postdatafile, 'w') as csvfile:

            fieldnames = ['mean_heart', 'max_heart', 'min_heart','steps_for_now']
            writer = csv.DictWriter(csvfile,fieldnames)
            writer.writerow({'mean_heart':mean_heart,'max_heart':max_heart, 'min_heart':min_heart,'steps_for_now':steps_for_now})



# lastHeartRate = 80
# we weren't able to get the heart rate calculation and connection established
# so we generate random values for the heart rate
def getHeartRate():
    global lastHeartRate 
    lastHeartRate= lastHeartRate + random.randint(-5,5)
    return lastHeartRate


def addDataToFile(steps, hr):
    txt_file = open('data.txt','w')
    txt_file.write("%u, %u" % (hr, steps))
    txt_file.close()


# This is a delegate for receiving BTLE eventsfrom hexiwear
# This class contains an Event Handler, discovery and method to obtain 
# notifications
class BTEventHandler(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
    	pass

    def handleNotification(self, cHandle, data):
    	# Only print the value when the handle is 40 (the battery characteristic)
        if cHandle == 40:
            steps, = struct.unpack('B', data)
            addDataToFile(steps, getHeartRate())

        if cHandle == 101:
            global flag 
            message = struct.unpack('BBBBBBBBBBBBBBBBBBBB', data)
            flag = message[1]

# Function to connect to Hexiwear
def connectHexiwear(peripheral, mac):
    success = False
    while not success:
        try:
            peripheral.connect(mac)
            print mac + " connected successfully"
            success = True
        except bluepy.btle.BTLEException:
            pass


# this function repeatedly tries to get the characteristic to write
# to from hexiwear, mind that if getCharacteristics itself fails,
# that means that the connection has been lost and you have to
# reconnect using connectHexiwear
def getThoseCharacteristics(peripheral, mac):
    num = 1
    while True:
        try:
            print mac + ' trying to get characteristics for the %dth time' % num
            c = peripheral.getCharacteristics(uuid='2031')[0]
            alert = HEXI1.getCharacteristics(uuid="2032")[0]
            alert_desc = alert.getDescriptors(forUUID=0x2902)[0]
            alert_desc.write(b"\x01", True)
            print mac + ' got characteristics!'
            return c

        # whenever you fail, you need to reconnect the hexiwear
        except bluepy.btle.BTLEException:
            num = num + 1
            connectHexiwear(peripheral, mac)

# function to get characteristics based on detecting the uuid
# If there is a failure to get connection, catch the exception and Connect 
# hexiwear            

                        
def getSpecificCharacteristic(peripheral, mac, id):
    while True:
        try:
            c = peripheral.getCharacteristics(uuid=id)[0]
            print mac + ' got characteristic ' + id
            return c

        # whenever you fail, you need to reconnect the hexiwear
        except bluepy.btle.BTLEException:
            connectHexiwear(peripheral, mac)


def writeTimeToCharacteristic(chars, peripheral, mac):
    success = False
    num = 1
    while not success:
        try:
            print mac + ' trying to write %s with length %d... for the %dth time' % (sendDatatoHexi(), len(sendDatatoHexi()),num)
            chars.write(sendDatatoHexi(), True)
            success = True
            print mac + ' successfully wrote'
        except bluepy.btle.BTLEException:
            num = num + 1
            chars = getThoseCharacteristics(peripheral, mac)

#Function to download Data 
def writeIndefinitely(peripheral, mac):
    # connectHexiwear(peripheral, mac)
    # chars = getThoseCharacteristics(peripheral, mac)

    # send time indefinitely
    while True:
        DownloadData()
        time.sleep(10)


def talkToHexi(peripheral, mac):
    # in a loop that runs forever
    #   1. be constantly receiving heart rate and steps, updating the data file
    #   2. be constantly receiving alerts from button presses
    #   3. whenever a button is pressed, respond with the correct data
    #   4. every once in a while, re-download the data from Azure
    #   5. every once in a while, upload that changes to your data to Azure

    # Infinite loop to receive notifications
    while True:
        try:
            HEXI.waitForNotifications(5.0)
            writeTimeToCharacteristic(chars, peripheral, mac)
        except bluepy.btle.BTLEException:
            connectHexiwear(peripheral, mac)




# maintain the BTLE event handler that processes BLE events
handler = BTEventHandler()

MAC = '00:3B:40:08:00:04'
HEXI = Peripheral().withDelegate(handler)
connectHexiwear(HEXI, MAC)

# get battery characteristic and have it notify the event handle
# when something is written
battery = getSpecificCharacteristic(HEXI, MAC, "2a19")
battery_desc = battery.getDescriptors(forUUID=0x2902)[0]
battery_desc.write(b"\x01", True)

writingDataThread = threading.Thread(target=writeIndefinitely, args=(HEXI,MAC))
writingDataThread.start()

talkToHexi()
