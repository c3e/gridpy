# gridpy
A python(3) module for GridEYE (AMG88) infrared array sensors.

Because you don't want to deal with i2c, bits and bytes for 256 pixel.

usage (on a raspberypi) with python3:
    import smbus2 as smbus
    from gridpy import GridEye
    
    with smbus.SMBusWrapper(1) as bus:
        eye = GridEye8(i2c_address=0x68, i2c_bus=bus)
        sensor_data = eye.get_sensor_data()[0]

or just run python3 gridpy.py
        
#features
- get/set for all sensor functions(except interrupts and moving average)
- sensor data as array with temps or (remapped) 8x8 pixel image (using Pillow) including current min/max values.
    
