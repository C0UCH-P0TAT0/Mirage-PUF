import serial
import csv
import time
import os

# =========================================================
# CONFIGURATION
# =========================================================
PORT = 'COM6'            # Update this to your actual COM port
BAUD_RATE = 115200       
TOTAL_READS = 1024       
TIMEOUT_SEC = 5          

# File path configuration
TARGET_DIR = os.path.join("data", "raw")
OUTPUT_FILE = os.path.join(TARGET_DIR, "ro_puf_log_2.csv")

def log_ro_puf():
    # Ensure the directory exists
    if not os.path.exists(TARGET_DIR):
        print(f"[*] Creating directory: {TARGET_DIR}")
        os.makedirs(TARGET_DIR)

    print(f"[*] Initializing {PORT} for {TOTAL_READS} samples...")
    
    try:
        # Open the serial port
        ser = serial.Serial(PORT, BAUD_RATE, timeout=TIMEOUT_SEC)
        
        # Prepare the CSV file in the data\raw directory
        with open(OUTPUT_FILE, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['Sample_ID', 'Timestamp', 'Fingerprint_Hex'])
            
            print(f"[*] Logging to {OUTPUT_FILE}...")
            print("-" * 45)

            for i in range(1, TOTAL_READS + 1):
                # 1. Trigger the FPGA by sending 16 dummy bytes
                ser.reset_input_buffer()
                trigger = bytes([0x00] * 16)
                ser.write(trigger)

                # 2. Read the 8-byte (64-bit) fingerprint
                raw_data = ser.read(8)

                if len(raw_data) == 8:
                    # Reverse bytes to handle LSB-first transmission order
                    fingerprint = raw_data[::-1].hex().upper()
                    
                    # 3. Log the data
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow([i, timestamp, f"0x{fingerprint}"])
                    
                    # Print progress every 64 samples
                    if i % 64 == 0:
                        print(f"[*] Processed {i}/{TOTAL_READS} samples...")
                else:
                    print(f"[!] Warning: Sample {i} timed out. Data skipped.")
            
            print("-" * 45)
            print(f"[SUCCESS] Logging complete.")
            print(f"[SUCCESS] File saved at: {os.path.abspath(OUTPUT_FILE)}")

        ser.close()

    except serial.SerialException as e:
        print(f"[!] Serial Port Error: {e}")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    log_ro_puf()