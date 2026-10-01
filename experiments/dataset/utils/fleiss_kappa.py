import numpy as np
import pandas as pd
from statsmodels.stats.inter_rater import fleiss_kappa
from scipy.stats import norm

df_aktivitaeten = pd.read_excel('annotations.xlsx', sheet_name='annotations')

rater_cols = ['annotator_1', 'annotator_2', 'annotator_3']
rater_data = df_aktivitaeten[rater_cols].dropna()

# Nur 0/1 erlaubt, sonst würden Aktivitäten stillschweigend falsch gezählt
invalid = ~rater_data.isin([0, 1]).all(axis=1)
if invalid.any():
    raise ValueError(f"Ungültige Werte (nicht 0/1) in Zeilen: {list(rater_data.index[invalid] + 2)}")
print(f"Aktivitäten mit drei Labels: {len(rater_data)} von {len(df_aktivitaeten)}")
print(f"Aktivitäten mit Uneinigkeit: {(rater_data.nunique(axis=1) > 1).sum()}")

formatted_data = {
    f"Category {cat}": [(rater_data.iloc[i] == cat).sum() for i in range(len(rater_data))] 
    for cat in [0, 1]
}
formatted_df = pd.DataFrame(formatted_data)

# Kappa berechnen
kappa = fleiss_kappa(formatted_df.values)

# Signifikanz und Konfidenzintervall
n = len(rater_cols)        
N = len(rater_data)        
k = 2                      

# Berechne p (Erwartete Übereinstimmung)
category_counts = formatted_df.sum(axis=0)
p = np.sum((category_counts / (N * n))**2)

variance = (2 / (N * n * (n - 1))) * ( (p - (2 * n - 3) * p**2 + 2 * (n - 2) * np.sum((category_counts / (N * n))**3)) / (1 - p)**2 )

if variance > 0:
    se = np.sqrt(variance)
    z_value = kappa / se
    p_value = 2 * (1 - norm.cdf(np.abs(z_value)))
    
    z_critical = norm.ppf(0.975) # 95% Konfidenz
    margin_of_error = z_critical * se
    conf_interval = (kappa - margin_of_error, kappa + margin_of_error)

    print("### STATISTIK ERGEBNISSE ###")
    print(f"Fleiss' Kappa:           {kappa:.4f}")
    print(f"P-Wert:                  {p_value:.4e}")
    print(f"95% Konfidenzintervall:  ({conf_interval[0]:.4f}, {conf_interval[1]:.4f})")
else:
    print(f"Fleiss' Kappa: {kappa:.4f}")
    print("Varianz ist 0 oder negativ (perfekte Übereinstimmung oder zu kleine Datenbasis).")