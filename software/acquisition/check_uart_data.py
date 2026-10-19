import serial
import os

PORT = 'COM7'
BAUD_RATE = 115200

ser = serial.Serial(PORT, BAUD_RATE, timeout=2)

for i in range(5):
    challenge = os.urandom(16)

    ser.reset_input_buffer()
    ser.write(challenge)
    ser.flush()

    response = ser.read(8)

    print("C:", challenge.hex().upper())
    print("R:", response.hex().upper())

ser.close()