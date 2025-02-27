#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plik: data_analysis.py

Analizuje plik long (lub blank_corrected_summary.csv) – grupuje dane według Measurement, Sample, Kinetics i Time_min,
obliczając statystyki (mean, std, count) dla wybranej kolumny (Corrected, jeśli istnieje, w przeciwnym razie Value).
Wynik zapisuje do pliku summary CSV. W tej wersji wykresy nie są generowane.
"""

import os
import pandas as pd

def analyze_long_file(input_file, measurement_interval):
    input_dir = os.path.dirname(input_file)
    output_folder = os.path.join(input_dir, "analysis")
    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    print(f"Folder wyjściowy: {output_folder}")
    try:
        df = pd.read_csv(input_file, encoding="latin1")
        print("Wczytano dane:", df.shape)
    except Exception as e:
        print(f"Błąd wczytania {input_file}: {e}")
        return
    df['Kinetics'] = pd.to_numeric(df['Kinetics'], errors="coerce")
    if "Time_min" not in df.columns:
        df['Time_min'] = (df['Kinetics'] - 1) * measurement_interval
    value_column = "Corrected" if "Corrected" in df.columns else "Value"
    summary = df.groupby(['Measurement','Sample','Kinetics','Time_min'])[value_column] \
                .agg(['mean','std','count']).reset_index()
    summary_path = os.path.join(output_folder, f"{base_name}_summary.csv")
    summary.to_csv(summary_path, index=False)
    print(f"Podsumowanie zapisano do: {summary_path}")

if __name__ == "__main__":
    file_path = input("Podaj ścieżkę do pliku (CSV): ").strip()
    try:
        measurement_interval = float(input("Podaj interwał pomiaru (min, domyślnie 20): ").strip() or 20)
    except:
        measurement_interval = 20
    analyze_long_file(file_path, measurement_interval)
