#! /usr/bin/env python
# -*- coding: utf8 -*-
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from array import array
from tkinter.filedialog import askopenfilename
import tkinter as tk
import sys,random
import math
import colorsys
import socket
import threading
import json
import datetime
import time
from pathlib import PurePath

PERSPECTIVE_FOV = 100.0
FAR_DIST = 1000.0
CAM_ROT_RATE_MIN = 0.01
CAM_ROT_RATE_MAX = 0.64
CAM_ROT_RATE_MULT = 4
ESCAPE = '\033'
GRID_LINE_WIDTH = 1
FLOOR_DEPTH = 1
TILE_LENGTH = 5.0
GROUND_LENGTH = 50
GROUND_WIDTH = 50
INIT_TREE_COUNT = 2
INIT_GRASS_COUNT = 250
SAFE_PLANT_BORDER = 0.750

# background color of sky
BG_COLOR = [0.45, 0.45, 0.85]
TILE_DEF_COLOR = [0.2, 0.2, 0.1]
WHITE = [1.0, 1.0, 1.0]

# stages of life of a plant
STAGE_PRESEED = 0
STAGE_DORMANT = 1
STAGE_GERMINATION = 2
STAGE_ACTIVE = 3
STAGE_MATURE = 4
STAGE_DEAD = 5

MOISTURE_DEMAND_DIVISOR = 100

# mouse drag modes
DRAG_MODE_NONE = 0
DRAG_MODE_ROT_MODEL = 1
DRAG_MODE_MOVE_CAM = 2
DRAG_MODE_ROT_CAM = 3

active_drag_mode = 0
begin_drag = False
next_drag_mode_left = DRAG_MODE_ROT_MODEL
next_drag_mode_right = DRAG_MODE_MOVE_CAM
drag_start_x = 0
drag_start_y = 0
drag_start_rx = 0
drag_start_ry = 0

frame_count = 0
cam_rot_y=0.0
cam_rot_x=25.0
cam_pos_x=-0.0
cam_pos_y=-20.0
cam_pos_z=-40.0
cam_rot_inc=CAM_ROT_RATE_MIN # degrees per frame
draw_grid=True
floor_y = 0.0
floor_x_min = -5.0
floor_x_max = 5.0
floor_z_min = -5.0
floor_z_max = 5.0
animate_rot_y = True
ortho_mode = False
ortho_left = -230.0
ortho_right = 230.0
ortho_bottom = -165.0
ortho_top = 165.0
ortho_near = 0.0
ortho_far = 1000.0

ground = []
plants = []
tilemap = [None] * (GROUND_LENGTH * GROUND_WIDTH)
remove_list = []

wind_phase = 0.0
wind_mag = 3.0 # 2.0
wind_phase_increment = 1.0 / 30 # 60

SEQ_TREE =  "CMMAEAPKEMZLNALAYHHCFF" #J
SEQ_GRASS = "CMCABABKEMZGAAJBADCCFE"

