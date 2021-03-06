# GRIDpy
A python(3) module for GridEYE (AMG88) infrared array sensors.

Because you don't want to deal with i2c, bits and bytes for 256 pixel.
#Requirements
- Python3 with Pillow and smbus(2)
- 1+ AMG88 sensor

# Usage 
(on a raspberypi) with python3:

    import smbus2 as smbus
    from gridpy import GridEye
    
    with smbus.SMBusWrapper(1) as bus:
        eye = GridEye(i2c_address=0x68, i2c_bus=bus)
        sensor_data = eye.get_sensor_data()[0]

or just run

    python3 gridpy.py
        
# Features
- get/set for all sensor functions(except get moving average)
- sensor data as array with temps or (remapped) 8x8 pixel image (using Pillow) including current min/max values.
- useful functions while handling the AMG88 or other ICs like int2twoscomplement(), split_in_2bytes()
