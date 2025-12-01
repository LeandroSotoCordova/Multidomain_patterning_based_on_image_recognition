# -*- coding: utf-8 -*-
"""
Created on Fri May  5 01:41:51 2023

@author: Leo
"""

from pycromanager import Bridge
import matplotlib.pyplot as plt
import numpy as np
from skimage.transform import resize
import time
from PIL import Image

h = 684
w = 608
radius = 100

#%% Initialization:
bridge = Bridge(convert_camel_case=False)
core = bridge.get_core()
DMD = core.getSLMDevice()
core.setProperty(DMD,'TriggerType',1)
h = core.getSLMHeight(DMD)
w = core.getSLMWidth(DMD)
core.setProperty('UserDefinedStateDevice-1','Label','Patterning ON (dichroic mirror)')
core.setProperty('UserDefinedStateDevice','Label','BF')
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
core.setProperty('Mightex_BLS(USB)','normal_CurrentSet',0)


#%%Functions: Useful to automate

def color_mask_generator(image_path):
    print("Creating masks based on colors in the image...\nPlease wait...")
    img = Image.open(image_path)
    img_array = np.array(img.convert('RGBA'))
    unique_colors = np.unique(img_array.reshape(-1, img_array.shape[2]), axis=0)

    masks = []
    for color in unique_colors:
        if color[-1] == 0 or np.all(color == [0, 0, 0, 255]) or np.all(color == [255, 255, 255, 255]):
            continue
        mask = np.zeros((img.height, img.width), dtype='uint8')
        for i in range(img.height):
            for j in range(img.width):
                if all(img_array[i,j,:-1] == color[:-1]):
                    mask[i,j] = 255
        mask = np.flipud(mask)
        masks.append(mask)
    return masks

def mask_rescaler(in1):
    y1 = resize(in1, (h, w))
    ypad = np.array(y1, dtype='uint8')
    ypad[ypad == 1] = 255
    return ypad

def position_list():
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
image_path = "Firefly.png"
masks = color_mask_generator(image_path)

xy_up = position_list()
uv_exposure = 5 #Intensity

print('Reviewing masks for patterning...')

for i, mask in enumerate(masks):
    plt.imshow(np.flipud(mask), cmap='gray')
    plt.title(f'Mask {i+1}')
    plt.show()
    user_input = input("Would you like to pattern this mask? (y/n): ").strip().lower()
    if user_input == 'y':
        print('Beginning patterning...')
        for j, position in enumerate(xy_up):
            # Set position, resize and pattern
            core.setXYPosition(position[0], position[1])
            SLim = mask_rescaler(mask)
            patterning(uv_exposure, SLim, channel=4, intensity=1000)
            time.sleep(1)
        print('Patterning ended for this mask.')
    elif user_input == 'n':
        print('Skipping this mask.')
        continue

print('Patterning process complete.')
