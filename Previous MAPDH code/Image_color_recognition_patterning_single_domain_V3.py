from pycromanager import Bridge
import matplotlib.pyplot as plt
import numpy as np
from skimage.transform import resize
import time
from PIL import Image
import jpy

# DMD properties 
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

#%% Functions: Useful to automate

def color_mask_generator(image_path):
    print("Creating masks based on colors in the image...\nPlease wait...")
    img = Image.open(image_path)
    img_array = np.array(img.convert('RGBA'))
    unique_colors = np.unique(img_array.reshape(-1, img_array.shape[2]), axis=0)

    masks = []
    for color in unique_colors:
        # Ignore transparent pixels, black color, and white color
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

def mask_rescaler(in1, size, cf):
    desired_size = size / cf
    scale_factor = desired_size / in1.shape[0]
    rescaled_mask = resize(in1, (int(in1.shape[0] * scale_factor), int(in1.shape[1] * scale_factor)))
    rescaled_mask[rescaled_mask == 1] = 255
    return rescaled_mask

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
    slimage_bytes = slimage.astype('uint8').tobytes()
    slimage_java_bytes = jpy.array('byte', slimage_bytes)
    core.setSLMImage(DMD, slimage_java_bytes)
    time.sleep(1.5)
    core.setProperty('Mightex_BLS(USB)', 'channel', channel)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', intensity)
    time.sleep(UVexposure)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', 0)
    time.sleep(1)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', 0)
#%% Patterning Images based on their colors.
# Note: Not all colors are available, so better stick to close derivatives of
# red, yellow, or blue, i.e., green

# Insert image
image_path = "Manta.png"
# image_path = "Pixel Watermelon.png"
masks = color_mask_generator(image_path)

# Adjust these values according to your requirements
size = 100  # micrometers
cf = 0.45  # Conversion factor (pixels to micrometers)

xy_up = position_list()
uv_exposure = 1  # Intensity

print('Beginning patterning...')

for j, position in enumerate(xy_up):
    for i, mask in enumerate(masks):
        # Visualize the masks that are patterning
        plt.subplot(len(xy_up), len(masks), j * len(masks) + i + 1)
        plt.imshow(np.flipud(mask), cmap='gray')

        # Set position, resize, and pattern
        core.setXYPosition(position[0], position[1])
        SLim = mask_rescaler(mask, size, cf)
        patterning(uv_exposure, SLim, channel=4, intensity=1000)
        time.sleep(1)

print('Patterning ended.')
print('These are the masks used for patterning:')