class Genome:
    def __init__(self):
        
        self.MinGermWet = 0.1                       #A = 0.0, Z = 1.0
        self.MaxGermWet = 0.5                       #A = 0.0, Z = 1.0
        self.GermTime = 10                          #A = 1,   Z = 100
        self.GermMoistureDemand = 0.001             #A = 0.001 Z = 1.0

        self.AverageAge = 1000                      #A = 100     Z = 50000
        self.AgeVariance = 1000                     #A = 100     Z = 5000
        self.DecayTime = 100                        #A = 100     Z = 10000
        
        self.emergenceAxisTilt = -30.0              #A = -180, Z = 180
        self.emergenceAxisTiltVariance = 60.0       #A = 0,    Z = 360        
        self.emergenceAxisRotation = 0.0            #A = -180, Z = 180
        self.emergenceAxisRotationVariance = 360.0  #A = 0,    Z = 360

        self.StemLengthGrowthRate = 0.05            #A = 0.01  Z = 0.1
        self.StemLengthGrowthVariance = 0.06        #A = 0.01  Z = 0.1
        self.StemLengthGrowthDecay = 0.0003         #A = 0.0001 Z = 0.0100
        
        self.StemDiameterGrowthRate = 0.005         #A = 0.001   Z = 0.010
        self.StemDiameterGrowthDecay = 0.00001      #A = 0.000001 Z = 0.001000
        
        self.StemSpawnGenerations = 9               #A = 1       Z = 10
        self.StemSpawnTime = 300                    #A = 10      Z = 1000
        self.StemSpawnTimeVariance = 300            #A = 10      Z = 1000
        
        self.StemForkCount = 0.95                   #A = 0       Z = 10
        self.StemForkVariance = 2.2                 #A = 0       Z = 10

        self.ColorAgeDivisor = 4000                 #A = 100    Z = 10000

        self.NodeProgressionStyle = 1

    def CodeToValue(c, minVal, maxVal):
        cv = ord(c)-65
        if (cv > 25):
            cv = cv - 32
        if (cv < 0):
            cv = 0
        val = minVal + (cv / 25) * (maxVal - minVal)
        return val

    def ValueToCode(v, minVal, maxVal):
        sv = int (25.0 * (v - minVal) / (maxVal - minVal))
        c = chr(sv+65)
        return c

    def Serialize(self):
        seq = ""
        seq = seq + Genome.ValueToCode(self.MinGermWet, 0.0, 1.0)
        seq = seq + Genome.ValueToCode(self.MaxGermWet, 0.0, 1.0)
        seq = seq + Genome.ValueToCode(self.GermTime, 1.0, 100.0)
        seq = seq + Genome.ValueToCode(self.GermMoistureDemand, 0.001, 1.0)
        seq = seq + Genome.ValueToCode(self.AverageAge, 100.0, 50000.0)
        seq = seq + Genome.ValueToCode(self.AgeVariance, 100.0, 5000.0)
        seq = seq + Genome.ValueToCode(self.DecayTime, 100.0, 10000.0)
        seq = seq + Genome.ValueToCode(self.emergenceAxisTilt, -180.0, 180.0)
        seq = seq + Genome.ValueToCode(self.emergenceAxisTiltVariance, 0.0, 360.0)
        seq = seq + Genome.ValueToCode(self.emergenceAxisRotation, -180.0, 180.0)
        seq = seq + Genome.ValueToCode(self.emergenceAxisRotationVariance, 0.0, 360.0)
        seq = seq + Genome.ValueToCode(self.StemLengthGrowthRate, 0.01, 0.10)
        seq = seq + Genome.ValueToCode(self.StemLengthGrowthVariance, 0.01, 0.10)
        seq = seq + Genome.ValueToCode(self.StemLengthGrowthDecay, 0.0001, 0.0100)
        seq = seq + Genome.ValueToCode(self.StemDiameterGrowthRate, 0.001, 0.010)
        seq = seq + Genome.ValueToCode(self.StemDiameterGrowthDecay, 0.000001, 0.001000)
        seq = seq + Genome.ValueToCode(self.StemSpawnGenerations, 0.0, 12.0)
        seq = seq + Genome.ValueToCode(self.StemSpawnTime, 10.0, 1000.0)
        seq = seq + Genome.ValueToCode(self.StemSpawnTimeVariance, 10.0, 1000.0)
        seq = seq + Genome.ValueToCode(self.StemForkCount, 0.0, 10.0)
        seq = seq + Genome.ValueToCode(self.StemForkVariance, 0.0, 10.0)
        seq = seq + Genome.ValueToCode(self.ColorAgeDivisor, 100.0, 10000.0)
        return seq

    def Deserialize(self, seq):
        self.MinGermWet = Genome.CodeToValue(seq[0], 0.0, 1.0)
        self.MaxGermWet = Genome.CodeToValue(seq[1], 0.0, 1.0)
        self.GermTime = Genome.CodeToValue(seq[2], 1.0, 100.0)
        self.GermMoistureDemand = Genome.CodeToValue(seq[3], 0.001, 1.0)
        self.AverageAge = Genome.CodeToValue(seq[4], 100.0, 50000.0)
        self.AgeVariance = Genome.CodeToValue(seq[5], 100.0, 5000.0)
        self.DecayTime = Genome.CodeToValue(seq[6], 100.0, 10000.0)
        self.emergenceAxisTilt = Genome.CodeToValue(seq[7], -180.0, 180.0)
        self.emergenceAxisTiltVariance = Genome.CodeToValue(seq[8], 0.0, 360.0)
        self.emergenceAxisRotation = Genome.CodeToValue(seq[9], -180.0, 180.0)
        self.emergenceAxisRotationVariance = Genome.CodeToValue(seq[10], 0.0, 360.0)
        self.StemLengthGrowthRate = Genome.CodeToValue(seq[11], 0.01, 0.10)
        self.StemLengthGrowthVariance = Genome.CodeToValue(seq[12], 0.01, 0.10)
        self.StemLengthGrowthDecay = Genome.CodeToValue(seq[13], 0.0001, 0.0100)
        self.StemDiameterGrowthRate = Genome.CodeToValue(seq[14], 0.001, 0.010)
        self.StemDiameterGrowthDecay = Genome.CodeToValue(seq[15], 0.000001, 0.001000)
        self.StemSpawnGenerations = int(Genome.CodeToValue(seq[16], 0.0, 12.0))
        self.StemSpawnTime = Genome.CodeToValue(seq[17], 10.0, 1000.0)
        self.StemSpawnTimeVariance = Genome.CodeToValue(seq[18], 10.0, 1000.0)
        self.StemForkCount = Genome.CodeToValue(seq[19], 0.0, 10.0)
        self.StemForkVariance = Genome.CodeToValue(seq[20], 0.0, 10.0)
        self.ColorAgeDivisor = Genome.CodeToValue(seq[21], 100.0, 10000.0)

        #print ("StemSpawnGenerations: " + str(self.StemSpawnGenerations))

