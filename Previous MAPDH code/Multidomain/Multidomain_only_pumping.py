# WORKING CODE
# # -*- coding: utf-8 -*-
# """
# author: Leo
# """
# from pycromanager import Bridge
# import pandas as pd
# import time

# bridge = Bridge(convert_camel_case=False)
# core = bridge.get_core()

# #%% Turn Arduino shutter ON:
# core.setProperty('Arduino-Shutter','OnOff',1)
# #First 0: closest to you, last 0: furthest away
# d = {'s1': '00001', 's2': '00010','s3': '000100', 's4': '01000', 's5': '10000'}
# d = {'s0': 0, 's1': 1, 's2': 2,'s3': 4, 's4': 8, 's5': 16}
# df = pd.Series(data=d)

# #%% Functions: Useful to automate
# def valve_on(switch):
#     # Switch must be something like 1,2,3,4,5,etc.
#     core.setProperty('Arduino-Switch','State',int(df.get(switch)))

# def valve_off(switch2='s0'):
#     # Note that only valve_off() turns off the valves.
#     core.setProperty('Arduino-Switch','State',int(df.get(switch2)))
    
# def valve_timer(switch, wait):
#     # Switch must be something like 1,2,3,4,5,etc.
#     core.setProperty('Arduino-Switch','State',int(df.get(switch)))
#     for m in range(0, wait):
#         time.sleep(1)
#     valve_off()
# #%% Cyclic valve ON & OFF
# valves = ('s0', 's1', 's2', 's3', 's4')
# #inks = ('SKIP','0 nM protein', '100 nM protein', 'KOH', '1X buffer')
# inks = ('SKIP','Txn + 0nM P', 'Txn + 50nM P', 'Wash (KOH)', 'Wash (Buffer)')

# initial = 0
# cycles = 2 #Number of cycles (1 cycle = pumping X amount of time for ALL inks)
# print('Pumping %d cycles during this run...' % cycles)

# while initial < cycles: 
#     for i in range(1, 5):
#         print('Starting %s flow for 1 hour' % inks[i])
#         valve_timer(valves[i], 3600) # seconds
#         print('Waiting for 1 second...')
#         time.sleep(1) # seconds
#     initial += 1
#     print('Cycle # %d completed...' % cycles)

# print("Experiment concluded...")
# print("PLEASE REMOVE MICROFLUIDIC DEVICE")

#%% WORKING CODE
import numpy as np
from pycromanager import Bridge
import pandas as pd
import time
import cv2
import os
from datetime import date
import glob
from PIL import Image

bridge = Bridge(convert_camel_case=False)
core = bridge.get_core()

# Turn Arduino shutter ON:
core.setProperty('Arduino-Shutter', 'OnOff', 1)
# First 0: closest to you, last 0: furthest away
d = {'s1': '00001', 's2': '00010', 's3': '000100', 's4': '01000', 's5': '10000'}
d = {'s0': 0, 's1': 1, 's2': 2, 's3': 4, 's4': 8, 's5': 16}
df = pd.Series(data=d)

# Functions: Useful to automate
def valve_on(switch):
    # Switch must be something like 1,2,3,4,5,etc.
    core.setProperty('Arduino-Switch', 'State', int(df.get(switch)))

def valve_off(switch2='s0'):
    # Note that only valve_off() turns off the valves.
    core.setProperty('Arduino-Switch', 'State', int(df.get(switch2)))

def valve_timer(switch, wait):
    # Switch must be something like 1,2,3,4,5,etc.
    core.setProperty('Arduino-Switch', 'State', int(df.get(switch)))
    for m in range(0, wait):
        time.sleep(1)
    valve_off()

def take_image(core, folder_path, current_time):
    global image_counter
    core.snapImage()
    tagged_image = core.getTaggedImage()
    pixels = np.reshape(tagged_image.pix, newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']])
    pixels = (pixels / np.max(pixels) * 255).astype(np.uint8)  # Convert to 8-bit grayscale
    image_path = os.path.join(folder_path, f"{int(current_time)}.tif")  # Round down current_time to nearest integer
    cv2.imwrite(image_path, pixels)
    print(f"Capturing image at {int(current_time)} seconds...")
    image_counter += 1

def capture_images(total_time, interval, valve_pumping_time, filename=None, save_path="."):
    global image_counter
    start_time = time.time()
    last_image_time = 0  # Keep track of the time when the last image was taken
    valve_on_time = 0  # Keep track of the time when the first valve was opened

    if filename is None:
        folder_name = date.today().strftime("%m-%d-%Y")  # Default to current date
    else:
        folder_name = filename
    folder_path = os.path.join(save_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)  # Create folder if it doesn't exist

    # Take initial image before the first valve goes on
    take_image(core, folder_path, 0)
    time.sleep(interval)  # Wait for the interval before starting the pump

    while time.time() - start_time < total_time:
        for i in range(1, 5):
            print(f'Opening valve {i} for {valve_pumping_time} seconds...')
            valve_on_time = time.time()  # Record the time when the valve was opened
            valve_on(f"s{i}")
            
            while time.time() - valve_on_time < valve_pumping_time:
                current_time = time.time()
                if current_time - last_image_time >= 5:
                    take_image(core, folder_path, current_time - start_time)
                    last_image_time = current_time  # Update the last image time

            valve_off()

    print(f"Total images captured: {image_counter}")
  
# Cyclic valve ON & OFF
valves = ('s0', 's1', 's2', 's3', 's4')
inks = ('SKIP', 'Txn + 0nM P', 'Txn + 50nM P', 'Wash (KOH)', 'Wash (Buffer)')

initial = 0
cycles = 1  # Number of cycles (1 cycle = pumping X amount of time for ALL inks)
valve_pumping_time = 10  # Time each valve will stay ON (seconds)
image_counter = 0
file_name = "Test2"
path = "E:\\C\\Users\\schulmanlab\\Johns Hopkins\\Schulman Lab - Microscope 2\\Leo\\Python Code\\Needs editing\\Multidomain (Pumping and image recording)\\Tests"
#path_i = "E:\\C\\Users\\schulmanlab\\Johns Hopkins\\Schulman Lab - Microscope 2\\Leo\\Python Code\\Needs editing\\Multidomain (Pumping and image recording)\\Tests\\Test2"

while initial < cycles:
    print(f'Starting cycle #{initial + 1}...')
    capture_images(40, 5, valve_pumping_time, file_name, save_path=path)
    initial += 1
    print('Cycle completed...')

print("Experiment concluded...")
print("PLEASE REMOVE MICROFLUIDIC DEVICE")

#%%


