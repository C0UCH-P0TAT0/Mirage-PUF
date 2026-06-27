import csv
from itertools import combinations

CSV_FILE = "../data/A2_RAW_20260415_142534.csv" # Update this!
BCH_THRESHOLD = 3 # Max allowable bit flips for BCH(64, 3)

def calc_stability():
    total_challenges = 0
    stable_count = 0
    poisoned_count = 0
    
    print(f"[*] Profiling Worst-Case Stability (BCH Threshold = {BCH_THRESHOLD})...")
    with open(CSV_FILE, 'r') as f:
        reader = csv.reader(f)
        next(reader) # Skip header
        
        for row in reader:
            reads = [r for r in row[1:] if r != "TIMEOUT"]
            if len(reads) < 2:
                continue
                
            max_flips = 0
            for r1, r2 in combinations(reads, 2):
                flips = bin(int(r1, 2) ^ int(r2, 2)).count('1')
                if flips > max_flips:
                    max_flips = flips
                    
            if max_flips <= BCH_THRESHOLD:
                stable_count += 1
            else:
                poisoned_count += 1
                
            total_challenges += 1

    stability_pct = (stable_count / total_challenges) * 100

    print("=======================================")
    print("        A2-PUF STABILITY REPORT")
    print("=======================================")
    print(f"Total Evaluated:  {total_challenges}")
    print(f"BCH-Stable Keys:  {stable_count} ({stability_pct:.2f}%)")
    print(f"Poisoned Keys:    {poisoned_count}")
    print("=======================================")

if __name__ == '__main__':
    calc_stability()