class SurfaceTile:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.r = TILE_DEF_COLOR[0] # red
        self.g = TILE_DEF_COLOR[1] # green
        self.b = TILE_DEF_COLOR[2] # blue
        self.c1h = 0.0
        self.c2h = 0.0
        self.c3h = 0.0
        self.c4h = 0.0

        self.wetness = 0.0
        self.water_table_y = -1.0
        self.hardness = 0.5
        self.nutrientlevel = 0.5
        self.moisture_demand = 0.0

        self.neighbors = [None] * 9

    def Draw(self):
        glColor3f(self.r, self.g, self.b)
        glBegin(GL_QUADS)
        glVertex3f(self.x, self.y+self.c1h, self.z)
        glVertex3f(self.x+TILE_LENGTH, self.y+self.c2h, self.z)
        glVertex3f(self.x+TILE_LENGTH, self.y+self.c3h, self.z+TILE_LENGTH)
        glVertex3f(self.x, self.y+self.c4h, self.z+TILE_LENGTH)
        glEnd()

    def Update(self):
        aspiration_rate = 0.0
        perc_rate = 0.0
        if (self.wetness > 0):
            aspiration_rate = 0.1 + ((1.0 - self.hardness) / 3)
        if (self.y > self.water_table_y):
            perc_rate = (1/(self.y - self.water_table_y))/33
        elif (self.y <= self.water_table_y):
            perc_rate = 1.0
        self.wetness = self.wetness * (1.0 - aspiration_rate) + perc_rate - (self.moisture_demand / MOISTURE_DEMAND_DIVISOR)
        if (self.wetness < 0):
            self.wetness = 0

class Cell:
    def __init__(self, parentPlant, parentCell):
        self.locationSeed = 0.0
        if (parentCell == None):
            self.isRoot = True
            self.rootDistance = 0
        else:
            self.isRoot = False
            self.rootDistance = parentCell.rootDistance + 1
        self.parentPlant = parentPlant
        self.parentCell = parentCell
        self.age = 0
        self.spawnCountdown = 0
        self.children = []
        self.growthFactorL = 0.0
        self.growthFactorD = 0.0

    def DrawSelf(self):
        glPointSize(6.0)
        glBegin(GL_POINTS)
        glColor3f(1.0,1.0,1.0)
        glVertex3f(0.0,0.0,0.0)
        glEnd()

    def Draw(self):
        glPushMatrix()
        self.DrawSelf()
        for childCell in self.children:
            childCell.Draw()
        glPopMatrix()

    def ReactSelf(self, parentCell, parentPlant):
        # override in derived classes
        return

    def React(self, parentCell, parentPlant):
        self.ReactSelf(parentCell, parentPlant)
        for childCell in self.children:
            childCell.React(self, parentPlant)
        self.age = self.age + 1
        
    def Update(self, parentPlant):
#        print("cell update")
        self.React(None, parentPlant)
#        for childCell in self.children:
#            childCell.React(self, parentPlant)

