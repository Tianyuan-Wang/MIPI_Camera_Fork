import v4l2
import fcntl
import array
import ctypes
import cv2
import numpy as np
from ArduCamControlsUtilities import ArduCamControlUtilities


class ArduCamUtilities(ArduCamControlUtilities):
    pixfmt_map_default = {
        v4l2.V4L2_PIX_FMT_SBGGR10:{ "depth":10, "cvt_code": cv2.COLOR_BAYER_RG2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SGBRG10:{ "depth":10, "cvt_code": cv2.COLOR_BAYER_GR2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SGRBG10:{ "depth":10, "cvt_code": cv2.COLOR_BAYER_GB2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SRGGB10:{ "depth":10, "cvt_code": cv2.COLOR_BAYER_BG2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_Y10:{ "depth":10, "cvt_code": -1, "convert2rgb": 0},
    }
    pixfmt_map_xavier_nx = {
        v4l2.V4L2_PIX_FMT_SBGGR10:{ "depth":16, "cvt_code": cv2.COLOR_BAYER_RG2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SGBRG10:{ "depth":16, "cvt_code": cv2.COLOR_BAYER_GR2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SGRBG10:{ "depth":16, "cvt_code": cv2.COLOR_BAYER_GB2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SRGGB10:{ "depth":16, "cvt_code": cv2.COLOR_BAYER_BG2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_Y10:{ "depth":16, "cvt_code": -1, "convert2rgb": 0},
    }

    pixfmt_map_raw8 = {
        v4l2.V4L2_PIX_FMT_SBGGR8:{ "depth":8, "cvt_code": cv2.COLOR_BAYER_RG2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SGBRG8:{ "depth":8, "cvt_code": cv2.COLOR_BAYER_GR2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SGRBG8:{ "depth":8, "cvt_code": cv2.COLOR_BAYER_GB2BGR, "convert2rgb": 0},
        v4l2.V4L2_PIX_FMT_SRGGB8:{ "depth":8, "cvt_code": cv2.COLOR_BAYER_BG2BGR, "convert2rgb": 0},
    }

    AUTO_CONVERT_TO_RGB = { "depth":-1, "cvt_code": -1, "convert2rgb": 1}

    def __init__(self, device_num):
        super().__init__(device_num)
        self.pixfmt_map = self.get_colour_conversion_map()
        self.config = self.get_pixfmt_cfg()

    def get_colour_conversion_map(self) -> dict:
        this_platform_type = self.get_platform_type()
        # Jetson Model
        pixfmt_map = None
        if "Xavier NX" in this_platform_type:
            pixfmt_map = ArduCamUtilities.pixfmt_map_xavier_nx
        elif "Orin NX" in this_platform_type:
            pixfmt_map = ArduCamUtilities.pixfmt_map_xavier_nx
        elif "Orin Nano" in this_platform_type:
            pixfmt_map = ArduCamUtilities.pixfmt_map_xavier_nx
        elif "AGX Orin" in this_platform_type:
            pixfmt_map = ArduCamUtilities.pixfmt_map_xavier_nx
        return pixfmt_map

    def convert(self, frame):
        if self.convert2rgb == 1:
            return frame

        if self.depth != -1:
            frame = cv2.convertScaleAbs(frame, None, 256.0 / (1 << self.depth))
            frame = frame.astype(np.uint8)

        if self.cvt_code != -1:
            frame = cv2.cvtColor(frame, self.cvt_code)

        return frame

    def get_pixelformat(self):
        fmt = v4l2.v4l2_format()
        fmt.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        ret = fcntl.ioctl(self.vd, v4l2.VIDIOC_G_FMT, fmt)
        return ret, fmt.fmt.pix.pixelformat

    def set_pixelformat(self, target_pixfmt=v4l2.V4L2_PIX_FMT_SRGGB10):
        """

        :param target_pixfmt:
        :return:
        """
        ''' Query the current format first '''
        fmt = v4l2.v4l2_format()
        fmt.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        ret = fcntl.ioctl(self.vd, v4l2.VIDIOC_G_FMT, fmt)

        ''' If the current format is not the target one, attempt to set it explicitly '''
        print("\nV4L2:")
        if fmt.fmt.pix.pixelformat != target_pixfmt:
            print(f"Current pixel format is 0x{fmt.fmt.pix.pixelformat:08x}, changing to 0x{target_pixfmt:08x}")
            fmt.fmt.pix.pixelformat = target_pixfmt
            try:
                ret = fcntl.ioctl(self.vd, v4l2.VIDIOC_S_FMT, fmt)
                print(f"Pixel format set to 0x{target_pixfmt:08x}")
            except Exception as e:
                print(f"Failed to set pixel format to 0x{target_pixfmt:08x}:", e)
                ''' Revert to actual settings if failed '''
                ret = fcntl.ioctl(self.vd, v4l2.VIDIOC_G_FMT, fmt)
        else:
            print(f"Current pixel format is already 0x{target_pixfmt:08x}, no need to update")

    def get_pixfmt_cfg(self):
        ret, pixfmt = self.get_pixelformat()
        self.set_pixelformat()

        print("\nV4L2:")

        # 初始化默认配置为 AUTO_CONVERT_TO_RGB
        chosen_config = ArduCamUtilities.AUTO_CONVERT_TO_RGB
        chosen_pixfmt = None

        # 列出所有相机支持的像素格式
        print("The camera supported pixel formats: ")
        camera_supported_formats = self.get_pixelformats()
        for element in camera_supported_formats:
            print(f"{element['index']}: {element['description']} (pixelformat: 0x{element['pixelformat']:08x})")

        # 列出所有程序支持的像素格式，然后让用户选择
        print("The program supported pixel formats: ")
        # 检查当前像素格式是否在 pixfmt_map_raw8 中
        pf = ArduCamUtilities.pixfmt_map_raw8.get(pixfmt, None)
        if pf is not None:
            chosen_config = pf
        else:
            # 枚举所有支持的像素格式并收集匹配的配置
            fmtdesc = v4l2.v4l2_fmtdesc()
            fmtdesc.index = 0
            fmtdesc.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE

            matches = []
            while True:
                try:
                    fcntl.ioctl(self.vd, v4l2.VIDIOC_ENUM_FMT, fmtdesc)
                    # 检查当前枚举的像素格式是否在 pixfmt_map 中
                    pixfmt_config = self.pixfmt_map.get(fmtdesc.pixelformat, None)
                    if pixfmt_config is not None:
                        matches.append({
                            "index": fmtdesc.index,
                            "pixelformat": fmtdesc.pixelformat,
                            "description": fmtdesc.description,
                            "config": pixfmt_config
                        })
                    fmtdesc.index += 1
                except Exception as e:
                    break  # 枚举完成或发生错误，退出循环

            if matches:
                print("找到多个程序支持的像素格式配置：")
                for idx, match in enumerate(matches):
                    pixfmt_hex = f"0x{match['pixelformat']:08X}"
                    print(f"{idx}: {match['description']} (pixelformat: {pixfmt_hex})")

                while True:
                    try:
                        selection = input(f"请选择一个像素格式配置 (0-{len(matches) - 1})，或按回车使用默认配置: ")
                        if selection == "":
                            print("使用默认配置: AUTO_CONVERT_TO_RGB")
                            break  # 保持默认配置
                        selection = int(selection)
                        if 0 <= selection < len(matches):
                            chosen_config = matches[selection]["config"]
                            chosen_pixfmt = matches[selection]["pixelformat"]
                            print(f"已选择: {matches[selection]['description']} (pixelformat: 0x{matches[selection]['pixelformat']:08X})")
                            break
                        else:
                            print(f"请输入一个介于 0 和 {len(matches) - 1} 之间的数字。")
                    except ValueError:
                        print("无效输入，请输入一个数字。")
            # 如果没有找到匹配的配置，保持默认配置 AUTO_CONVERT_TO_RGB

        ''' Print out the config the program will use. '''
        key_name = get_v4l2_key_name(chosen_pixfmt, v4l2)
        print(f"Key: {key_name}, Value: {self.pixfmt_map[chosen_pixfmt]}")

        # 在函数末尾统一返回选择的配置
        return chosen_config

    def get_pixelformats(self):
        supported_formats = []
        fmtdesc = v4l2.v4l2_fmtdesc()
        fmtdesc.index = 0
        fmtdesc.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
        while True:
            try:
                fcntl.ioctl(self.vd, v4l2.VIDIOC_ENUM_FMT, fmtdesc)
                supported_formats.append({
                    "index": fmtdesc.index,
                    "pixelformat": fmtdesc.pixelformat,
                    "description": fmtdesc.description
                })
                fmtdesc.index += 1
            except Exception as e:
                break
        return supported_formats

    def get_framesizes(self, pixel_format = v4l2.V4L2_PIX_FMT_Y16):
        framesizes = []
        framesize = v4l2.v4l2_frmsizeenum()
        framesize.index = 0
        framesize.pixel_format = pixel_format
        while True:
            try:
                fcntl.ioctl(self.vd, v4l2.VIDIOC_ENUM_FRAMESIZES, framesize)
                framesizes.append((framesize.discrete.width, framesize.discrete.height))
                framesize.index += 1
            except Exception as e:
                break
        return framesizes

    def __getattr__(self, key):
        return self.config.get(key)

def get_v4l2_key_name(key, module):
    # Reverse lookup for key names
    constants = {value: name for name, value in vars(module).items() if name.startswith("V4L2_PIX_FMT_")}
    return constants.get(key, f"Unknown ({key})")

def print_ctypes_structure(obj, indent=0):
    """递归打印 ctypes 结构体和联合体字段"""
    if isinstance(obj, ctypes.Structure):
        print(" " * indent + f"{obj.__class__.__name__}:")
        for field_name, field_type in obj._fields_:
            value = getattr(obj, field_name)
            if isinstance(value, ctypes.Structure):
                print(" " * (indent + 2) + f"{field_name} ({field_type.__name__}):")
                print_ctypes_structure(value, indent + 4)
            elif isinstance(value, ctypes.Union):
                print(" " * (indent + 2) + f"{field_name} (Union {field_type.__name__}):")
                print_union_structure(value, indent + 4)
            elif isinstance(value, ctypes.Array):
                print(" " * (indent + 2) + f"{field_name} (Array {field_type.__name__}): [{', '.join(map(str, value))}]")
            else:
                print(" " * (indent + 2) + f"{field_name} ({field_type.__name__}): {value}")
    else:
        print(" " * indent + str(obj))

def print_union_structure(union_obj, indent=0):
    """打印 ctypes 联合体的所有可能字段"""
    print(" " * indent + f"Union: {union_obj.__class__.__name__}")
    for field_name, field_type in union_obj._fields_:
        value = getattr(union_obj, field_name)
        if isinstance(value, ctypes.Structure):
            print(" " * (indent + 2) + f"{field_name} ({field_type.__name__}):")
            print_ctypes_structure(value, indent + 4)
        else:
            print(" " * (indent + 2) + f"{field_name} ({field_type.__name__}): {value}")
