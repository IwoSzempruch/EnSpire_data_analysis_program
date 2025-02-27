#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plik: data_blank_corrected.py

Dla pliku long (CSV) oblicza skorygowane wartości (Corrected = Sample_avg - Blank_avg)
dla każdej grupy (Measurement, Sample, Kinetics, Time_min) i zapisuje wynik do blank_corrected_summary.csv.
Nie generuje wykresów.
"""

import os
import pandas as pd

def blank_correct_file(input_file, measurement_interval):
    input_dir = os.path.dirname(input_file)
    analysis_folder = os.path.join(input_dir, "blank_corrected_analysis")
    os.makedirs(analysis_folder, exist_ok=True)
    df = pd.read_csv(input_file, encoding="latin1")
    df['Kinetics'] = pd.to_numeric(df['Kinetics'], errors="coerce")
    df['Value'] = pd.to_numeric(df['Value'], errors="coerce")
    df['Time_min'] = (df['Kinetics'] - 1) * measurement_interval
    corrected_list = []
    for meas in df['Measurement'].unique():
        df_meas = df[df['Measurement'] == meas]
        blank_avg = df_meas[df_meas['Sample'] == "BLANK"].groupby('Kinetics')['Value']\
                      .mean().reset_index().rename(columns={'Value': 'Blank_avg'})
        sample_stats = df_meas[df_meas['Sample'] != "BLANK"].groupby(['Sample','Kinetics','Time_min'])['Value']\
                           .agg(['mean','std','count']).reset_index().rename(
                           columns={'mean':'Sample_avg', 'std':'Sample_std', 'count':'n'})
        merged = pd.merge(sample_stats, blank_avg, on='Kinetics', how='left')
        merged['Blank_avg'] = merged['Blank_avg'].fillna(0)
        merged['Corrected'] = merged['Sample_avg'] - merged['Blank_avg']
        merged['Measurement'] = meas
        corrected_list.append(merged)
    if corrected_list:
        result = pd.concat(corrected_list, ignore_index=True)
    else:
        result = pd.DataFrame()
    summary_path = os.path.join(analysis_folder, "blank_corrected_summary.csv")
    result.to_csv(summary_path, index=False)
    print("Blank-corrected summary zapisano do:", summary_path)
    return result

if __name__ == "__main__":
    input_file = input("Podaj ścieżkę do pliku long (CSV): ").strip()
    try:
        measurement_interval = float(input("Podaj interwał pomiaru (min, domyślnie 20): ").strip() or 20)
    except:
        measurement_interval = 20
    blank_correct_file(input_file, measurement_interval)
