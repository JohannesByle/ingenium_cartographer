#!/bin/bash
import RPi.GPIO as GPIO
import time
import os
import subprocess
import sys

while True:
    #get environment
    #ros = os.environ.get('ROS')
    os.environ.get('PATH')

    #sys.path.append(ros)
    #sys.path.append(cat)
    #print(os.environ)

    #get record to bag file:
    rec = subprocess.Popen("locate record_to_bag.sh", stdout=subprocess.PIPE, shell=True)
    (out,err) = rec.communicate()
    out = str(out)
    out = out[2:len(out)-3]

    #start and stop buttons for data collection
    start = 11
    stop = 13
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(start, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(stop, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    #waiting for start signal
    GPIO.wait_for_edge(start, GPIO.RISING)
    os.system('. /home/ubuntu/ingenium_cartographer/record_to_bag.sh &')
    print('start')

    #waiting for stop button to be pressed. Then run kill part of record script
        #NOTE: Right now, not sure to pass 'n' to script. Just made another script 
    GPIO.wait_for_edge(stop, GPIO.RISING)
    print('stop')


    #os.system('echo %s'%'y')
    os.system('rosnode kill -a &')
    os.system('sleep 5')
    os.system('pkill roscore')

    #while True:
    #    input_state = GPIO.input(11)
    #    if input_state == False:
    #        os.system('put filepath of whatever file you want to be run when the button is pressed')
    #        time.sleep(0.2)

    GPIO.cleanup()
