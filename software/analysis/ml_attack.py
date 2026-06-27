import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
import lightgbm as lgb
import time
import os

# Suppress warnings for clean output
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# CONFIGURATION
# ==========================================
CSV_PATH = '../data/A2_ML_DATASET.csv'  # Updated to point to the clean ML dataset
TRAINING_SIZES = [500, 1000, 2000, 5000, 10000, 20000]
NUM_MUTATIONS = 16

# ==========================================
# FEATURE ENGINEERING (A2-PUF Specific)
# ==========================================
def bits_to_phi(bits):
    """Converts raw entropy bits into the Cumulative Parity Vector (Phi)"""
    x = 1 - 2 * bits
    phi = np.ones(len(bits) + 1)
    phi[:-1] = np.cumprod(x[::-1])[::-1]
    return phi

def build_feature_vector(bits, strategy='concatenate'):
    # Extract Pure Entropy (Skip the 16 locked dials)
    # Upper Track: 8-63 | Lower Track: 72-127
    base_entropy = np.concatenate((bits[8:64], bits[72:128])) 

    if strategy == 'concatenate':
        # Omni-State Phi: 16 Mutated Phi Vectors Concatenated (1808 features)
        phis = []
        for m in range(NUM_MUTATIONS):
            mutated = base_entropy.copy()
            # Mutate only the Upper Track bits (indices 0 to 55)
            mutated[54] ^= (m >> 3) & 1
            mutated[36] ^= (m >> 2) & 1
            mutated[18] ^= (m >> 1) & 1
            mutated[0]  ^= m & 1
            phis.append(bits_to_phi(mutated))
        return np.concatenate(phis)

    elif strategy == 'raw':
        # Pure 112-bit entropy (Tree models usually prefer raw bits over Phi)
        return base_entropy.astype(float)

    elif strategy == 'raw_concat':
        # Raw 112-bit entropy + all 15 mutated variations (1792 features)
        mutations = []
        for m in range(NUM_MUTATIONS):
            mutated = base_entropy.copy().astype(float)
            mutated[54] = float(int(mutated[54]) ^ ((m >> 3) & 1))
            mutated[36] = float(int(mutated[36]) ^ ((m >> 2) & 1))
            mutated[18] = float(int(mutated[18]) ^ ((m >> 1) & 1))
            mutated[0]  = float(int(mutated[0]) ^ (m & 1))
            mutations.append(mutated)
        return np.concatenate(mutations)

# ==========================================
# DATA LOADING (Direct from Pre-Flattened CSV)
# ==========================================
def load_data(csv_path, strategy):
    print(f"[*] Extracting Features: [{strategy.upper()}]...")
    df = pd.read_csv(csv_path)
    
    # Grab the 128 challenge bits
    C_cols = [f"C_{i}" for i in range(128)]
    X_raw = df[C_cols].values
    
    # We attack a SINGLE response bit (R_0). 
    # If a hacker can model one bit, the PUF is cryptographically compromised.
    y = df['R_0'].values 

    X = []
    for bits in X_raw:
        X.append(build_feature_vector(bits, strategy))

    X, y = np.array(X), np.array(y)
    ones_pct = np.mean(y) * 100
    print(f"  -> Valid CRPs: {len(X)} | Label balance (R_0): {ones_pct:.1f}% ones")
    return X, y

# ==========================================
# ATTACK RUNNER
# ==========================================
def run_attack(X, y, attack_name, clf_fn, training_sizes, scale=True):
    print(f"\n[--- {attack_name} ---]")
    print(f"{'Training CRPs':>15} | {'Test Accuracy':>14} | {'Time':>8} | {'Verdict':>15}")
    print("-" * 60)

    if scale:
        scaler = StandardScaler()
        X_proc = scaler.fit_transform(X)
    else:
        X_proc = X  # Tree models don't need scaling

    results = []
    for n in training_sizes:
        if n + 500 > len(X_proc):
            print(f"  [!] Not enough CRPs for n={n}, skipping.")
            continue

        X_train, y_train = X_proc[:n], y[:n]
        X_test,  y_test  = X_proc[n:n+500], y[n:n+500]

        t0 = time.time()
        clf = clf_fn()
        clf.fit(X_train, y_train)
        acc = accuracy_score(y_test, clf.predict(X_test)) * 100
        elapsed = time.time() - t0

        verdict = (
            "SECURE"      if acc < 55.0 else
            "MARGINAL"    if acc < 65.0 else
            "VULNERABLE"  if acc < 80.0 else
            "COMPROMISED"
        )

        print(f"  {n:>13,} | {acc:>13.2f}% | {elapsed:>6.2f}s | {verdict:>15}")
        results.append((n, acc, elapsed, verdict))

    return results

