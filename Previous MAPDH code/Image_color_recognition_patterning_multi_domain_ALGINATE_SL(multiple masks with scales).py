# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 19:51:57 2025

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
core.setProperty(DMD,'TriggerType',1)
# core.setSLMPixelsTo(DMD,100) #show all pixels
h = core.getSLMHeight(DMD)
w = core.getSLMWidth(DMD)
core.setProperty('UserDefinedStateDevice-1','Label','Patterning ON (dichroic mirror)')
core.setProperty('UserDefinedStateDevice','Label','BF')
# core.setProperty('HamamatsuHam_DCAM','Binning','2x2')
core.setProperty('UserDefinedShutter-1','State',1)
core.setProperty('UserDefinedShutter','State',1)

#Channel 4: UV LED
core.setProperty('Mightex_BLS(USB)','mode','NORMAL')
core.setProperty('Mightex_BLS(USB)','channel',1)
core.setProperty(DMD,'AffineTransform.m00',0)
core.setProperty(DMD,'AffineTransform.m01',-0.7988)
core.setProperty(DMD,'AffineTransform.m02',1231.7751)
core.setProperty(DMD,'AffineTransform.m10',1.1149)
core.setProperty(DMD,'AffineTransform.m11',0.0000)
core.setProperty(DMD,'AffineTransform.m12',-904.0098)
#current set: 0-1000
core.setProperty('Mightex_BLS(USB)','normal_CurrentSet',0)

#%% Turn Arduino shutter ON:
core.setProperty('Arduino-Shutter','OnOff',1)
#first 0: closest to you, last 0: furthest away
d = {'s1': '00001', 's2': '00010','s3': '000100', 's4': '01000', 's5': '10000'}
d = {'s0': 0, 's1': 1, 's2': 2,'s3': 4, 's4': 8, 's5': 16}
df = pd.Series(data=d)

#%%Functions: Useful to automate
def valve_on(switch):
    # Switch must be something like 1,2,3,4,5,etc.
    core.setProperty('Arduino-Switch','State',int(df.get(switch)))

def valve_off(switch2='s0'):
    # Note that only valve_off() turns off the valves.
    core.setProperty('Arduino-Switch','State',int(df.get(switch2)))
    
def valve_timer(switch, wait):
    # Switch must be something like 1,2,3,4,5,etc.
    core.setProperty('Arduino-Switch','State',int(df.get(switch)))
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
        #Ignore transparent pixels, black color and white color
        if color[-1] == 0 or np.all(color == [0, 0, 0, 255]) or np.all(color == [255, 255, 255, 255]):  
            continue
        mask = np.zeros((img.height, img.width), dtype='uint8')
        for i in range(img.height):
            for j in range(img.width):
                if all(img_array[i,j,:-1] == color[:-1]):
                    mask[i,j] = 255
                    
        #Flip each mask array vertically (upside down)
        #Mirroring along horizontal axis)
        mask = np.flipud(mask)
        
        masks.append(mask)
    return masks

# def mask_rescaler(in1, h, w):
#     y1 = resize(in1, (h, w))
#     ypad = np.array(y1, dtype='uint8')
#     ypad[ypad == 1] = 255
#     return ypad

#%%
scaling_factor = 0.7  # Seems to work in btw 0.2-0.7

def mask_rescaler(in1):
    in_h, in_w = in1.shape
    aspect_ratio_input = in_w / in_h
    aspect_ratio_target = w / h

    # Determine the scaling factor to fit within the DMD dimensions
    if aspect_ratio_input > aspect_ratio_target:
        # Wider image, scale by width
        scale_factor = (w / in_w) * scaling_factor
    else:
        # Taller image, scale by height
        scale_factor = (h / in_h) * scaling_factor

    # Corrective factor for y-axis distortion (empirical adjustment)
    y_correction_factor = 1.82  # Keep the y-axis correction

    # Calculate new dimensions after scaling
    new_h = int(in_h * scale_factor * y_correction_factor)
    new_w = int(in_w * scale_factor)

    # Resize mask with corrected dimensions
    resized_mask = resize(in1, (new_h, new_w), anti_aliasing=True)

    # Create a new blank mask with DMD dimensions
    ypad = np.zeros((h, w), dtype='uint8')

    # Calculate padding to center the mask
    pad_y = (h - new_h) // 2
    pad_x = (w - new_w) // 2

    # Ensure padding does not go negative (in case of slight overcorrection)
    pad_y = max(pad_y, 0)
    pad_x = max(pad_x, 0)

    # Place the resized mask in the center
    ypad[pad_y:pad_y + min(new_h, h), pad_x:pad_x + min(new_w, w)] = (resized_mask[:h, :w] * 255).astype('uint8')

    return ypad
