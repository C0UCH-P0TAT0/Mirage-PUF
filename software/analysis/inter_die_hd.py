import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
OLD_CSV = r"C:\Users\a\Desktop\Mirage_PUF\data\raw\Mirage_RAW_4_20261013_113605.csv"
NEW_CSV = r"C:\Users\a\Desktop\Mirage_PUF\data\raw\Mirage_RAW_14.csv"

OLD_CHALLENGE_COL = "Challenge_Hex" 
NEW_CHALLENGE_COL = "Challenge_Hex"

OLD_READ_COLS = [f"Read_{i}" for i in range(1, 11)] 
NEW_READ_COLS = ["Read_1_Bin", "Read_2_Bin", "Read_3_Bin"]

# Define "Ideal" range (45-55% of 64 bits)
IDEAL_HD_MIN = 29 
IDEAL_HD_MAX = 35

# ==========================================
# MAJORITY VOTER FUNCTION
# ==========================================
def majority_vote(reads_list):
    valid_reads = [str(r).strip() for r in reads_list if pd.notna(r)]
    valid_reads = [r for r in valid_reads if len(r) == 64 and all(c in '01' for c in r)]
    
    if not valid_reads:
        return None
        
    n_reads = len(valid_reads)
    stable_resp = []
    
    for bit_idx in range(64):
        ones_count = sum(1 for r in valid_reads if r[bit_idx] == '1')
        if ones_count > (n_reads / 2):
            stable_resp.append('1')
        else:
            stable_resp.append('0')
            
    return "".join(stable_resp)

# ==========================================
# MAIN PIPELINE
# ==========================================
def main():
    print("[*] Loading datasets...")
    try:
        df_old = pd.read_csv(OLD_CSV)
        df_new = pd.read_csv(NEW_CSV)
    except Exception as e:
        print(f"[-] Error loading files: {e}")
        return

    initial_old_count = len(df_old)
    initial_new_count = len(df_new)

    # --- 1. SANITIZE CHALLENGES ---
    df_old['Challenge_Master'] = df_old[OLD_CHALLENGE_COL].astype(str).str.strip().str.lower().str.replace('0x', '')
    df_new['Challenge_Master'] = df_new[NEW_CHALLENGE_COL].astype(str).str.strip().str.lower().str.replace('0x', '')

    # --- 2. EXTRACT GOLDEN RESPONSES ---
    df_old['Golden_Old'] = df_old[OLD_READ_COLS].apply(lambda row: majority_vote(row.tolist()), axis=1)
    df_new['Golden_New'] = df_new[NEW_READ_COLS].apply(lambda row: majority_vote(row.tolist()), axis=1)

    df_old_clean = df_old.dropna(subset=['Golden_Old'])
    df_new_clean = df_new.dropna(subset=['Golden_New'])
    
    discarded_old_quality = initial_old_count - len(df_old_clean)
    discarded_new_quality = initial_new_count - len(df_new_clean)

    # --- 3. CROSS-REFERENCE MATCHES ---
    merged = pd.merge(df_old_clean[['Challenge_Master', 'Golden_Old']], 
                      df_new_clean[['Challenge_Master', 'Golden_New']], 
                      on='Challenge_Master', 
                      how='inner')

    total_matches = len(merged)
    if total_matches == 0:
        print("[-] FATAL: Zero overlapping challenges.")
        return

    # --- 4. CALCULATE INTER-DIE HD ---
    merged['HD_bits'] = merged.apply(
        lambda x: bin(int(x['Golden_Old'], 2) ^ int(x['Golden_New'], 2)).count('1'), 
        axis=1
    )

    mean_hd_bits = merged['HD_bits'].mean()
    mean_hd_pct = (mean_hd_bits / 64.0) * 100

    # --- 5. FIND IDEAL CHALLENGES (Close to 50%) ---
    ideal_df = merged[(merged['HD_bits'] >= IDEAL_HD_MIN) & (merged['HD_bits'] <= IDEAL_HD_MAX)]
    num_ideal = len(ideal_df)
    pct_ideal = (num_ideal / total_matches) * 100

    # --- 6. FIND TOP 10 HIGHEST HD CHALLENGES ---
    top_10 = merged.sort_values(by='HD_bits', ascending=False).head(10)

    # --- FINAL REPORT ---
    print("\n=======================================")
    print("        DATA INTEGRITY REPORT")
    print("=======================================")
    print(f"Initial Rows (Old/New):      {initial_old_count} / {initial_new_count}")
    print(f"Discarded (Noise/Format):    {discarded_old_quality} (Old) / {discarded_new_quality} (New)")
    print(f"Final Valid CRP Matches:     {total_matches}")
    print("---------------------------------------")
    print("        INTER-DIE HD RESULTS")
    print("---------------------------------------")
    print(f"Mean Inter-HD:               {mean_hd_bits:.4f} / 64 bits")
    print(f"Mean Inter-HD (%):           {mean_hd_pct:.4f}%")
    print(f"Ideal CRPs (45-55% HD):      {num_ideal} ({pct_ideal:.2f}%)")
    
    print("\n---------------------------------------")
    print("    TOP 10 HIGHEST HD CHALLENGES")
    print("---------------------------------------")
    print(f"{'Rank':<5} {'HD Bits':<10} {'HD %':<10} {'Challenge Hex'}")
    for i, (idx, row) in enumerate(top_10.iterrows(), 1):
        hd_p = (row['HD_bits'] / 64.0) * 100
        print(f"{i:<5} {row['HD_bits']:<10} {hd_p:<10.2f}% {row['Challenge_Master']}")
    print("=======================================")

    if 45.0 <= mean_hd_pct <= 55.0:
        print("[W] VERDICT: BOARDS ARE DIFFERENT (~50% HD).")
    elif mean_hd_pct < 10.0:
        print("[L] VERDICT: BOARDS ARE THE SAME (Fatal routing bias).")
    else:
        print(f"[!] VERDICT: BORDERLINE (Bias present: {mean_hd_pct:.2f}%).")

if __name__ == "__main__":
    main()