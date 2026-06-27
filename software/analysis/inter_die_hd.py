import pandas as pd

# ==========================================
# CONFIGURATION
# ==========================================
OLD_CSV = "../data/A2_RAW_20260415_142534.csv"
NEW_CSV = "../data/new_board_3.csv"

# Exact challenge column headers
OLD_CHALLENGE_COL = "Challenge_Hex" 
NEW_CHALLENGE_COL = "Challenge_Hex"

# Exact read column headers based on your files
OLD_READ_COLS = [f"Read_{i}" for i in range(1, 11)] 
NEW_READ_COLS = ["Read_1_Bin", "Read_2_Bin", "Read_3_Bin"]

# ==========================================
# MAJORITY VOTER FUNCTION
# ==========================================
def majority_vote(reads_list):
    """Takes a list of 64-bit strings, scrubs noise, returns golden response."""
    # Filter out empty or malformed strings
    valid_reads = [str(r).strip() for r in reads_list if pd.notna(r)]
    valid_reads = [r for r in valid_reads if len(r) == 64 and all(c in '01' for c in r)]
    
    if not valid_reads:
        return None
        
    n_reads = len(valid_reads)
    stable_resp = []
    
    # Iterate through all 64 bit positions
    for bit_idx in range(64):
        ones_count = sum(1 for r in valid_reads if r[bit_idx] == '1')
        # If '1' appears more than half the time, the stable bit is 1
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

    print(f"[*] Found {len(df_old)} rows in Old CSV.")
    print(f"[*] Found {len(df_new)} rows in New CSV.")

    # --- 1. SANITIZE CHALLENGES ---
    df_old['Challenge_Master'] = df_old[OLD_CHALLENGE_COL].astype(str).str.strip().str.lower().str.replace('0x', '')
    df_new['Challenge_Master'] = df_new[NEW_CHALLENGE_COL].astype(str).str.strip().str.lower().str.replace('0x', '')

    # --- 2. EXTRACT GOLDEN RESPONSES (SCRUB NOISE) ---
    print("[*] Executing Temporal Majority Vote on Old Board (10 reads)...")
    df_old['Golden_Old'] = df_old[OLD_READ_COLS].apply(lambda row: majority_vote(row.tolist()), axis=1)
    
    print("[*] Executing Temporal Majority Vote on New Board (3 reads)...")
    df_new['Golden_New'] = df_new[NEW_READ_COLS].apply(lambda row: majority_vote(row.tolist()), axis=1)

    # Drop any rows where the majority vote failed (e.g., corrupted UART data)
    df_old = df_old.dropna(subset=['Golden_Old'])
    df_new = df_new.dropna(subset=['Golden_New'])

    # --- 3. CROSS-REFERENCE MATCES ---
    print("[*] Cross-referencing exact challenge matches...")
    # Using 'inner' drop drops anything that doesn't exist in BOTH files
    merged = pd.merge(df_old[['Challenge_Master', 'Golden_Old']], 
                      df_new[['Challenge_Master', 'Golden_New']], 
                      on='Challenge_Master', 
                      how='inner')

    total_matches = len(merged)
    print(f"[+] Successfully isolated {total_matches} EXACT overlapping challenges.")

    if total_matches == 0:
        print("[-] FATAL: Zero overlapping challenges. The LFSR seeds do not match.")
        return

    # --- 4. CALCULATE INTER-DIE HD ---
    print("[*] Calculating Inter-Die HD on the overlapping Golden set...")
    
    # XOR the Golden_Old and Golden_New binary strings and count the '1's
    merged['HD_bits'] = merged.apply(
        lambda x: bin(int(x['Golden_Old'], 2) ^ int(x['Golden_New'], 2)).count('1'), 
        axis=1
    )

    mean_hd_bits = merged['HD_bits'].mean()
    mean_hd_pct = (mean_hd_bits / 64.0) * 100

    print("\n=======================================")
    print("        INTER-DIE HD REPORT")
    print("=======================================")
    print(f"CRPs Compared:      {total_matches}")
    print(f"Mean Inter-HD:      {mean_hd_bits:.4f} / 64 bits")
    print(f"Mean Inter-HD (%):  {mean_hd_pct:.4f}%")
    print("=======================================")

    if 45.0 <= mean_hd_pct <= 55.0:
        print("[W] VERDICT: BOARDS ARE DIFFERENT (~50% HD). You struck gold. Update Table II immediately.")
    elif mean_hd_pct < 10.0:
        print("[L] VERDICT: BOARDS ARE THE SAME (or routing bias is fatal).")
    else:
        print(f"[!] VERDICT: BORDERLINE. You have a routing bias pulling it down to {mean_hd_pct:.2f}%.")

if __name__ == "__main__":
    main()