class Seed(Cell):
    def __init__(self, parentPlant, parentCell):
        Cell.__init__(self, parentPlant, parentCell)
        self.isRoot = True
        self.r = 0.75
        self.g = 0.75
        self.b = 0.0
        self.pointSize = 2.0

    def DrawSelf(self):
        glPointSize(6.0)
        glBegin(GL_POINTS)
        glColor3f(self.r,self.g,self.b)
        glVertex3f(0.0,0.0,0.0)
        glEnd()

    def ReactSelf(self, parentCell, parentPlant):
        if (parentPlant.stage == STAGE_DORMANT):
            #print ("dormant seed ground tile wetness: " + str(parentPlant.groundTile.wetness))
            if ((parentPlant.groundTile.wetness >= parentPlant.genome.MinGermWet) and (parentPlant.groundTile.wetness <= parentPlant.genome.MaxGermWet)):
                # begin germination
                parentPlant.stage = STAGE_GERMINATION
                self.germinationCountdown = parentPlant.genome.GermTime
                parentPlant.moisture_demand += parentPlant.genome.GermMoistureDemand
                self.r = 0.25
                self.g = 0.25
                self.b = 0.0
                #print ("germination started")
        elif (parentPlant.stage == STAGE_GERMINATION):
            if ((parentPlant.groundTile.wetness >= parentPlant.genome.MinGermWet) and (parentPlant.groundTile.wetness <= parentPlant.genome.MaxGermWet)):
                self.germinationCountdown = self.germinationCountdown - 1
                if (self.germinationCountdown <= 0):
                    # completed germination, become active
                    parentPlant.stage = STAGE_ACTIVE
                    # add a trunk (stem) cell
                    trunk = Trunk(parentPlant, parentCell)
                    self.children.append(trunk)
                    #print ("germination completed")
            else:
                # failed germination, become inactive
                parentPlant.stage = STAGE_INACTIVE
                print ("germination failed")
            return
        
class Trunk(Cell):
    def __init__(self, parentPlant, parentCell):
        Cell.__init__(self, parentPlant, parentCell)
        self.r = 0.0
        self.g = 0.75
        self.b = 0.0
        self.x2 = 0.0
        self.y2 = 0.0
        self.z2 = 0.0
        self.emergenceAxisTilt = parentPlant.genome.emergenceAxisTilt + (random.random() * parentPlant.genome.emergenceAxisTiltVariance)
        self.emergenceAxisRotation = parentPlant.genome.emergenceAxisRotation+ (random.random() * parentPlant.genome.emergenceAxisRotationVariance)
        self.length = 0
        self.diameter = 0.01
        self.growthFactorL = (parentPlant.genome.StemLengthGrowthRate + (random.random() * parentPlant.genome.StemLengthGrowthVariance)) / ((10+self.rootDistance)/10)
        self.growthFactorD = parentPlant.genome.StemDiameterGrowthRate / ((10+self.rootDistance)/10)
        self.stemSpawnCountdown = parentPlant.genome.StemSpawnTime + (random.random() * parentPlant.genome.StemSpawnTimeVariance)
        
    def DrawSelf(self):
        glLineWidth(2.0 + self.diameter)
        glColor3f(self.r,self.g,self.b)
#        glRotatef(self.emergenceAxisRotation, 0.0, 1.0, 0.0)
        glRotatef(self.emergenceAxisRotation+(wind_mag*math.sin(self.parentPlant.x+wind_phase*(self.rootDistance+1))), 0.0, 1.0, 0.0)

#        glRotatef(self.emergenceAxisTilt, 1.0, 0.0, 0.0)
        glRotatef(self.emergenceAxisTilt-(wind_mag*math.sin(self.parentPlant.x+wind_phase*(self.rootDistance+1))), 1.0, 0.0, 0.0)

        glBegin(GL_QUADS)
        glVertex3f(-self.diameter/2,0.0,0.0)
        glVertex3f(self.diameter/2,0.0,0.0)
        glVertex3f(self.diameter/3,self.length,0.0)
        glVertex3f(-self.diameter/3,self.length,0.0)
        glVertex3f(0.0,0.0,-self.diameter/2)
        glVertex3f(0.0,0.0,self.diameter/2)
        glVertex3f(0.0,self.length,self.diameter/3)
        glVertex3f(0.0,self.length,-self.diameter/3)
        glEnd()
        glTranslatef(0.0,self.length,0.0);

    def ReactSelf(self, parentCell, parentPlant):
#        print("Trunk react")
        if (parentPlant.stage == STAGE_ACTIVE):
            if (self.growthFactorL > 0):
                self.length = self.length + self.growthFactorL
                self.growthFactorL = self.growthFactorL - parentPlant.genome.StemLengthGrowthDecay
                if (self.growthFactorL <= 0):
                    self.growthFactorL = 0.0
