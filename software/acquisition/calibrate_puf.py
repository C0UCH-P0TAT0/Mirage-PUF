import serial
import time
import os
import csv
from datetime import datetime

PORT = 'COM7'
BAUD_RATE = 115200

# Increased for statistical validity during calibration
NUM_BASE_CHALLENGES = 100 
READS_PER_CHALLENGE = 10

def generate_base_challenges(n):
    challenges = []
    for _ in range(n):
        rand_128 = int.from_bytes(os.urandom(16), 'big')
        mask = ~((0xFF << 120) | (0xFF << 56))
        challenges.append(rand_128 & mask)
    return challenges

def query_puf(ser, chal_bytes):
    ser.reset_input_buffer()
    ser.write(chal_bytes)
    ser.flush()
    resp = ser.read(8)
    time.sleep(0.005) # Optimized sleep
    if len(resp) == 8:
        return bin(int.from_bytes(resp, 'big'))[2:].zfill(64)
    return None

def get_hd(b1, b2):
    return bin(int(b1, 2) ^ int(b2, 2)).count('1')

def calibrate():
    print("[*] Connecting to A2-PUF for UNIFORMITY-FIRST Calibration...")
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=2)
    except Exception as e:
        print(f"[-] Port error: {e}")
        return

    base_challenges = generate_base_challenges(NUM_BASE_CHALLENGES)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"calibration_A2_{timestamp}.csv"

    results = []

    with open(log_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Delay_A", "Delay_B",
            "Mean_IntraHD", "Max_IntraHD",
            "Uniformity_Pct", "Timeouts",
            "Stable_Challenges"
        ])

        for delay_a in range(4):
            for delay_b in range(4):
                print(f"\n--- Sweeping Dials: A={delay_a} | B={delay_b} ---")

                all_intra_hds = []
                all_bits = []
                timeouts = 0
                stable_count = 0

                for base_chal in base_challenges:
                    upper = (delay_b << 124) | (delay_a << 120)
                    lower = (delay_b << 60)  | (delay_a << 56)
                    tuned = (base_chal | upper | lower).to_bytes(16, 'big')

                    reads = []
                    for _ in range(READS_PER_CHALLENGE):
                        r = query_puf(ser, tuned)
                        if r:
                            reads.append(r)
                            all_bits.extend([int(b) for b in r])
                        else:
                            timeouts += 1

                    if len(reads) >= 2:
                        max_hd = max(
                            get_hd(reads[i], reads[j])
                            for i in range(len(reads))
                            for j in range(i+1, len(reads))
                        )
                        mean_hd = sum(
                            get_hd(reads[i], reads[j])
                            for i in range(len(reads))
                            for j in range(i+1, len(reads))
                        ) / max(1, len(reads) * (len(reads)-1) / 2)

                        all_intra_hds.append(mean_hd)
                        if max_hd <= 3:
                            stable_count += 1

                mean_intra = sum(all_intra_hds) / len(all_intra_hds) if all_intra_hds else 999
                max_intra  = max(all_intra_hds) if all_intra_hds else 999
                uniformity = (sum(all_bits) / len(all_bits) * 100) if all_bits else 0

                print(f"  Uniformity:    {uniformity:.2f}%")
                print(f"  Mean IntraHD:  {mean_intra:.3f} bits")
                print(f"  Stable Chals:  {stable_count}/{NUM_BASE_CHALLENGES}")

                writer.writerow([
                    delay_a, delay_b,
                    round(mean_intra, 4), round(max_intra, 4),
                    round(uniformity, 2), timeouts,
                    stable_count
                ])
                results.append((delay_a, delay_b, mean_intra, stable_count, uniformity))

    ser.close()

    # THE FIX: Prioritize distance from 50% Uniformity FIRST. Then tiebreak with lowest noise.
    best = min(results, key=lambda x: (abs(x[4] - 50.0), x[2]))

    print("\n========================================================")
    print("            A2-PUF CALIBRATION COMPLETE")
    print("========================================================")
    print(f"{'A':>4} {'B':>4} {'Uniformity':>12} {'MeanHD':>8} {'StableChals':>12}")
    print("-" * 45)
    
    # Sorting the print output to match our new Uniformity-first reality
    for a, b, mhd, sc, uni in sorted(results, key=lambda x: abs(x[4] - 50.0)):
        marker = " <--- GOLDEN DIALS" if (a, b) == (best[0], best[1]) else ""
        print(f"{a:>4} {b:>4} {uni:>11.2f}% {mhd:>8.3f} {sc:>12}{marker}")
    print("========================================================")
    print(f"[✔] Best Physical Setting: A={best[0]}, B={best[1]}")
    print(f"    Uniformity: {best[4]:.2f}% | Mean Noise: {best[2]:.3f} bits")
    print(f"    Log saved to: {log_file}")
    print("========================================================")

if __name__ == "__main__":
    calibrate()