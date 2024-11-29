import fcntl
import ctypes

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ  = 2


def _IOC(dir_, type_, nr, size):
    return (
        ctypes.c_int32(dir_ << _IOC_DIRSHIFT).value |
        ctypes.c_int32(ord(type_) << _IOC_TYPESHIFT).value |
        ctypes.c_int32(nr << _IOC_NRSHIFT).value |
        ctypes.c_int32(size << _IOC_SIZESHIFT).value)

def _IOC_TYPECHECK(t):
    return ctypes.sizeof(t)

def _IO(type_, nr):
    return _IOC(_IOC_NONE, type_, nr, 0)

def _IOW(type_, nr, size):
    return _IOC(_IOC_WRITE, type_, nr, _IOC_TYPECHECK(size))

def _IOR(type_, nr, size):
    return _IOC(_IOC_READ, type_, nr, _IOC_TYPECHECK(size))

def _IOWR(type_, nr, size):
    return _IOC(_IOC_READ | _IOC_WRITE, type_, nr, _IOC_TYPECHECK(size))

BASE_VIDIOC_PRIVATE = 192

class arducam_i2c(ctypes.Structure):
    _fields_ = [
        ('reg', ctypes.c_uint16),
        ('val', ctypes.c_uint16),
    ]

class arducam_dev(ctypes.Structure):
    _fields_ = [
        ('reg', ctypes.c_uint16),
        ('val', ctypes.c_uint32),
    ]


VIDIOC_R_I2C = _IOWR('V', BASE_VIDIOC_PRIVATE + 0, arducam_i2c)
VIDIOC_W_I2C = _IOWR('V', BASE_VIDIOC_PRIVATE + 1, arducam_i2c)
VIDIOC_R_DEV = _IOWR('V', BASE_VIDIOC_PRIVATE + 2, arducam_dev)
VIDIOC_W_DEV = _IOWR('V', BASE_VIDIOC_PRIVATE + 3, arducam_dev)


class ArduCamControlUtilities(object):

    DEVICE_REG_BASE     = 0x0100
    PIXFORMAT_REG_BASE  = 0x0200
    FORMAT_REG_BASE     = 0x0300
    CTRL_REG_BASE       = 0x0400
    SENSOR_REG_BASE     = 0x500

    STREAM_ON                = (DEVICE_REG_BASE | 0x0000)
    FIRMWARE_VERSION_REG     = (DEVICE_REG_BASE | 0x0001)
    SENSOR_ID_REG            = (DEVICE_REG_BASE | 0x0002)
    DEVICE_ID_REG            = (DEVICE_REG_BASE | 0x0003)
    FIRMWARE_SENSOR_ID_REG   = (DEVICE_REG_BASE | 0x0005)
    SERIAL_NUMBER_REG        = (DEVICE_REG_BASE | 0x0006)
    CHANNEL_SWITCH_REG       = (DEVICE_REG_BASE | 0x0008)

    PIXFORMAT_INDEX_REG     = (PIXFORMAT_REG_BASE | 0x0000)
    PIXFORMAT_TYPE_REG      = (PIXFORMAT_REG_BASE | 0x0001)
    PIXFORMAT_ORDER_REG     = (PIXFORMAT_REG_BASE | 0x0002)
    MIPI_LANES_REG          = (PIXFORMAT_REG_BASE | 0x0003)

    RESOLUTION_INDEX_REG    = (FORMAT_REG_BASE | 0x0000)
    FORMAT_WIDTH_REG        = (FORMAT_REG_BASE | 0x0001)
    FORMAT_HEIGHT_REG       = (FORMAT_REG_BASE | 0x0002)

    CTRL_INDEX_REG  = (CTRL_REG_BASE | 0x0000)
    CTRL_ID_REG     = (CTRL_REG_BASE | 0x0001)
    CTRL_MIN_REG    = (CTRL_REG_BASE | 0x0002)
    CTRL_MAX_REG    = (CTRL_REG_BASE | 0x0003)
    CTRL_STEP_REG   = (CTRL_REG_BASE | 0x0004)
    CTRL_DEF_REG    = (CTRL_REG_BASE | 0x0005)
    CTRL_VALUE_REG  = (CTRL_REG_BASE | 0x0006)

    SENSOR_RD_REG = (SENSOR_REG_BASE |0x0001)
    SENSOR_WR_REG = (SENSOR_REG_BASE |0x0002)

    NO_DATA_AVAILABLE = 0xFFFFFFFE

    DEVICE_ID = 0x0030

    def __init__(self, device_num):
        self.vd = open('/dev/video{}'.format(device_num), 'w')

    @staticmethod
    def get_platform_type():
        from jtop import jtop
        with jtop() as jetson:
            if jetson.ok():
                for name_category, category in jetson.board.items():
                    if name_category == "hardware":
                        environment_vars = category['Module']
        print("Hardware is: {}".format(environment_vars))
        return environment_vars

    def read_sensor(self, reg):
        i2c = arducam_i2c()
        i2c.reg = reg
        fcntl.ioctl(self.vd, VIDIOC_R_I2C, i2c)
        return i2c.val

    def write_sensor(self, reg, val):
        i2c = arducam_i2c()
        i2c.reg = reg
        i2c.val = val
        return fcntl.ioctl(self.vd, VIDIOC_W_I2C, i2c)

    def read_dev(self, reg):
        dev = arducam_dev()
        dev.reg = reg
        ret = fcntl.ioctl(self.vd, VIDIOC_R_DEV, dev)
        return ret, dev.val

    def write_dev(self, reg, val):
        dev = arducam_dev()
        dev.reg = reg
        dev.val = val
        return fcntl.ioctl(self.vd, VIDIOC_W_DEV, dev)

    def get_device_info(self):
        _, fw_sensor_id = self.read_dev(ArduCamControlUtilities.FIRMWARE_SENSOR_ID_REG)
        _, sensor_id = self.read_dev(ArduCamControlUtilities.SENSOR_ID_REG)
        _, fw_version = self.read_dev(ArduCamControlUtilities.FIRMWARE_VERSION_REG)
        _, serial_number = self.read_dev(ArduCamControlUtilities.SERIAL_NUMBER_REG)
        return fw_sensor_id, sensor_id, fw_version, serial_number
