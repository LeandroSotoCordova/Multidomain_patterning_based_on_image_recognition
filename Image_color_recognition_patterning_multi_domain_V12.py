# -*- coding: utf-8 -*-
"""
Created on Mon May 5 12:56:11 2025

@author: Leo
"""

from pycromanager import Bridge
import matplotlib.pyplot as plt
import numpy as np
from skimage.transform import resize
import time
from PIL import Image
import pandas as pd

h = 684
w = 608
radius = 100

#%% Initialization:
bridge = Bridge(convert_camel_case=False)
core = bridge.get_core()
DMD = core.getSLMDevice()
core.setProperty(DMD, 'TriggerType', 1)
# core.setSLMPixelsTo(DMD,100) #show all pixels
h = core.getSLMHeight(DMD)
w = core.getSLMWidth(DMD)
core.setProperty('UserDefinedStateDevice-1', 'Label', 'Patterning ON (dichroic mirror)')
core.setProperty('UserDefinedStateDevice', 'Label', 'BF')
# core.setProperty('HamamatsuHam_DCAM','Binning','2x2')
core.setProperty('UserDefinedShutter-1', 'State', 1)
core.setProperty('UserDefinedShutter', 'State', 1)

# Channel 4: UV LED
core.setProperty('Mightex_BLS(USB)', 'mode', 'NORMAL')
core.setProperty('Mightex_BLS(USB)', 'channel', 1)
core.setProperty(DMD, 'AffineTransform.m00', 0)
core.setProperty(DMD, 'AffineTransform.m01', -0.7988)
core.setProperty(DMD, 'AffineTransform.m02', 1231.7751)
core.setProperty(DMD, 'AffineTransform.m10', 1.1149)
core.setProperty(DMD, 'AffineTransform.m11', 0.0000)
core.setProperty(DMD, 'AffineTransform.m12', -904.0098)
# current set: 0-1000
core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', 0)

#%% Turn Arduino shutter ON:
core.setProperty('Arduino-Shutter', 'OnOff', 1)
# Valve bitmasks
d = {'s0': 0, 's1': 1, 's2': 2, 's3': 4, 's4': 8, 's5': 16}
df = pd.Series(data=d)

#%% Functions: Useful to automate
def valve_on(switch):
    # Switch must be something like 's1','s2','s3','s4','s5'
    core.setProperty('Arduino-Switch', 'State', int(df.get(switch)))

def valve_off(switch2='s0'):
    # Note that only valve_off() turns off the valves.
    core.setProperty('Arduino-Switch', 'State', int(df.get(switch2)))

def valve_timer(switch, wait):
    # Switch must be something like 's1','s2','s3','s4','s5'
    core.setProperty('Arduino-Switch', 'State', int(df.get(switch)))
    for m in range(0, wait):
        time.sleep(1)
    valve_off()

def color_mask_generator(image_path):
    print("Creating masks based on colors in the image...\nPlease wait...")
    img = Image.open(image_path)
    img_array = np.array(img.convert('RGBA'))
    unique_colors = np.unique(img_array.reshape(-1, img_array.shape[2]), axis=0)

    masks = []
    for color in unique_colors:
        # Ignore transparent pixels, black color and white color
        if color[-1] == 0 or np.all(color == [0, 0, 0, 255]) or np.all(color == [255, 255, 255, 255]):
            continue
        mask = np.zeros((img.height, img.width), dtype='uint8')
        for i in range(img.height):
            for j in range(img.width):
                if all(img_array[i, j, :-1] == color[:-1]):
                    mask[i, j] = 255

        # Flip each mask array vertically (upside down, mirroring along horizontal axis)
        mask = np.flipud(mask)

        masks.append(mask)
    return masks

def mask_rescaler(in1, h, w):
    y1 = resize(in1, (h, w))
    ypad = np.array(y1, dtype='uint8')
    ypad[ypad == 1] = 255
    return ypad

def position_list():  # Define specific positions
    mm = bridge.get_studio()
    pm = mm.positions()
    pos_list = pm.getPositionList()
    numpos = pos_list.getNumberOfPositions()
    np_list = np.zeros((numpos, 2))
    for idx in range(numpos):
        pos = pos_list.getPosition(idx)
        stage_pos = pos.get(0)
        np_list[idx, 0] = stage_pos.x
        np_list[idx, 1] = stage_pos.y
    return np_list

def patterning(UVexposure, slimage, channel=4, intensity=1000):
    core.setSLMImage(DMD, slimage)
    time.sleep(1.5)
    core.setProperty('Mightex_BLS(USB)', 'channel', channel)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', intensity)
    time.sleep(UVexposure)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', 0)
    time.sleep(1)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', 0)

#%% Patterning Images based on their colors.
# Note: Not all colors are available in image recognition, so better stick to close derivatives of
#       red, yellow or blue. i.e. green

# DMD Properties
h = 684
w = 608
CF = 0.45
valves = ('s0', 's1', 's2', 's3', 's4', 's5')
'''
4X Objective (CF = 1.23)
10X Objective (CF = 0.45)
20X Objective (CF = 0.28)
'''

# Default UV exposure time (seconds)
default_uv_exposure = 0.3

# Insert image
image_path = "Crab2.png"
masks = color_mask_generator(image_path)

xy_up = position_list()
inks = ('SKIP', 'Atto488', 'Tex615', 'Tye665', '1XRNAbuffer', '1XRNAbuffer2')  # List of chemicals in each valve, first has to be SKIP

for ink in range(1, 5):
    # Ask for confirmation before pumping each ink
    user_input = input(f"Do you want to proceed with pumping {inks[ink]}? (y/n): ").strip().lower()

    if user_input != 'y':
        print(f"Skipping {inks[ink]}...")
        continue

    if ink in (1, 2, 3, 4):
        print('Starting %s flow for 60 seconds' % inks[ink])
        valve_timer(valves[ink], 60)  # 60s flow

        print('Beginning patterning of %s...' % inks[ink])

        exp_input = input(
            f"Define exposure time in seconds for {inks[ink]} "
            f"(press Enter to use default {default_uv_exposure} s): "
        ).strip()

        if exp_input == "":
            uv_exposure = default_uv_exposure
        else:
            try:
                uv_exposure = float(exp_input)
            except ValueError:
                print("Invalid input. Using default exposure time.")
                uv_exposure = default_uv_exposure
        
        for position_index, position in enumerate(xy_up):
            for i, mask in enumerate(masks):
                # Set position, resize, and pattern
                core.setXYPosition(position[0], position[1])
                if (ink == 1 and i == 0) or (ink == 2 and i == 1) or (ink == 3 and i == 2) or (ink == 4 and i == 3):
                    SLim = mask_rescaler(np.array(mask), h, w)
                    patterning(uv_exposure, SLim, channel=4, intensity=1000)
                time.sleep(1)

        # Ask for confirmation before cleaning
        user_input = input(f"Do you want to proceed with cleaning using {inks[5]}? (y/n): ").strip().lower()
        if user_input != 'y':
            print(f"Skipping cleaning with {inks[5]}...")
        else:
            print('Cleaning chamber with %s for 90 seconds' % inks[5])
            valve_timer(valves[5], 90)  #90s wash

print('\n----Multidomain patterning completed. PLEASE REMOVE MICROFLUIDIC DEVICE----')

# Visualize the masks that were patterned
print('These were the masks used for patterning:')
for i, mask in enumerate(masks):
    plt.subplot(1, len(masks), i + 1)
    plt.imshow(np.flipud(mask), cmap='gray')
    plt.title('%s' % inks[i + 1])
plt.show()
