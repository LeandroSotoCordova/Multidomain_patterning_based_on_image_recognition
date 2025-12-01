from pycromanager import Bridge
import matplotlib.pyplot as plt
import numpy as np
from skimage.transform import resize
import time
import skimage.draw as skdraw
import pandas as pd
from skimage.draw import polygon

# DMD Properties
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

#Channel 1: Blue Light
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

#%%Functions: Useful to auntomate
    
def valve_on(switch):
    # Switch must be something like 's0', 's1', etc.
    core.setProperty('Arduino-Switch','State',int(df.get(switch)))

def valve_off(switch2='s0'):
    core.setProperty('Arduino-Switch','State',int(df.get(switch2)))
    
def valve_timer(switch, wait):
    # Switch must be something like 's0', 's1', etc.
    core.setProperty('Arduino-Switch','State',int(df.get(switch)))
    for m in range(0, wait):
        time.sleep(1)
    valve_off()

def circle_mask_generator(h,w,radius):  
    rr, cc = skdraw.disk((h//2, w//2), radius, shape=(h, w))
    mask1 = np.zeros([h,w],dtype='uint8')
    mask1[rr,cc] = 255
    return mask1
       
def square_mask_generator(h,w,ex):
    rr,cc = skdraw.rectangle(((h-ex)/2,(w-ex)/2),extent=(ex,ex),shape=[h,w])
    mask2 = np.zeros((h,w),dtype='uint8')
    mask2[rr.astype('int'),cc.astype('int')] = 255
    return mask2
   
def equil_triangle_mask_generator(h,w,base):
    mask1 = np.zeros([h,w],dtype='uint8')
    x = base
    Ax = np.round(x/2)
    Ay = np.round(np.sqrt(3)*x/4)
    cx = h/2
    cy = w/2
    r = np.array([cx,cx-Ax, cx+Ax])
    c = np.array([cy+Ay,cy-Ay,cy-Ay])
    rr, cc = polygon(r, c)
    mask1[rr,cc] = 255
    return (mask1)

def mask_rescaler(in1):
    y1 = resize(in1,(h,w/2))
    wpad = int(w/4)
    ypad = np.pad(y1,((0,0),(wpad,wpad)),'constant', constant_values=(0))
    ypad=np.array(ypad,dtype='uint8')
    ypad[ypad==1]=255
    return ypad

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
    
def patterning_grid(UVexposure, slimage, num_rows=3, num_cols=3, channel=4, intensity=1000):
    core.setSLMImage(DMD, slimage)
    time.sleep(1.5)
    core.setProperty('Mightex_BLS(USB)', 'channel', channel)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', intensity)
    time.sleep(UVexposure)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', 0)
    time.sleep(1)
    core.setProperty('Mightex_BLS(USB)', 'normal_CurrentSet', 0)

#%% Shapes' Parameters (CHANGE CF and shape size)
"""
STARTING HERE YOU CAN EDIT #############################################################################################################################
"""

# Conversion Factor (pixels to microns)
'''
4X Objective (CF = 1.23)
10X Objective (CF = 0.45)
20X Objective (CF = 0.28)
'''
CF = 0.45
 
##CHANGE SIZES OF SHAPES
# Square and Objective Parameters
square_side = 150 #microns
square_conv = square_side / CF
draw_square = square_mask_generator(h,w,ex=square_conv)

# Triangle and Objective Parameters
base_side = 150 #microns
base_conv = base_side / CF
draw_triangle = equil_triangle_mask_generator(h, w, base=base_conv)

# Circle and Objective Parameters
diam = 50 #microns
diam_conv = diam / CF
draw_circle = circle_mask_generator(h, w, radius=(diam_conv / 2))

# Positions in the microscope (do NOT change)
xy_up = position_list()

#%% Patterning Variables (Change other variables)

# Calculate the coordinates for the 3x3, 5x5, 7x7, 9x9 grid
'''You need to make rows and columns equal to use the concentric circles!!!
For 10X objective:
    3x3 grid: range(-1, 2)  Working_grid_sizes = 0.65-4.5 (40um), 0.65-3 (50um), 0.6-1.7 (100um), 0.6-1(150um), 0.55-0.8 (200um)
    5x5 grid: range(-2, 3)  Working_grid_sizes = 0.8-1.2(50um), 0.65-0.9 (100um), 0.6(150um)
    7x7 grid: range(-3, 4)  Working_grid_sizes = 
    9x9 grid: range(-4, 5)  Working_grid_sizes = 
'''
row_range = range(-1, 2) # Number of rows in grid 
col_range = range(-1, 2) # Number of columns in grid
uv_exposure = 5  # Intensity (in seconds)
grid_size = square_conv * 0.8  # Size of the grid based on your shape 
output = draw_square #shape are patterning


"""
EDIT UNTIL HERE #############################################################################################################################
"""
#%%
# Print the total number of gels to be patterned
num_rows = len(row_range)
num_cols = len(col_range)
total_gels = len(xy_up) * num_rows * num_cols
print(f"Total gels to be patterned: {total_gels}")

# Estimate the total time required for patterning (in minutes)
stage_move_delay = 0.08
image_update_delay = 1.5
patterning_delay = 2.5
delay_per_gel = stage_move_delay + image_update_delay + patterning_delay + uv_exposure
total_time_sec = total_gels * delay_per_gel
total_minutes = int(total_time_sec // 60)
total_seconds = int(total_time_sec % 60)
print(f"Estimated time to finish patterning: {total_minutes} min {total_seconds} sec")

# Initialize gel counter
gel_counter = 0

# Start patterning with a countdown
for i in range(len(xy_up)):
    x_center, y_center = xy_up[i, 0], xy_up[i, 1]
    for row in row_range:
        for col in col_range:
            x_pos = x_center + col * grid_size
            y_pos = y_center + row * grid_size
            
            core.setXYPosition(x_pos, y_pos)
            SLim = mask_rescaler(output)
            patterning_grid(uv_exposure, SLim, channel=4, intensity=1000)
            plt.imshow(output)
            
            gel_counter += 1
            remaining_gels = total_gels - gel_counter
            print(f"{remaining_gels} gels remaining...")
print("Patterning complete!")

#%% Time debugging
# # Measure actual delay for setting XY position
# start_time = time.time()
# core.setXYPosition(x_pos, y_pos)
# end_time = time.time()
# move_delay = end_time - start_time
# print(f"Measured move delay: {move_delay} seconds")

# # Measure actual delay for SLM image update
# start_time = time.time()
# core.setSLMImage(DMD, SLim)
# end_time = time.time()
# image_update_delay = end_time - start_time
# print(f"Measured image update delay: {image_update_delay} seconds")

# # Measure total patterning time
# start_time = time.time()
# patterning_grid(uv_exposure, SLim, channel=4, intensity=1000)
# end_time = time.time()
# total_patterning_delay = end_time - start_time
# print(f"Measured patterning delay: {total_patterning_delay} seconds")