# ==========================================
# MAIN
# ==========================================
def run_full_attack():
    print("========================================================")
    print("        A2-PUF COMPREHENSIVE ML ATTACK SUITE")
    print("========================================================")

    # Dictionary: Name -> (Strategy, Scale_Data, Model_Lambda)
    attackers = {
        "LOGISTIC REGRESSION (Omni-State)": (
            'concatenate', True,
            lambda: LogisticRegression(max_iter=1000, solver='lbfgs', n_jobs=-1)
        ),
        "SUPPORT VECTOR MACHINE (Omni-State)": (
            'concatenate', True,
            lambda: SVC(kernel='rbf', C=10, gamma='scale')
        ),
        "SHALLOW MLP (Omni-State)": (
            'concatenate', True,
            lambda: MLPClassifier(hidden_layer_sizes=(128, 64), activation='relu', max_iter=300, early_stopping=True)
        ),
        "DEEP MLP (Omni-State)": (
            'concatenate', True,
            lambda: MLPClassifier(hidden_layer_sizes=(256, 128, 64, 32), activation='relu', max_iter=300, early_stopping=True)
        ),
        "RANDOM FOREST (Raw Bits)": (
            'raw', False,
            lambda: RandomForestClassifier(n_estimators=150, max_depth=15, n_jobs=-1)
        ),
        "XGBOOST (Raw Bits)": (
            'raw', False,
            lambda: XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1, n_jobs=-1, eval_metric='logloss')
        ),
        "LIGHTGBM (Raw Omni-State)": (
            'raw_concat', False,
            lambda: lgb.LGBMClassifier(n_estimators=300, max_depth=10, learning_rate=0.05, n_jobs=-1, verbose=-1)
        ),
    }

    all_results = {}
    
    # Cache data to prevent redundant processing
    data_cache = {}
    for strategy in ['concatenate', 'raw', 'raw_concat']:
        data_cache[strategy] = load_data(CSV_PATH, strategy)

    for attack_name, (strategy, scale, clf_fn) in attackers.items():
        X, y = data_cache[strategy]
        results = run_attack(X, y, attack_name, clf_fn, TRAINING_SIZES, scale=scale)
        all_results[attack_name] = results

    # Summary Output
    print("\n========================================================")
    print("                    ATTACK SUMMARY")
    print("========================================================")
    print(f"{'Attack':>38} | {'Max Acc':>8} | {'Verdict':>12}")
    print("-" * 65)

    overall_secure = True
    for attack_name, results in all_results.items():
        if not results:
            continue
        max_acc = max(r[1] for r in results)
        if max_acc >= 65.0:
            overall_secure = False
            
        verdict = (
            "SECURE"     if max_acc < 55.0 else
            "MARGINAL"   if max_acc < 65.0 else
            "VULNERABLE" if max_acc < 80.0 else
            "COMPROMISED"
        )
        print(f"  {attack_name:>36} | {max_acc:>7.2f}% | {verdict:>12}")

    print("========================================================")
    if overall_secure:
        print("[✔] A2-PUF RESISTS ALL TESTED ATTACK STRATEGIES")
        print("    Architecture holds against linear, tree, boosting,")
        print("    SVMs, and neural network attacks up to 20,000 CRPs.")
    else:
        print("[!] VULNERABILITY DETECTED - Check the summary table.")
    print("========================================================")

if __name__ == "__main__":
    run_full_attack()