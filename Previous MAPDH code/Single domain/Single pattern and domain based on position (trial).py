from pycromanager import Bridge
from matplotlib import image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from skimage.color import rgb2gray
from skimage.transform import resize
import time
import skimage.draw as skdraw
import pandas as pd
import os
import cv2
import datetime
from skimage.draw import polygon

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
    # return np.rot90(mask1)
    return (mask1)
        
def square_mask_generator(h,w,ex):
    rr,cc = skdraw.rectangle(((h-ex)/2,(w-ex)/2),extent=(ex,ex),shape=[h,w])
    mask2 = np.zeros((h,w),dtype='uint8')
    mask2[rr.astype('int'),cc.astype('int')] = 255
    return mask2
    
def rectangle_mask_generator(h,w,lx,ly):
    midx = h/2
    midy = w/2
    startx = midx-lx
    starty = midy-ly
    endx = midx + lx
    endy = midy + ly
    rr,cc = skdraw.rectangle((startx, starty),end=(endx, endy),shape=[h,w])
    mask2 = np.zeros((h,w),dtype='uint8')
    mask2[rr.astype('int'),cc.astype('int')] = 255
    return mask2

def plus_mask_generator(h,w,wdist,wthick):
    m1 = rectangle_mask_generator(h,w,wthick,wdist)
    m2 = rectangle_mask_generator(h,w,wdist,wthick)
    mtog = m1+m2
    mtog[mtog>1] = 255
    return mtog
    
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

#%% Patterning Shape

# DMD Properties
h = 684
w = 608
CF = 1.23

'''
# 4X Objective --> CF = 1.23
# 1 pixel = 1.23 um
# 100 um gel = 100/1.23 = 81 pixels


# 10X Objective --> CF = 0.45
# 1 pixel = 0.45 um
# 100 um gel = 100/0.45 = 222 pixels

# 20X UV Objective --> CF = 0.28
# 1 pixel = 0.28 um
# 100 um rec. gel = 100/0.28 = 357 pixels

'''
##CHANGE SIZES OF SHAPES
# Square and Objective Parameters
square_side = 500 
square_conv = square_side / CF
draw_square = square_mask_generator(h,w,ex=square_conv)

# Triangle and Objective Parameters
base_side = 100
base_conv = base_side / CF
draw_triangle = equil_triangle_mask_generator(h, w, base=base_conv)

# Rectangle and Objective Parameters
lx_side = 50
ly_side = 100
lx_conv = lx_side / CF
ly_conv = ly_side / CF
draw_rectangle = rectangle_mask_generator(h, w, lx=lx_conv, ly=ly_conv)

# Plus and Objective Parameters
width_side = 100/2
thick_side = 40/2
width_conv = width_side / CF
thick_conv = thick_side / CF
draw_plus = plus_mask_generator(h, w, wdist=width_conv, wthick=thick_conv)

#Position located patterning
plt.imshow(draw_square)

xy_up = position_list()

uv_exposure = 10                                                                                                                                                                                                 #Intensity
for i in range(len(xy_up)):
    core.setXYPosition(xy_up[i,0],xy_up[i,1])
    output = draw_square
    SLim = mask_rescaler(output)
    patterning(uv_exposure,SLim,channel=4,intensity=1000)
    
    
                                             
    
    
    
    
    
    
    
    
    