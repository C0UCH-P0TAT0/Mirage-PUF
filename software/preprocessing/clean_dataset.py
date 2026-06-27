import csv
from collections import Counter
from itertools import combinations

RAW_CSV = "../data/A2_RAW_20260415_142534.csv"
ML_CSV = "../data/A2_ML_DATASET_CLEAN.csv"
BCH_THRESHOLD = 3 

def forge_clean_ml_dataset():
    print("[*] Forging the CLEAN ML-Ready Tensor Dataset...")
    headers = [f"C_{i}" for i in range(128)] + [f"R_{i}" for i in range(64)]

    with open(RAW_CSV, 'r') as infile, open(ML_CSV, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        next(reader) 
        writer.writerow(headers)
        
        valid_rows = 0
        poisoned_dropped = 0
        
        for row in reader:
            chal_hex = row[0]
            reads = [r for r in row[1:] if r != "TIMEOUT"]
            
            if len(reads) < 2:
                continue
                
            # --- THE VITAL FIX: STABILITY GATEKEEPER ---
            max_flips = 0
            for r1, r2 in combinations(reads, 2):
                flips = bin(int(r1, 2) ^ int(r2, 2)).count('1')
                if flips > max_flips:
                    max_flips = flips
                    
            if max_flips > BCH_THRESHOLD:
                poisoned_dropped += 1
                continue # DROP THE METASTABLE NOISE!
            # -------------------------------------------

            # Now it's safe to take the majority vote
            golden_resp = Counter(reads).most_common(1)[0][0]
            
            chal_int = int(chal_hex, 16)
            chal_bin = bin(chal_int)[2:].zfill(128)
            
            chal_features = [int(b) for b in chal_bin]
            resp_labels = [int(b) for b in golden_resp]
            
            writer.writerow(chal_features + resp_labels)
            valid_rows += 1

    print("\n========================================================")
    print("             CLEAN ML DATASET SECURED")
    print("========================================================")
    print(f"[✔] Total Clean CRPs Forged: {valid_rows}")
    print(f"[!] Metastable Noise Dropped: {poisoned_dropped}")
    print("========================================================")

if __name__ == '__main__':
    forge_clean_ml_dataset()