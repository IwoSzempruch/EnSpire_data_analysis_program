import pandas as pd
import re
import csv
import io

def parse_results_block(lines, start_index):
    """
    Począwszy od start_index (wiersz nagłówka wyników),
    zwraca (header, list_of_rows, new_index).
    Header – lista kolumn (np. ["01","02",…,"12"])
    list_of_rows – lista list; każdy wiersz zaczyna się literą (np. "A") i dalsze wartości.
    """
    header_line = lines[start_index].strip()
    header = next(csv.reader(io.StringIO(header_line), delimiter=',')) 
    header = [h.strip() for h in header if h.strip() != ""]
    
    results = []
    i = start_index + 1
    while i < len(lines) and lines[i].strip() != "":
        row_line = lines[i].strip()
        if ',' not in row_line:
            break
        row = next(csv.reader(io.StringIO(row_line), delimiter=',')) 
        row = [x.strip() for x in row if x.strip() != ""]
        if row:
            results.append(row)
        i += 1
    return header, results, i

def import_enspire_file(file_path):
    """
    Wczytuje plik wyeksportowany z EnSpire przy użyciu encoding="latin1".
    Szuka sekcji "Plate information" (aby pobrać m.in. wartość Kinetics),
    a następnie sekcji "Results for Meas A" i (opcjonalnie) "Results for Meas B".
    
    Dla każdej sekcji wyników przyjmuje, że linia zaraz po niej to nagłówek (z numerami kolumn),
    a kolejne 8 linii zawierają dane dla wierszy A–H.
    
    Funkcja zwraca słownik:
         {"MeasA": DataFrame, "MeasB": DataFrame}
    DataFrame’y mają kolumny: "Measurement", "Kinetics", "Row", "Column", "Well" oraz "Value".
    """
    with open(file_path, "r", encoding="latin1") as f:
        lines = f.readlines()
        
    data_measA = []
    data_measB = []
    current_kinetics = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Plate information"):
            # Pomijamy nagłówki i pobieramy dane z trzeciej linii
            i += 1
            if i < len(lines):
                _ = lines[i].strip()  # linia nagłówka, ignorujemy
            i += 1
            if i < len(lines):
                plate_info_line = lines[i].strip()
                plate_data = next(csv.reader(io.StringIO(plate_info_line), delimiter=',')) 
                if len(plate_data) >= 12:
                    current_kinetics = plate_data[11].strip()
            i += 1
            continue
        if line.startswith("Results for Meas A"):
            i += 1
            if i >= len(lines):
                break
            header, result_rows, i = parse_results_block(lines, i)
            for row in result_rows:
                if len(row) < 1:
                    continue
                row_letter = row[0]
                for j, col in enumerate(header):
                    value = row[j+1] if j+1 < len(row) else ""
                    if value == "":
                        continue
                    well = f"{row_letter}{col}"
                    try:
                        numeric_val = float(value)
                    except ValueError:
                        numeric_val = float("nan")
                    data_measA.append({
                        "Measurement": "Meas A",
                        "Kinetics": current_kinetics,
                        "Row": row_letter,
                        "Column": col,
                        "Well": well,
                        "Value": numeric_val
                    })
            continue
        if line.startswith("Results for Meas B"):
            i += 1
            if i >= len(lines):
                break
            header, result_rows, i = parse_results_block(lines, i)
            for row in result_rows:
                if len(row) < 1:
                    continue
                row_letter = row[0]
                for j, col in enumerate(header):
                    value = row[j+1] if j+1 < len(row) else ""
                    if value == "":
                        continue
                    well = f"{row_letter}{col}"
                    try:
                        numeric_val = float(value)
                    except ValueError:
                        numeric_val = float("nan")
                    data_measB.append({
                        "Measurement": "Meas B",
                        "Kinetics": current_kinetics,
                        "Row": row_letter,
                        "Column": col,
                        "Well": well,
                        "Value": numeric_val
                    })
            continue
        i += 1

    df_measA = pd.DataFrame(data_measA) if data_measA else pd.DataFrame(columns=["Measurement", "Kinetics", "Row", "Column", "Well", "Value"])
    df_measB = pd.DataFrame(data_measB) if data_measB else pd.DataFrame(columns=["Measurement", "Kinetics", "Row", "Column", "Well", "Value"])
    return {"MeasA": df_measA, "MeasB": df_measB}

# Przykładowe użycie:
if __name__ == "__main__":
    # Podaj ścieżkę do pliku EnSpire
    file_path = "ścieżka/do/pliku.txt"
    result = import_enspire_file(file_path)
    print("Dane Meas A:")
    print(result["MeasA"])
    print("Dane Meas B:")
    print(result["MeasB"])
