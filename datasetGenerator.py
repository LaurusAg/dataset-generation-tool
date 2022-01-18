#!/usr/bin/env python

# TODO:
# 

# BUG:
# _Can't erase local datase folder when deleting dataset.

# Dependencies: 
# pip install pysmb
# pip install opencv

import cv2
import numpy as np
import uuid
import pickle
import os
import math

dirname = os.path.dirname(__file__)
path = os.path.join(dirname, 'generated_datasets/')
from tkinter import Tk
from tkinter.filedialog import askdirectory
Tk().withdraw()

print("")
print("--- Image Dataset Generation Tool ---")

# Capture with OpenCV
capture = cv2.VideoCapture(0)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 10000)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 10000)

# Check for calibration file
will_calibrate = False
calib_file_path = "./calibration_data.pkl"
cd = {}
if os.path.exists(calib_file_path):
    resp = input("Calibration file found. Do you want to load it ? (Y/n): ")
    if resp is None or resp == "N" or resp == "n":
        resp = input("The calibraiton file will be overwriten. Continue anyways ? (y/N): ")
        if resp == "y" or resp == "Y":
            will_calibrate = True
        else:
            os._exit(0)
    else:
        with open(calib_file_path, 'rb') as f:
            cd = pickle.load(f)
else:
    print("No calibration file found.")
    will_calibrate = True