#                    if (self.growthFactorD <= 0):
#                        self.BecomeMature(parentCell, parentPlant)
                    
            if (self.growthFactorD > 0):
                self.diameter = self.diameter + self.growthFactorD
                self.growthFactorD = self.growthFactorD - parentPlant.genome.StemDiameterGrowthDecay
                if (self.growthFactorD <= 0):
                    self.growthFactorD = 0.0
#                    if (self.growthFactorL <= 0):
#                        self.BecomeMature(parentCell, parentPlant)

            color_age = self.age / parentPlant.genome.ColorAgeDivisor
            if (color_age > 1.0):
                color_age = 1.0
            self.g = 0.85 - (color_age * 0.6)
            self.r = 0.10 + (color_age * 0.3)

        if (self.stemSpawnCountdown > 0):
            self.stemSpawnCountdown = self.stemSpawnCountdown - 1
            if (self.stemSpawnCountdown <= 0):
                if (self.rootDistance <= parentPlant.genome.StemSpawnGenerations):
                    # spawn 1 or more new trunk/stem cells here
                    forkCount = int(parentPlant.genome.StemForkCount + (random.random() * parentPlant.genome.StemForkVariance))
                    for n in range(forkCount + int(random.random() * self.rootDistance / 3)):
                        newStem = Trunk(parentPlant, self)
                        self.children.append(newStem)

        if ((parentPlant.stage == STAGE_DEAD) and (self.rootDistance == 0)):
            tilt = self.emergenceAxisTilt
            #print ("falling dead trunk tilt:" + str(tilt))
            if ((tilt < 0.0) and (tilt > -90.0)):
                self.emergenceAxisTilt = tilt - 1
            elif ((tilt >= 0.0) and (tilt < 90.0)):
                self.emergenceAxisTilt = tilt + 1
                    
    def BecomeMature(self, parentCell, parentPlant):
        parentPlant.stage = STAGE_MATURE
        #print("Trunk matured")
    
class Plant:
    def __init__(self,x,y,z,geneSeq):
        self.x = x
        self.y = y
        self.z = z
        self.age = 0
        self.rootCell = Seed(self, None)
        self.stage = STAGE_PRESEED
        self.groundTile = None
        self.genome = Genome()
        self.genome.Deserialize(geneSeq)
        self.moisture_demand = 0.0
        self.timeToLive = self.genome.AverageAge + (random.random() * self.genome.AgeVariance)
        self.decay_time = 0

    def Draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        self.rootCell.Draw()
        glPopMatrix()

    def Update(self):
        self.moisture_demand = 0.0
        self.rootCell.Update(self)
        self.age = self.age + 1
        if ((self.stage == STAGE_ACTIVE) or (self.stage == STAGE_MATURE)):
            self.timeToLive = self.timeToLive - 1
            if (self.timeToLive <= 0):
                self.stage = STAGE_DEAD
                self.decay_time = self.genome.DecayTime
                #print ("plant is dead")
        elif (self.stage == STAGE_DEAD):
            self.decay_time = self.decay_time - 1
            if (self.decay_time <= 0):
                remove_list.append(self)

def main():

    global window

    InitGround()
    InitPlants()
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(800, 600)    
    glutInitWindowPosition(100, 100)
    window = glutCreateWindow(b"Garden")
    glutDisplayFunc(DrawGLScene)

    #glutFullScreen()

    glutIdleFunc(DrawGLScene)
    #glutIdleFunc(UpdateWorld)
    glutReshapeFunc(ReSizeGLScene)
    glutKeyboardFunc(keyPressed)
    glutMouseFunc(mouseAction)
    glutMotionFunc(motionFunc)
    InitGL(800, 600)
    glutMainLoop()

def mouseAction(button, state, x, y):
    global drag_start_x, drag_start_y, drag_start_rx, drag_start_ry
    global cam_rot_x, cam_rot_y, cam_pos_x, cam_pos_y, drag_start_cx, drag_start_cy
    global active_drag_mode, next_drag_mode_left, next_drag_mode_right
    global begin_drag
#    print ("mouse action button:" + str(button) + " state:" + str(state) + " x,y:" + str(x) + "," + str(y))
    if (button==0) & (state==0): # left button pressed
