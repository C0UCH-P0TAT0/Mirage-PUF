import csv
from collections import Counter
from itertools import combinations

CSV_FILE = r"C:\Users\a\Desktop\Mirage_PUF\data\raw\Mirage_RAW_1_20261013_113605.csv" # Update this!

def calc_inter_hd():
    golden_keys = []
    
    print("[*] Extracting offline Majority Votes...")
    with open(CSV_FILE, 'r') as f:
        reader = csv.reader(f)
        next(reader) # Skip header
        
        for row in reader:
            reads = [r for r in row[1:] if r != "TIMEOUT"]
            if not reads:
                continue
            # Majority vote
            golden_resp = Counter(reads).most_common(1)[0][0]
            golden_keys.append(int(golden_resp, 2))

    print(f"[*] Calculating Inter-HD across {len(golden_keys)} keys (This takes a few seconds)...")
    
    total_hd = 0
    pairs = 0
    
    for r1, r2 in combinations(golden_keys, 2):
        total_hd += (r1 ^ r2).bit_count() # C-optimized speed
        pairs += 1

    inter_hd_pct = ((total_hd / pairs) / 64.0) * 100.0

    print("=======================================")
    print("        A2-PUF INTER-HD REPORT")
    print("=======================================")
    print(f"Unique Combinations: {pairs:,}")
    print(f"Spatial Uniqueness:  {inter_hd_pct:.4f}%")
    print("=======================================")

if __name__ == '__main__':
    calc_inter_hd()