#%%

def position_list(): #Define specific positions
    mm = bridge.get_studio()
    pm = mm.positions()
    pos_list = pm.getPositionList()
    numpos = pos_list.getNumberOfPositions()
    np_list = np.zeros((numpos,2))
    for idx in range(numpos):
        pos = pos_list.getPosition(idx)
        stage_pos = pos.get(0)
        np_list[idx,0] = stage_pos.x
        np_list[idx,1] = stage_pos.y          
    return np_list

def patterning(UVexposure,slimage,channel=4,intensity=1000):
    core.setSLMImage(DMD,slimage)
    time.sleep(1.5)
    core.setProperty('Mightex_BLS(USB)','channel',channel)
    core.setProperty('Mightex_BLS(USB)','normal_CurrentSet',intensity)
    time.sleep(UVexposure)
    core.setProperty('Mightex_BLS(USB)','normal_CurrentSet',0)
    time.sleep(1)
    core.setProperty('Mightex_BLS(USB)','normal_CurrentSet',0)
    
#%% Patterning Images based on their colors.
#Note: Not all color are availble, so better stick to close derivatives of 
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
xy_up = position_list()  # Get the list of XY positions
uv_exposure = 0.3  # UV exposure time in seconds
inks = ('SKIP', 'Atto488', 'Tex615', 'Tye665', '1X RNABufferWash', '1X RNABufferWash2')  # Chemicals in valves

# Insert images
image_paths = ["Fly2.png", "Centipede2.png", "Mantis.png"]
masks_list = []  # Store masks for all images

# Generate masks for all images and store them
for image_path in image_paths:
    masks = color_mask_generator(image_path)
    masks_list.append(masks)

# Loop through each ink to pattern masks sequentially at different positions
for ink in range(1, 5):  # Loop through inks 1 to 4
    # Ask for confirmation before using each ink
    user_input = input(f"Do you want to proceed with pumping {inks[ink]}? (y/n): ").strip().lower()
    if user_input != 'y':
        print(f"Skipping {inks[ink]}...")
        continue

    print(f'Starting {inks[ink]} flow for 60 seconds...')
    valve_timer(valves[ink], 60)  # Open valve for 60 seconds

    print(f'Beginning patterning of {inks[ink]}...')

    # Pattern the nth mask from each image at consecutive positions
    for image_index, masks in enumerate(masks_list):
        if ink - 1 < len(masks):  # Make sure the mask index exists
            mask = masks[ink - 1]  # Select Mask N (where N = ink)
            position = xy_up[image_index]  # Get corresponding position
            core.setXYPosition(position[0], position[1])  # Move to the position
            
            SLim = mask_rescaler(mask)
            # SLim = mask_rescaler(np.array(mask), h, w)  # Resize the mask
 
            patterning(uv_exposure, SLim, channel=4, intensity=1000)
            time.sleep(1)  # Wait 1 sec between masks

    # Wash with water (ink 5) after each ink
    user_input = input(f"Do you want to proceed with cleaning using {inks[5]}? (y/n): ").strip().lower()
    if user_input == 'y':
        print(f'Cleaning chamber with {inks[5]} for 90 seconds...')
        valve_timer(valves[5], 90)  # Clean with Water2
    else:
        print(f"Skipping cleaning with {inks[5]}...")

print('\n----Multidomain patterning completed. PLEASE REMOVE MICROFLUIDIC DEVICE----')

# Visualize the masks used for patterning
print('These were the masks used for patterning:')
plt.figure(figsize=(12, 6))
for image_index, masks in enumerate(masks_list):
    for i, mask in enumerate(masks):
        plt.subplot(len(masks_list), len(masks), image_index * len(masks) + i + 1)
        plt.imshow(np.flipud(mask), cmap='gray')
        plt.title(f'{inks[i + 1]} - Image {image_index + 1}')
plt.show()
