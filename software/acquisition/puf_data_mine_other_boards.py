import pandas as pd
import serial
import time
import csv

# ==========================================
# CONFIGURATION
# ==========================================
OLD_CSV = r"C:\Users\a\Desktop\Mirage_PUF\data\raw\Mirage_RAW_4_20261013_113605.csv"  # The 25k dataset you already have
NEW_CSV = r"C:\Users\a\Desktop\Mirage_PUF\data\raw\Mirage_RAW_14.csv"  # Where the new data will be saved
CHALLENGE_COL = "Challenge_Hex"     # Column name in your old CSV

COM_PORT = "COM6"                   # Change to your Nexys A7 COM port
BAUD_RATE = 115200

def main():
    print(f"[*] Extracting seeds from {OLD_CSV}...")
    try:
        df_old = pd.read_csv(OLD_CSV)
        # Drop duplicates, keep order
        seeds = df_old[CHALLENGE_COL].dropna().unique().tolist()
        print(f"[+] Successfully extracted {len(seeds)} unique 128-bit seeds.")
    except Exception as e:
        print(f"[-] Error reading CSV: {e}")
        return

    print(f"[*] Opening {COM_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=2)
        time.sleep(2) # Allow connection to stabilize
    except Exception as e:
        print(f"[-] Serial Error: {e}")
        return

    print("[*] Beginning targeted extraction (3 reads per seed)...")
    
    with open(NEW_CSV, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Challenge_Hex", "Read_1_Bin", "Read_2_Bin", "Read_3_Bin"])
        
        for idx, seed_hex in enumerate(seeds):
            # Clean the hex string and convert to exactly 16 raw bytes
            clean_hex = seed_hex.strip().replace("0x", "")
            if len(clean_hex) != 32:
                print(f"[!] Warning: Seed at index {idx} is not 32 hex chars. Skipping.")
                continue
                
            seed_bytes = bytes.fromhex(clean_hex)
            reads = []
            
            for _ in range(3):
                # Send the 16 raw bytes directly (NO newline character)
                ser.write(seed_bytes)
                
                # The FPGA transmits an 8-byte (64-bit) response
                resp_bytes = ser.read(8)
                
                if len(resp_bytes) == 8:
                    # Convert 8 raw bytes back into a 64-bit binary string (e.g., '1010...')
                    # zfill ensures leading zeros aren't dropped
                    bin_str = bin(int.from_bytes(resp_bytes, byteorder='big'))[2:].zfill(64)
                    reads.append(bin_str)
                else:
                    print(f"[-] UART Timeout on seed {idx}. Got {len(resp_bytes)}/8 bytes.")
                    reads.append("0" * 64) # Fallback to prevent CSV corruption
                
            writer.writerow([seed_hex, reads[0], reads[1], reads[2]])
            
            if (idx + 1) % 1000 == 0:
                print(f"    -> Progress: {idx + 1} / {len(seeds)} seeds extracted.")

    ser.close()
    print(f"[+] Done! Data saved to {NEW_CSV}.")

if __name__ == "__main__":
    main()