try:
    import smbus2 as smbus
except (ImportError):
    import smbus
from PIL import Image

VERSION = 0.15
AUTHOR = "c. bluoss"
LICENSE = "MIT License"


class GridEye():

    """
    GridEye class for easy handling of GridEYE AMG88 i2c modules.
    Although Grid-EYE%20SPECIFICATIONS(Reference).pdf may still be helpful.

    TODO: Interrupts
    """

    def __init__(self, i2c_address=0x68, i2c_bus=smbus.SMBus(1)):
        self.i2c = {"bus": i2c_bus, "address": i2c_address}
        self.read_byte = self.i2c["bus"].read_byte_data
        self.write_byte = self.i2c["bus"].write_byte_data
        self.modes = {0x00: "NORM",
                      0x10: "SLEEP",
                      0x20: "STANDBY60",
                      0x21: "STANDBY10"
                     }

    def get_mode(self):
        mode = self.read_byte(self.i2c["address"], 0x00)
        return self.modes.get(mode)

    def set_mode(self, mode="NORM"):
        if isinstance(mode, str):
            mode = {v: k for k, v in self.modes.items()}.get(mode)
        self.write_byte(self.i2c["address"], 0x00, mode)

    def reset(self, flags_only=False):
        if flags_only:
            reset = 0x30
        else:
            reset = 0x3F
        self.write_byte(self.i2c["address"], 0x01, reset)

    def get_fps(self):
        fps = self.read_byte(self.i2c["address"], 0x02)
        if fps is 0:
            return 10
        else:
            return 1

    def set_fps(self, fps=10):
        if fps is not 1:
            fps = 0x00
        self.write_byte(self.i2c["address"], 0x02, fps)

    def get_interrupt_ctrl(self):
        """
        returns a boolean tuple (interupt_enabled, interupt_mode)
        """
        intc = self.read_byte(self.i2c["address"], 0x03)
        return (1 & intc is 1), (2 & intc is 2)

    def set_interupt_ctrl(self, enabled=False, mode=False):
        """
        mode = False -> difference mode
        mode = True  -> absolute mode
        """
        intc = 0x0
        if enabled:
            intc += 1
        if mode:
            intc += 2
        self.write_byte(self.i2c["address"], 0x03, intc)

    def get_states(self):
        """
        returns a tuple of (
            Interrupt Outbreak,
            Temperature Output Overflow,
            Thermistor Temperature Output Overflow
            )
        from 0x04
        """
        state = self.read_byte(self.i2c["address"], 0x04)
        return (1 & state is 1), (2 & state is 2), (4 & state is 4)

    def clear_states(self, interrupt=False, temp_overflow=False, thermistor_overflow=False):
        clear = 0x00
        if interrupt:
            clear += 1
        if temp_overflow:
            clear += 2
        if thermistor_overflow:
            clear += 4
        self.write_byte(self.i2c["address"], 0x05, clear)

    def set_moving_average(self, twice=False):
        # not quite sure how this works.
        if twice:
            value = 0x20
        else:
            value = 0
        self.write_byte(self.i2c["address"], 0x07, value)

    def set_interrupt_limits(self, lower_limit, upper_limit, hysteresis_level):
        lower_limit = split_in_2bytes(int2twoscomplement(lower_limit))
        upper_limit = split_in_2bytes(int2twoscomplement(upper_limit))
        hysteresis_level = split_in_2bytes(int2twoscomplement(hysteresis_level))
        self.write_byte(self.i2c["address"], 0x08, upper_limit[1])
        self.write_byte(self.i2c["address"], 0x09, upper_limit[0])

        self.write_byte(self.i2c["address"], 0x0A, lower_limit[1])
        self.write_byte(self.i2c["address"], 0x0B, lower_limit[0])

        self.write_byte(self.i2c["address"], 0x0C, hysteresis_level[1])
        self.write_byte(self.i2c["address"], 0x0D, hysteresis_level[0])

    def get_interrupts(self, reset=False):
        """
        Returns current interrupts and optionally resets the interrupt table.
        Format is a list of tuples (line, pixel in line)
        """
        interrupts = []
        data = self.i2c["bus"].read_i2c_block_data(self.i2c["address"], 0x10, 8)
        for i in range(8):
            for bit in range(8):
                if data[i] & 2**bit != 0:
                    interrupts.append((i, bit))

        if reset:
            self.clear_states(interrupt=True)
        return interrupts

    def get_thermistor_temp(self, raw=False):
        """
        returns the thermistor temperature in .25°C resolution
        TODO: high res option with possible 0.0625℃ resolution
        """
        upper = self.read_byte(self.i2c["address"], 0x0F) << 6
        lower = self.read_byte(self.i2c["address"], 0x0E) >> 2
        complete = upper + lower
        if not raw:
            if complete > 512:
                complete -= 1024
                complete = -complete
            return complete / 4
        else:
            return complete

    def get_sensor_data(self, mode="TEMP", remap=True):
        """
        returns the sensor data, supporting different modes
        "TEMP" -> [8][8] Array of temp values
        "GRAYIMAGE" -> a 8x8 pixel image with optional remapping
        +
        min, max values as [value, x,y]
        NOTE: READ is done per line. the raspberry pi doesn't like reading 128
        bytes at once.
        """
        lines = []
        minv = [500, 0, 0]
        maxv = [-500, 0, 0]
        for line in range(8):
            offset = 0x80+line*16
            block = self.i2c["bus"].read_i2c_block_data(
                self.i2c["address"], offset, 16)
            values = []
            for i in range(0, 16, 2):
                upper = block[i+1] << 8
                lower = block[i]
                val = upper + lower
                if 2048 & val == 2048:
                    val -= 4096
                val = val/4
                if val < minv[0]:
                    minv = [val, i//2, line]
                if val > maxv[0]:
                    maxv = [val, i//2, line]
                values.append(val)
            lines.append(values)
        if mode is "TEMP":
            return lines, minv, maxv
        elif mode is "GRAYIMAGE":
            img = Image.new("L", (8, 8))
            pixel = img.load()
            for i in range(8):
                for j in range(8):
                    if remap:
                        value = maprange(
                            (minv[0], maxv[0]), (0, 255), lines[i][j])
                        value = (int(value),)
                    else:
                        value = (int(lines[i][j]), )
                    pixel[i, j] = value
            return img, minv, maxv


def int2twoscomplement(value, bits=12):
    """returning a integer which is equal to value as two's complement"""
    if value > 0:
        return value
    else:
        return (1 << bits) + num
def split_in_2bytes(value):
    """
    Returns a tuple with 2 integers (upper,lower) matching the according bytes
    The AMG88 usually uses 2 byte to store 12bit values.
    """
    upper = value >> 9
    lower = 0b011111111 & value
    return (upper, lower)

def maprange(a, b, s):
    """remap values linear to a new range"""
    (a1, a2), (b1, b2) = a, b
    return b1 + ((s - a1) * (b2 - b1) / (a2 - a1))

if __name__ == '__main__':
    from time import sleep
    from pprint import pprint

    with smbus.SMBusWrapper(1) as bus:
        print("Init GridEye88xx")
        ge = GridEye(i2c_bus=bus)
        print("Save Sensor Data As heatmap.png")
        image = ge.get_sensor_data("GRAYIMAGE")[0]
        image.save("heatmap.png", "PNG")
        while True:
            print("Thermistor Temperature is: %f°C" % ge.get_thermistor_temp())
            print("Current Sensor Data:")
            pprint(ge.get_sensor_data()[0])
            sleep(1)