#        hit_test_controls(x, y)
        active_drag_mode = next_drag_mode_left #DRAG_MODE_ROT_MODEL
        drag_start_x = x
        drag_start_y = y
        begin_drag = True;
    elif (button==0) & (state==1): # left button released
        active_drag_mode = DRAG_MODE_NONE
        dx = x - drag_start_x
        dy = y - drag_start_y
    elif (button==2) & (state==0): # right button pressed
        active_drag_mode = next_drag_mode_right #DRAG_MODE_MOVE_CAM
        drag_start_x = x
        drag_start_y = y
        begin_drag = True;
    elif (button==2) & (state==1): # right button released
        active_drag_mode = DRAG_MODE_NONE
        dx = x - drag_start_x
        dy = y - drag_start_y

def motionFunc(x, y):
    global drag_start_x, drag_start_y, drag_start_rx, drag_start_ry
    global cam_rot_x, cam_rot_y, cam_pos_x, cam_pos_y, drag_start_cx, drag_start_cy
    global active_drag_mode, begin_drag
    global cursor_xa, cursor_xb, cursor_ya, cursor_yb, cursor_za, cursor_zb
    global cursor_box_y_rot, CURSOR_ALPHA
    dx = x - drag_start_x
    dy = y - drag_start_y
    if (active_drag_mode == DRAG_MODE_ROT_MODEL):
        if (begin_drag == True):
            drag_start_rx = cam_rot_x
            drag_start_ry = cam_rot_y
        #print ("rotate model")
        cam_rot_x = drag_start_rx + (dy / 2)
        cam_rot_y = drag_start_ry + (dx / 2)
    elif (active_drag_mode == DRAG_MODE_MOVE_CAM):
        if (begin_drag == True):
            drag_start_cx = cam_pos_x
            drag_start_cy = cam_pos_y
        #print ("move model")
        cam_pos_x = drag_start_cx + (dx / 10)
        cam_pos_y = drag_start_cy - (dy / 10)
    # reset begin drag flag
    begin_drag = False

def keyPressed(key, x, y):
    global cam_pos_z
#    print ("key: " + str(key))
    key = ord(key)
    key = chr(key)
    key = key.upper()
    
    if (key == ESCAPE) | (key == 'Q'):
        sys.exit()
    if (key == '-'):
        cam_pos_z = cam_pos_z - 1
    if (key == '='):
        cam_pos_z = cam_pos_z + 1
    if (key == 'C'):
        plants.clear()
    if (key == 'R'):
        InitPlants()
    if (key == 'G'):
        for g in range(INIT_GRASS_COUNT):
            px = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_LENGTH/2) + (random.random()*GROUND_LENGTH))
            pz = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_WIDTH/2)+(random.random()*GROUND_WIDTH))
            p = Plant(px, 0.0, pz, SEQ_GRASS)
            p.stage = STAGE_DORMANT
            p.groundTile = FindTile(px, pz)
            plants.append(p)
    if (key == 'T'):
        px = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_LENGTH/2) + (random.random()*GROUND_LENGTH))
        pz = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_WIDTH/2)+(random.random()*GROUND_WIDTH))
        p = Plant(px, 0.0, pz, SEQ_TREE) #"CMCAKEMZLNALAWHHCFJ")
        p.stage = STAGE_DORMANT
        p.groundTile = FindTile(px, pz)
        plants.append(p)

def InitGL(Width, Height):                # We call this right after our OpenGL window is created.
    global window_width, window_height
    window_width = Width
    window_height = Height
    glClearColor(BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], 0.0)    # This Will Clear The Background Color To Black
    glClearDepth(1.0)                    # Enables Clearing Of The Depth Buffer
    glDepthFunc(GL_LESS)                # The Type Of Depth Test To Do
    glEnable(GL_DEPTH_TEST)                # Enables Depth Testing
    glEnable(GL_BLEND)         
    glShadeModel(GL_SMOOTH)                # Enables Smooth Color Shading
    
    #glBlendFunc(GL_SRC_ALPHA,GL_ONE)
    glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
    #glHint(GL_PERSPECTIVE_CORRECTION_HINT,GL_NICEST);
    glHint(GL_POINT_SMOOTH_HINT,GL_NICEST);   
    #glEnable(GL_TEXTURE_2D);                  
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()                    # Reset The Projection Matrix
                                        # Calculate The Aspect Ratio Of The Window
    gluPerspective(PERSPECTIVE_FOV, float(Width)/float(Height), 0.1, FAR_DIST)
    glMatrixMode(GL_MODELVIEW)

