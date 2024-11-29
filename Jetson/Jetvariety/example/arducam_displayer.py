try:
    import cv2
except ImportError:
    print("Start to install opencv...")
    os.system(f'sudo apt-get update')
    os.system(f'sudo apt install nvidia-opencv-dev')
import numpy as np
from datetime import datetime
import array
import fcntl
import os
import argparse
from ArduCamUtilities import ArduCamUtilities
try:
    from utils import ArducamUtils
except ImportError as e:
    import sys

    print(e)
    print("Start to install python environment...")

    if sys.version[0] == 2:
        print("Try to install python-pip...")
        os.system(f'sudo apt install python-pip')       
    if sys.version[0] == 3:
        print("Try to install python3-pip...")
        os.system(f'sudo apt install python3-pip')

    try:
        from pip import main as pipmain
    except ImportError:
        from pip._internal import main as pipmain

    print("Try to install jetson-stats...")
    pipmain(['install', 'jetson-stats'])

    print("Try to install v4l2-fix...")
    pipmain(['install', 'v4l2-fix'])

    from utils import ArducamUtils
import time
import sys

def resize(frame, dst_width):
    width = frame.shape[1]
    height = frame.shape[0]
    scale = dst_width * 1.0 / width
    return cv2.resize(frame, (int(scale * width), int(scale * height)))

def display(cap, arducam_utils, fps = False):
    counter = 0
    start_time = datetime.now()
    frame_count = 0
    start = time.time()
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    while True:
        ret, frame_raw = cap.read()
        if not ret:
            print("Failed to grab a frame.")
            break
        counter += 1
        frame_count += 1

                        # # Step 1: Convert the RG10-packed data to a usable format
                        # # Assuming RG10 stores 10-bit data in 16-bit format (little-endian)
                        # width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        # height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        #
                        # frame_bytes = frame_raw.tobytes()
                        #
                        # # frame_16bit = np.frombuffer(frame_raw, dtype=np.uint16).reshape((height, width))
                        # frame_16bit = np.frombuffer(frame_bytes, dtype='<u2').reshape((height, width))
                        #
                        # # Extract the 10-bit data (if necessary)
                        # frame_10bit = (frame_16bit & 0x03FF).astype(np.uint16)  # Keep only 10 bits
                        #
                        # # Step 2: Convert to 8-bit for display purposes
                        # frame_8bit = (frame_10bit >> 2).astype(np.uint8)
                        #
                        # # Step 3: Demosaic the Bayer pattern to BGR
                        # bgr_image = cv2.cvtColor(frame_8bit, cv2.COLOR_BAYER_RG2BGR)
                        #
                        # # Step 4: Display the processed frame
                        # bgr_image = resize(bgr_image, 1280.0)
                        # cv2.imshow("RG10 Camera Feed", bgr_image)



        frame_2d = frame_raw.reshape(height, width) if arducam_utils.convert2rgb == 0 else frame_raw
        frame = arducam_utils.convert(frame_2d)

        frame = resize(frame, 1280.0)
        # display
        cv2.imshow("Arducam", frame)
        ret = cv2.waitKey(1)
        # press 'q' to exit.
        if ret == ord('q'):
            break

        if fps and time.time() - start >= 1:
            if sys.version[0] == '2':
                print("fps: {}".format(frame_count))    
            else:
                print("fps: {}".format(frame_count),end='\r')
            start = time.time()
            frame_count = 0 

    end_time = datetime.now()
    elapsed_time = end_time - start_time
    avgtime = elapsed_time.total_seconds() / counter
    print ("Average time between frames: " + str(avgtime))
    print ("Average FPS: " + str(1/avgtime))

def fourcc(a, b, c, d):
    return ord(a) | (ord(b) << 8) | (ord(c) << 16) | (ord(d) << 24)

def pixelformat(string):
    if len(string) != 3 and len(string) != 4:
        msg = "{} is not a pixel format".format(string)
        raise argparse.ArgumentTypeError(msg)
    if len(string) == 3:
        return fourcc(string[0], string[1], string[2], ' ')
    else:
        return fourcc(string[0], string[1], string[2], string[3])

def show_info(arducam_utils):
    _, sensor_id, firmware_version, serial_number = arducam_utils.get_device_info()
    print("\nFirmware Version: {}".format(firmware_version))
    print("Sensor ID: 0x{:04X}".format(sensor_id))
    print("Serial Number: 0x{:08X}".format(serial_number))

def process_arguments():
    parser = argparse.ArgumentParser(description='Arducam Jetson Nano MIPI Camera Displayer.')

    parser.add_argument('--device', default=0, type=int, nargs='?', help='/dev/videoX default is 0')
    parser.add_argument('--pixelformat', type=pixelformat, help="set pixelformat")
    parser.add_argument('--width', type=lambda x: int(x, 0), help="set width of image")
    parser.add_argument('--height', type=lambda x: int(x, 0), help="set height of image")
    parser.add_argument('--fps', action='store_true', help="display fps")
    parser.add_argument('--channel', default=-1, type=int, nargs='?', help="When using Camarray's single channel, use this parameter to switch channels. (E.g. ov9781/ov9281 Quadrascopic Camera Bundle Kit)")

    args_local = parser.parse_args()
    return args_local

if __name__ == "__main__":
    args = process_arguments()
    print("\nProgram starting... User input arguments are: " + str(vars(args)))

    arducam_utils = ArduCamUtilities(args.device)

    # open camera
    cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
    # set pixel format, width, height, etc.
    if args.pixelformat != None:
        if not cap.set(cv2.CAP_PROP_FOURCC, args.pixelformat):
            print("Failed to set pixel format.")
    if args.width != None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    if args.height != None:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if args.channel in range(0, 4):
        arducam_utils.write_dev(ArducamUtils.CHANNEL_SWITCH_REG, args.channel)

    # ''' Set the FourCC to RG10 '''
    # cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'RG10'))
    # print("\nFourCC 设置成功") if int(cap.get(cv2.CAP_PROP_FOURCC)) == cv2.VideoWriter_fourcc(*'RG10') else print("FourCC 设置失败")

    arducam_utils.show_camera_info()
    # turn off RGB conversion
    if arducam_utils.convert2rgb == 0:
        cap.set(cv2.CAP_PROP_CONVERT_RGB, arducam_utils.convert2rgb)

    # begin display
    display(cap, arducam_utils, args.fps)

    # release camera
    cap.release()
