# -*- coding: utf-8 -*-
"""
Created on Fri May  18 19:18:51 2023
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

# Initialization:
bridge = Bridge(convert_camel_case=False)
core = bridge.get_core()
DMD = core.getSLMDevice()
core.setProperty(DMD, 'TriggerType', 1)
# core.setSLMPixelsTo(DMD, 100) #show all pixels
h = core.getSLMHeight(DMD)
w = core.getSLMWidth(DMD)
core.setProperty('UserDefinedStateDevice-1', 'Label', 'Patterning ON (dichroic mirror)')
core.setProperty('UserDefinedStateDevice', 'Label', 'BF')
# core.setProperty('HamamatsuHam_DCAM', 'Binning', '2x2')
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


# Functions: Useful to automate

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

        # Flip each mask array vertically (upside down)
        # Mirroring along horizontal axis)
        mask = np.flipud(mask)

        masks.append(mask)
    return masks


def mask_rescaler(in1, conversion_factor):
    h_rescaled = int(h * conversion_factor)
    w_rescaled = int(w * conversion_factor)
    y1 = resize(in1, (h_rescaled, w_rescaled), anti_aliasing=True)
    ypad = np.zeros((h, w), dtype='uint8')
    ypad[:h_rescaled, :w_rescaled] = y1
    ypad[ypad == 1] = 255
    return ypad



def position_list():
    # Define specific positions
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


# Patterning Images based on their colors.
# Note: Not all color are available, so better stick to close derivatives of
# red, yellow or blue. i.e. green

# DMD Properties
h = 684
w = 608
CF = 1 #Max 1, changing this will change the size of the masks

'''
Not used...
4X Objective (CF = 1.23)
10X Objective (CF = 0.45)
20X Objective (CF = 0.28)
'''

# Insert image
image_path = "Manta.png"
# image_path = "Pixel Watermelon.png"
masks = color_mask_generator(image_path)

xy_up = position_list()
uv_exposure = 1  # Intensity

print('Beginning patterning...')

for j, position in enumerate(xy_up):
    for i, mask in enumerate(masks):
        # Visualize the masks that are patterning
        plt.subplot(len(xy_up), len(masks), j * len(masks) + i + 1)
        plt.imshow(np.flipud(mask), cmap='gray')

        # Set position, resize and pattern
        core.setXYPosition(position[0], position[1])
        SLim = mask_rescaler(mask, CF)
        patterning(uv_exposure, SLim, channel=4, intensity=1000)
        time.sleep(1)

print('Patterning ended.')
print('These are the masks used for patterning:')

