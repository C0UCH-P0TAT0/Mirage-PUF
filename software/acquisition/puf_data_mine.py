import serial
import time
import os
import csv
from datetime import datetime

PORT = 'COM7'
BAUD_RATE = 115200
TOTAL_CHALLENGES = 25000
READS_PER_CHALLENGE = 10

# Bitstream 3 Golden Dials
CALIBRATED_PDL_A = 2
CALIBRATED_PDL_B = 3

def generate_locked_challenge():
    raw_chal = os.urandom(16)
    chal_int = int.from_bytes(raw_chal, 'big')
    mask = ~( (0xFF << 120) | (0xFF << 56) )
    upper_injection = (CALIBRATED_PDL_B << 124) | (CALIBRATED_PDL_A << 120)
    lower_injection = (CALIBRATED_PDL_B << 60)  | (CALIBRATED_PDL_A << 56)
    chal_int = (chal_int & mask) | upper_injection | lower_injection
    return chal_int.to_bytes(16, 'big'), hex(chal_int)

def query_puf(ser, challenge_bytes):
    ser.reset_input_buffer()
    ser.write(challenge_bytes)
    ser.flush()
    resp = ser.read(8)
    time.sleep(0.01)
    if len(resp) == 8:
        return bin(int.from_bytes(resp, 'big'))[2:].zfill(64)
    return "TIMEOUT"

def mine_data():
    out_dir = "C:\\Users\\a\\Desktop\\Mirage_PUF\\data\\raw"
    os.makedirs(out_dir, exist_ok=True)
    filepath = f"{out_dir}/Mirage_RAW_1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        print(f"[!] Port Error: {e}")
        return

    print(f"[*] Mining {TOTAL_CHALLENGES} raw challenges...")
    with open(filepath, mode='w', newline='') as f:
        writer = csv.writer(f)
        # Dynamic headers based on read count
        headers = ["Challenge_Hex"] + [f"Read_{i+1}" for i in range(READS_PER_CHALLENGE)]
        writer.writerow(headers)
        
        for i in range(TOTAL_CHALLENGES):
            chal_bytes, chal_hex = generate_locked_challenge()
            reads = [query_puf(ser, chal_bytes) for _ in range(READS_PER_CHALLENGE)]
            
            writer.writerow([chal_hex] + reads)
            f.flush()
            
            if (i + 1) % 500 == 0:
                print(f" -> Progress: {i + 1} / {TOTAL_CHALLENGES}")
                
    ser.close()
    print(f"[✔] Raw silicon data safely vaulted in: {filepath}")

if __name__ == '__main__':
    mine_data()