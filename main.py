#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plik: main.py

Integracja procesu:
  1. Uruchamia GUI (launch_gui z gui.py), które generuje pliki long (m.in. long_measA.csv oraz long_measB.csv)
     oraz zapisuje interwał pomiaru w konfiguracji.
  2. Scala oba pliki long w jeden plik (long_merged.csv).
  3. Uruchamia analizę blank correction (blank_correct_file z data_blank_corrected.py)
     – wynik zapisuje się jako blank_corrected_summary.csv.
  4. Uruchamia analizę danych (analyze_long_file z data_analysis.py) na pliku blank_corrected_summary.csv.
  5. Uruchamia analizę ratio (calculate_ratio z data_ratio.py) dla pliku long_merged.csv.
  6. Umożliwia uruchomienie interfejsu interaktywnego wyboru wykresów, który pobiera dane (np. zagregowane
     statystyki) i generuje jeden wykres kompozytowy z wieloma liniami (średnia ± std) dla wybranych próbek.
"""

import os
import pandas as pd
from gui import launch_gui
from data_blank_corrected import blank_correct_file
from data_analysis import analyze_long_file
from data_ratio import calculate_ratio
from interactive_plot_selector import launch_plot_selector  # Upewnij się, że plik ma tę nazwę

def main():
    print("Uruchamiam GUI – przygotuj dane...")
    config = launch_gui()  # Zwraca config zawierający 'long_file' (ścieżka do long_measA.csv) oraz 'measurement_interval'
    
    long_file_A = config.get('long_file', "")
    if not long_file_A or not os.path.isfile(long_file_A):
        print("Brak wygenerowanego pliku long_measA.csv. Koniec programu.")
        return

    measurement_interval = config.get('measurement_interval', 20)
    output_dir = os.path.dirname(long_file_A)
    long_file_B = os.path.join(output_dir, "long_measB.csv")
    
    # Scalanie danych z obu plików long (jeśli long_measB.csv istnieje)
    if os.path.isfile(long_file_B):
        print("Scalam pliki long_measA.csv oraz long_measB.csv...")
        df_A = pd.read_csv(long_file_A, encoding="latin1")
        df_B = pd.read_csv(long_file_B, encoding="latin1")
        merged_df = pd.concat([df_A, df_B], ignore_index=True)
        merged_file = os.path.join(output_dir, "long_merged.csv")
        merged_df.to_csv(merged_file, index=False)
        print("Scalony plik zapisano jako:", merged_file)
    else:
        print("Plik long_measB.csv nie został znaleziony – używam tylko long_measA.csv.")
        merged_file = long_file_A

    # Blank correction – przetwarzamy scalony plik
    print("Uruchamiam analizę blank correction...")
    blank_correct_file(merged_file, measurement_interval)
    blank_analysis_folder = os.path.join(output_dir, "blank_corrected_analysis")
    blank_summary_file = os.path.join(blank_analysis_folder, "blank_corrected_summary.csv")
    if not os.path.isfile(blank_summary_file):
        print("Plik blank_corrected_summary.csv nie został wygenerowany. Koniec programu.")
        return

    # Analiza danych – wykresy raw_diagram_in_time (użycie danych skorygowanych lub oryginalnych)
    print("Uruchamiam analizę danych (skorygowane)...")
    analyze_long_file(blank_summary_file, measurement_interval)
    
    # Analiza ratio – korzystamy z pliku long_merged.csv
    print("Uruchamiam analizę ratio...")
    calculate_ratio(merged_file, measurement_interval)
    
    # Uruchomienie interfejsu do wyboru wykresów
    odp = input("Czy wyświetlić interaktywny wybór wykresów? (t/n): ").strip().lower()
    while odp == "t":
        try:
            # Funkcja launch_plot_selector przyjmuje jako argument folder bazowy (najczęściej [nazwa_pliku]_results)
            launch_plot_selector(output_dir)
        except Exception as e:
            print("Błąd przy uruchamianiu interfejsu wyboru wykresów:", e)
            break
        odp = input("Czy chcesz uruchomić interfejs ponownie? (t/n): ").strip().lower()

if __name__ == "__main__":
    main()
