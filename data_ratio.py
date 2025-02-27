#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plik: data_ratio.py

Cel:
  Dla danych z pliku long_merged.csv (surowe dane przed blank correction)
  dla każdej kombinacji (Sample, Kinetics, Time_min) oblicza stosunek:
    Ratio = (Value dla pomiaru LICZNIKOWEGO) / (Value dla pomiaru MIANOWNIKOWEGO)
  Na podstawie ilorazów obliczana jest średnia (Ratio_mean), odchylenie standardowe (Ratio_std) i liczba par.
Wynik zapisuje się do pliku ratio_summary.csv.
Folder wynikowy nazywa się dynamicznie – na podstawie pierwszej definicji stosunku z listy.
Nie generujemy wykresów.
"""

import os
import pandas as pd
import numpy as np

def calculate_ratio(long_merged_file, measurement_interval=20, ratio_mapping=None):
    print("[DEBUG] Wczytywanie danych z:", long_merged_file)
    df = pd.read_csv(long_merged_file, encoding="latin1")
    if 'Value' not in df.columns:
        raise KeyError("Brak kolumny 'Value'. Użyj pliku long_merged.csv.")
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    df['Kinetics'] = pd.to_numeric(df['Kinetics'], errors='coerce')
    if 'Time_min' not in df.columns:
        df['Time_min'] = (df['Kinetics'] - 1) * measurement_interval
    if ratio_mapping is None or len(ratio_mapping)==0:
        ratio_mapping = [{"numerator": "Meas A", "denominator": "Meas B"}]
    # Używamy pierwszej definicji ratio do nazwy folderu
    mapping0 = ratio_mapping[0]
    df_num = df[df['Measurement'] == mapping0["numerator"]].copy()
    df_den = df[df['Measurement'] == mapping0["denominator"]].copy()
    if df_num.empty or df_den.empty:
        raise ValueError("Brak danych dla wybranego stosunku.")
    df_num = df_num[['Sample','Kinetics','Time_min','Value']].rename(columns={'Value': 'Num'})
    df_den = df_den[['Sample','Kinetics','Time_min','Value']].rename(columns={'Value': 'Den'})
    merged = pd.merge(df_num, df_den, on=['Sample','Kinetics','Time_min'], how='inner')
    ratio_records = []
    grouped = merged.groupby(['Sample','Kinetics','Time_min'])
    for (sample, kinetics, time_min), group in grouped:
        ratios = [row['Num']/row['Den'] for _, row in group.iterrows() if row['Den'] != 0]
        if not ratios:
            continue
        ratio_mean = np.mean(ratios)
        ratio_std = np.std(ratios, ddof=1) if len(ratios)>1 else 0
        count = len(ratios)
        ratio_records.append({
            "Sample": sample,
            "Kinetics": kinetics,
            "Time_min": time_min,
            "Ratio_mean": ratio_mean,
            "Ratio_std": ratio_std,
            "Count": count
        })
    if ratio_records:
        ratio_df = pd.DataFrame(ratio_records)
    else:
        print("[DEBUG] Brak danych do obliczenia ratio.")
        return None
    mapping_str = f"{mapping0.get('numerator')}_to_{mapping0.get('denominator')}_ratio"
    input_dir = os.path.dirname(long_merged_file)
    ratio_folder = os.path.join(input_dir, mapping_str)
    os.makedirs(ratio_folder, exist_ok=True)
    ratio_summary_path = os.path.join(ratio_folder, "ratio_summary.csv")
    ratio_df.to_csv(ratio_summary_path, index=False)
    print("[DEBUG] Ratio summary zapisano do:", ratio_summary_path)
    return ratio_df

if __name__ == "__main__":
    long_merged_file = input("Podaj ścieżkę do pliku long_merged.csv: ").strip()
    interval_input = input("Podaj interwał pomiaru (domyślnie 20): ").strip()
    try:
        measurement_interval = float(interval_input) if interval_input else 20
    except:
        measurement_interval = 20
    # Przykładowy ratio mapping – można ustawić z configu
    mapping = [{"numerator": "Meas A", "denominator": "Meas B"}]
    calculate_ratio(long_merged_file, measurement_interval, mapping)