# The function called when our window is resized (which shouldn't happen if you enable fullscreen, below)
def ReSizeGLScene(Width, Height):
    global window_width, window_height
    window_width = Width
    window_height = Height
    if Height == 0:                        # Prevent A Divide By Zero If The Window Is Too Small 
        Height = 1

    glViewport(0, 0, Width, Height)        # Reset The Current Viewport And Perspective Transformation
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(PERSPECTIVE_FOV, float(Width)/float(Height), 0.1, FAR_DIST)
    glMatrixMode(GL_MODELVIEW)

def resetProjection():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()                    # Reset The Projection Matrix
    if (ortho_mode == True):
        glOrtho(ortho_left,ortho_right,ortho_bottom,ortho_top,ortho_near,ortho_far)
    else:
        gluPerspective(PERSPECTIVE_FOV, float(window_width)/float(window_height), 0.1, FAR_DIST)
    glMatrixMode(GL_MODELVIEW)    

def DrawGLScene():
    global cam_rot_y, cam_rot_x, cam_pos_x, cam_pos_y, cam_pos_z, frame_count
    UpdateWorld()
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    # setup camera viewpoint/ rotation
    glLoadIdentity()
    glTranslatef(cam_pos_x, cam_pos_y, cam_pos_z)
    glRotatef(cam_rot_y,0.0,1.0,0.0)
    # determine vector/axis to rotate around for camera tilt
    ctx = math.cos(cam_rot_y * math.pi / 180.0)
    ctz = math.sin(cam_rot_y * math.pi / 180.0)
    glRotatef(cam_rot_x,ctx,0.0,ctz)

    DrawGrid()
    DrawGround()
    DrawPlants()

    DrawString(str(frame_count) + " / " + str(len(plants)), -220, -160, 8, WHITE)
    
    glutSwapBuffers()
    if (animate_rot_y == True):
        cam_rot_y += cam_rot_inc

    frame_count = frame_count + 1
    #print ("draw")

def DrawGrid():
    global cam_rot_y, cam_rot_x, cam_pos_x, cam_pos_y, cam_pos_z, draw_point_size, draw_grid, active_points, clear_points
    glLineWidth(GRID_LINE_WIDTH)
    glBegin(GL_LINES)
    glColor3f(0.0, 0.5, 0.0)
    fx = floor_x_min
    while fx <= floor_x_max:
        glVertex3f(fx, floor_y-FLOOR_DEPTH, floor_z_min)
        glVertex3f(fx, floor_y-FLOOR_DEPTH, floor_z_max)
        fx += 10.0
    fz = floor_z_min
    while fz <= floor_z_max:
        glVertex3f(floor_x_min, floor_y-FLOOR_DEPTH, fz)
        glVertex3f(floor_x_max, floor_y-FLOOR_DEPTH, fz)
        fz += 10.0
    glEnd()

def DrawGround():
    global ground
    for tile in ground:
        tile.Draw()

def DrawPlants():
    global plants
    for p in plants:
        p.Draw()
        
def DrawChar(ch, x, y, size, color):
    glColor3f(color[0], color[1], color[2])
    segs = 0xffff
    #    segment to bit mapping
    #    _ _    6 7
    #   |\|/|  589a0
    #    - -    b c  
    #   |/|\|  4def1
    #    _ _    3 2
    #
    # relative coordinates of 2 vertices of each of the 16 possible segments
    cx1 = [4,4,4,2,0,0,0,2,0,2,4,0,2,0,2,4]
    cx2 = [4,4,2,0,0,0,2,4,2,2,2,2,4,2,2,2]
    cy1 = [6,3,0,0,0,3,6,6,6,6,6,3,3,0,0,0]
    cy2 = [3,0,0,0,3,6,6,6,3,3,3,3,3,3,3,3]
    # character set expressed as 16 bit value per glyph
    char_segs = [0x0000, 0x6208, 0x0201, 0x5a8f, 0x5aee, 0x7e66, 0xa68e, 0x0400, #  !"#$%&'
                 0x8400, 0x2100, 0xff00, 0x5a00, 0x2000, 0x1800, 0x5006, 0x2400, # <>*+,-./
                 0x24ff, 0x4200, 0x18dd, 0x14ce, 0x5a20, 0x18EE, 0x18fe, 0x44c0, # 01234567
                 0x18ff, 0x18ef, 0x0808, 0x2040, 0x8c00, 0x180c, 0x3100, 0x50c1, # 89:;<=>?
                 0x12fd, 0x18f3, 0x52cf, 0x00fc, 0x42cf, 0x08fc, 0x08f0, 0x10fe, # @ABCDEFG
                 0x1833, 0x42cc, 0x001f, 0x8c30, 0x003c, 0x0533, 0x8133, 0x00ff, # HIJKLMNO
                 0x18f1, 0x80ff, 0x98f1, 0x18ee, 0x42c0, 0x003f, 0x2430, 0xa033, # PQRSTUVW
                 0xa500, 0x4500, 0x24cc, 0x4284, 0x8100, 0x4248, 0xa000, 0x000c] # XYZ[\]^_
    glyph_id = ord(ch) - 32 # first printable char is space
    if (glyph_id == 14):
        size = size / 2 # ugh special case period to not look like little 'o'
    if (glyph_id >= 64):
        glyph_id = glyph_id - 32
    segs = char_segs[glyph_id]
    glLineWidth(2.0)
    glBegin(GL_LINES)
    for s in range(16):
        if ((segs & 1) == 1):
            glVertex2f(x +(cx1[s]*size/7)+(cy1[s]/7), y+(cy1[s]*size/7))
            glVertex2f(x +(cx2[s]*size/7)+(cy2[s]/7), y+(cy2[s]*size/7))
        segs = segs >> 1
    glEnd()

