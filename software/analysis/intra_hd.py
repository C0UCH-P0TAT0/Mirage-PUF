import csv
from itertools import combinations

CSV_FILE = "../data/A2_RAW_20260415_142534.csv" # Update this!

def calc_intra_hd():
    total_challenges = 0
    global_intra_hd_sum = 0
    
    print("[*] Calculating Intra-HD (Silicon Noise)...")
    with open(CSV_FILE, 'r') as f:
        reader = csv.reader(f)
        next(reader) # Skip header
        
        for row in reader:
            reads = [r for r in row[1:] if r != "TIMEOUT"]
            if len(reads) < 2:
                continue
                
            chal_hd_sum = 0
            pairs = 0
            for r1, r2 in combinations(reads, 2):
                chal_hd_sum += bin(int(r1, 2) ^ int(r2, 2)).count('1')
                pairs += 1
                
            global_intra_hd_sum += (chal_hd_sum / pairs)
            total_challenges += 1

    mean_intra_bits = global_intra_hd_sum / total_challenges
    mean_intra_pct = (mean_intra_bits / 64.0) * 100

    print("=======================================")
    print("        A2-PUF INTRA-HD REPORT")
    print("=======================================")
    print(f"Challenges Analyzed: {total_challenges}")
    print(f"Mean Noise (Bits):   {mean_intra_bits:.4f} / 64 bits")
    print(f"Mean Noise (Pct):    {mean_intra_pct:.4f}%")
    print("=======================================")

if __name__ == '__main__':
    calc_intra_hd()