if will_calibrate:
    # Stereo Camera
    resp = input("Are you using a stereo camera ? (y/N): ")
    if resp == "y" or resp == "Y":
        cd['stereo_camera'] = True
    else:
        cd['stereo_camera'] = False

    # GUI Width
    cd['gui_width'] = 900
    resp = input("Enter the desired GUI width (900px): ")
    if resp.isnumeric():
        cd['gui_width'] = int(resp)

    # GUI Width adaptation
    ret,numpy_img = capture.read()
    if cd['stereo_camera']:
        width = numpy_img.shape[1]
        new_width = int(math.floor(width/2))
        cd['new_width'] = new_width
        numpy_img = numpy_img[:,:new_width,:]
    img_dim = numpy_img.shape[1], numpy_img.shape[0]
    ratio = img_dim[0]/img_dim[1]
    cd['dims'] = (cd['gui_width'], int(cd['gui_width']/ratio))

    # Rotate if needed
    print("Rotation correction")
    cv2.namedWindow("Calibration")
    cv2.setWindowProperty("Calibration", cv2.WND_PROP_TOPMOST, 1)
    cv2.displayOverlay("Calibration", "Rotate image using arrows if needed, otherwise hit enter...", 0)
    angle = 0
    while True:
        ret,numpy_img = capture.read()
        if cd['stereo_camera']: numpy_img = numpy_img[:,:new_width,:]
        numpy_img = cv2.resize(numpy_img, cd['dims'], interpolation = cv2.INTER_AREA)
        if angle != 0: numpy_img = cv2.rotate(numpy_img, int(angle/90 - 1))
        cv2.imshow("Calibration", numpy_img)
        key = cv2.waitKey(1)
        if key == 13: break
        if key == 81: angle -= 90
        if key == 83: angle += 90
        if angle < 0: angle += 360
        if angle >= 360: angle -=360
    cd['rotate'] = angle
    cv2.destroyAllWindows()

    # Perspective correction
    resp = input("Should a perspective correction be done ? (y/N): ")
    if resp == "y" or resp == "Y":

        cv2.namedWindow("Calibration")
        cv2.setWindowProperty("Calibration", cv2.WND_PROP_TOPMOST, 1)
        cv2.displayOverlay("Calibration", "Adjust ROI and Perspective - Hit any key to continue", 0)

        height = numpy_img.shape[0]
        width = numpy_img.shape[1]
        polyPts = np.array([[-1,-1],[1,-1],[1,1],[-1,1]], np.int32)
        polyPts[:,0] *= int(width/4)
        polyPts[:,1] *= int(height/4)
        polyPts[:,0] += int(width/2)
        polyPts[:,1] += int(height/2)
        polyPts = polyPts.reshape((-1, 1, 2))

        cp = numpy_img.copy()
        cv2.polylines(cp, [polyPts], True, (0,200,0), 2)
        cv2.imshow("Calibration", cp)

        def points_distance(pointA, pointB):
            return np.sqrt((pointA[0]-pointB[0])**2 + (pointA[1]-pointB[1])**2) 

        def adjustPerspectivePolygon(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                distances = []
                for point in polyPts:
                    distances.append(points_distance((x,y), point[0]))
                idx = np.argmin(distances)
                polyPts[idx][0] = [x,y]
                cp = numpy_img.copy()
                cv2.polylines(cp, [polyPts], True, (0,200,0), 2)
                cv2.imshow("Calibration", cp)
            
        cv2.setMouseCallback("Calibration", adjustPerspectivePolygon)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        cd['originalWidth'] = int(input("Enter original horizontal dimention in mm: "))
        cd['originalHeight'] = int(input("Enter original vertical dimention in mm: "))
        if cd['originalHeight'] == 0 or cd['originalWidth'] == 0: os._exit(0)

        polyPts = polyPts.reshape(4,2)

        maxWidth = max(points_distance(polyPts[0], polyPts[1]), points_distance(polyPts[2], polyPts[3]))
        maxHeight = max(points_distance(polyPts[1], polyPts[2]), points_distance(polyPts[3], polyPts[0]))
        cd['scale'] = max(maxWidth/cd['originalWidth'], maxHeight/cd['originalHeight'])
        originalPts = np.array([[0,0],[cd['originalWidth'],0],[cd['originalWidth'],cd['originalHeight']],[0,cd['originalHeight']]], np.int32)
        cd['matrix'] = cv2.getPerspectiveTransform(polyPts.astype(np.float32), originalPts.astype(np.float32)* cd['scale'])
        cd['perspective_correction'] = True
    else:
        cd['perspective_correction'] = False

    # Save calibration data
    with open(calib_file_path, 'wb') as f:
        pickle.dump(cd, f)
    print("Calibration file saved.")

# Select path to store
# dirs = os.listdir(path)
# i = 0
# while True:
#     if str(i) not in dirs:
#         print(i, "available")
#         break
#     i += 1
# path += "/" + str(i)

# Dataset folder name
dataset_name = input("Enter the dataset name (leave empty for default format DATE-TIME): ")
if len(dataset_name) == 0:
    import time
    dataset_name = time.strftime("%Y%m%d-%H%M%S")
path += dataset_name + "/"
if os.path.isdir(path):
    print("Directory already exists. New images will be added to the existing dataset.")
else:
    os.mkdir(path)

# Main Loop
print("")
print("Running...")
print(" - Press the space bar or enter to capture")
print(" - Press Q or escape to exit")
cv2.namedWindow("OpenCV Camera")
cv2.setWindowProperty("OpenCV Camera", cv2.WND_PROP_TOPMOST, 1)
cv2.displayOverlay("OpenCV Camera", "Rotate image using arrows if needed, otherwise hit enter...", 0)

flag = False
while True:
    ret,numpy_img = capture.read()
    if cd['stereo_camera']: numpy_img = numpy_img[:,:cd['new_width'],:]
    numpy_img = cv2.resize(numpy_img, cd['dims'], interpolation = cv2.INTER_AREA)
    if cd['rotate'] != 0: numpy_img = cv2.rotate(numpy_img, int(cd['rotate']/90 - 1))
    if cd['perspective_correction']: numpy_img = cv2.warpPerspective(numpy_img, cd['matrix'], (int(cd['originalWidth']* cd['scale']), int(cd['originalHeight'] * cd['scale'])))
    cv2.imshow("OpenCV Camera", numpy_img)


    key = cv2.waitKey(1)
    if key == 13 or key == 32:
        flag = True
        cv2.displayOverlay("OpenCV Camera", "Image saved", 1000)
        cv2.imwrite(path + str(uuid.uuid4()) + '.jpg', numpy_img)
    if key == ord('q') or key == 113:
        break

cv2.destroyAllWindows()
if not flag:
    print("Exiting...")
    os._exit(0)

# Copy generated dataset to server
print("")
resp = input("Do you want to send the dataset to the server ? (Y/n): ")
if resp is None or resp == "N" or resp == "n":
    print("Exiting...")
    os._exit(0)

print("Copying generated dataset to server...")
from smb.SMBConnection import SMBConnection

servers_list = [
    {"ip": "192.168.195.158", "hostname": "PCFEDE" },
]

conn = None
server = None
for srv in servers_list:
    try:
        conn = SMBConnection("fran6ko", "dummy", "dummy", srv["hostname"], use_ntlm_v2 = True)
        conn.connect(srv["ip"], port=139, timeout=5)
        server = srv
    except Exception as e:
        conn = None
        continue

if conn is None:
    print("Couldn't find an online server. Dataset is saved locally.")
else:
    print("Connected to", server["hostname"],"at", server["ip"])
    
    try:
        conn.getAttributes("datasets", dataset_name)
        print("Directory already exists. New images will be added to the existing dataset.")
    except Exception:
        conn.createDirectory("datasets", dataset_name)

    files = os.listdir(path)
    for i, file in enumerate(files):
        print(file, "-", int((i+1)*100/len(files)), "%")
        if not os.path.isfile(os.path.join(path, file)):
            continue
        file2transfer = open(os.path.join(path, file),"rb")
        conn.storeFile("datasets", "/" + dataset_name + "/" + file, file2transfer)

    print("Done.")
    print("")
    resp = input("Should the local dataset be erased ? (y/N): ")
    if resp == "y" or resp == "Y":
        import shutil
        shutil.rmtree(path[:-1], ignore_errors=True)

print("Exiting...")