def DrawString(s, x, y, size, color):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(ortho_left,ortho_right,ortho_bottom,ortho_top,ortho_near,ortho_far)
    glMatrixMode (GL_MODELVIEW)
    glLoadIdentity()
    l = len(s)
    xx = x
    for i in range(l):
        ch = s[i]
        DrawChar(ch, xx, y, size, color)
        xx += (size * 0.75)
    resetProjection()

def resetProjection():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()                    # Reset The Projection Matrix
    if (ortho_mode == True):
        glOrtho(ortho_left,ortho_right,ortho_bottom,ortho_top,ortho_near,ortho_far)
    else:
        gluPerspective(PERSPECTIVE_FOV, float(window_width)/float(window_height), 0.1, FAR_DIST)
    glMatrixMode(GL_MODELVIEW)    

def InitGround():
    global ground, tilemap
    ground.clear()
    for z in range(GROUND_LENGTH):
        for x in range(GROUND_WIDTH):
            tile = SurfaceTile()
            tile.x = TILE_LENGTH * float(x-(GROUND_WIDTH/2))
            tile.y = 0.0
            tile.z = TILE_LENGTH * float(z-(GROUND_LENGTH/2))
            ground.append(tile)
            tilemap[z * GROUND_WIDTH + x] = tile
            
    for z in range(GROUND_LENGTH):
        for x in range(GROUND_WIDTH):
            tile = tilemap[z * GROUND_WIDTH + x]
            for i in range(-1,2):
                if (((z+i)>=0) and ((z+i)<GROUND_LENGTH)):
                    for j in range(-1,2):
                        if (((x+j)>=0) and ((x+j)<GROUND_WIDTH)):
                            tile.neighbors[((i+1)*3)+j+1]=tilemap[(z+i)*GROUND_WIDTH+(x+j)]
                        
def InitPlants():
    global plants
    plants.clear()
    for p in range(INIT_TREE_COUNT):
        px = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_LENGTH/2) + (random.random()*GROUND_LENGTH))
        pz = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_WIDTH/2)+(random.random()*GROUND_WIDTH))        
        p = Plant(px, 0.0, pz, SEQ_TREE)
        p.stage = STAGE_DORMANT
        p.groundTile = FindTile(px, pz)
        plants.append(p)
    for p in range(INIT_GRASS_COUNT):
        px = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_LENGTH/2) + (random.random()*GROUND_LENGTH))
        pz = SAFE_PLANT_BORDER * TILE_LENGTH * (-(GROUND_WIDTH/2)+(random.random()*GROUND_WIDTH))        
        p = Plant(px, 0.0, pz, SEQ_GRASS)
        p.stage = STAGE_DORMANT
        p.groundTile = FindTile(px, pz)
        plants.append(p)

def FindTile(x, z):
    for tile in ground:
        if ((x >= tile.x) and (z >= tile.z) and (x < (tile.x+TILE_LENGTH)) and (z < (tile.z+TILE_LENGTH))):
            return tile
    return None

def UpdateWorld():
    global ground
    global plants
    global wind_phase

    wind_phase = wind_phase + wind_phase_increment
    for t in ground:
        t.Update()
        
    for p in plants:
        p.Update()

    for rp in remove_list:
        plants.remove(rp)
    remove_list.clear()

# Print message to console, and kick off the main to get it rolling.
if __name__ == "__main__":
    print ("starting garden...")
    main()
