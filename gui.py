#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plik: gui.py

Interfejs graficzny do przygotowania danych (przypisań dołków) oraz generowania plików long.
Zakładki:
  1. "Próby i Przypisz" – wczytanie pliku (domyślnie interwał=0), przypisywanie dołków,
     informacja o konieczności przypisania BLANK (domyślnie pierwsza próba) z przyciskiem do zignorowania,
     skróty klawiszowe (Shift+A/E/Z/N) widoczne przy odpowiednich przyciskach oraz przycisk "Dalej =>".
  2. "Mapping i Stosunki" – przypisywanie opisów do wykrytych pomiarów (np. "Fluorescencja, OD, Luminescencja"),
     dodawanie definicji stosunków (ratio) oraz przycisk "Potwierdź" umieszczony na dole tej zakładki.
     
Wszystkie ustawienia są zapisywane do pliku config.txt (w folderze wynikowym), z którego może korzystać interactive_plot_selector.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import re, os, csv, io, hashlib, colorsys

def get_color_from_sample(name):
    """
    Generuje kolor na podstawie całej nazwy.
    Dzięki sumie kodów znaków – nazwy takie jak "M1" i "P1" będą znacznie różne.
    """
    total_ord = sum(ord(ch) for ch in name)
    hue = ((total_ord * 37) % 360) / 360.0
    sat = 0.8
    val = 0.9
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))

def parse_platemap(file_path):
    assignments = {}
    try:
        with open(file_path, "r", encoding="latin1") as f:
            lines = f.readlines()
        print("[DEBUG] Wczytano", len(lines), "linii z pliku platemap.")
        start_idx = None
        for i, line in enumerate(lines):
            if "Platemap:" in line:
                start_idx = i
                break
        if start_idx is None:
            print("[DEBUG] Sekcja 'Platemap:' nie została znaleziona.")
            return assignments
        header_idx = None
        for i in range(start_idx, len(lines)):
            if re.match(r"^,(\s*\S+\s*,)+", lines[i]):
                header_idx = i
                break
        if header_idx is None:
            print("[DEBUG] Nie znaleziono linii nagłówkowej platemapu.")
            return assignments
        row_labels = ['A','B','C','D','E','F','G','H']
        for i in range(header_idx+1, header_idx+1+len(row_labels)):
            if i >= len(lines):
                break
            parts = lines[i].strip().split(',')
            if not parts:
                continue
            row = parts[0].strip()
            if row not in row_labels:
                continue
            for j, cell in enumerate(parts[1:], start=1):
                sample = cell.strip()
                if sample:
                    well = f"{row}{j}"
                    assignments[well] = sample
        print("[DEBUG] Parsowanie platemapu zakończone. Znaleziono:", assignments)
        return assignments
    except Exception as e:
        print("Błąd parsowania platemapu:", e)
        return assignments

def parse_enspire_file(file_path, output_folder, sample_mapping=None):
    try:
        with open(file_path, "r", encoding="latin1") as f:
            lines = f.readlines()
        print("[DEBUG] Wczytano", len(lines), "linii z pliku EnSpire.")
    except Exception as e:
        print("Błąd wczytania pliku EnSpire:", e)
        return None
    data_measA = []
    data_measB = []
    current_kinetics = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Plate information"):
            print("[DEBUG] Znaleziono 'Plate information' na linii", i)
            i += 1
            if i < len(lines):
                _ = lines[i].strip()
            i += 1
            if i < len(lines):
                plate_info_line = lines[i].strip()
                plate_data = next(csv.reader(io.StringIO(plate_info_line), delimiter=',')) 
                if len(plate_data) >= 12:
                    current_kinetics = plate_data[11].strip()
                    print("[DEBUG] Ustalono Kinetics =", current_kinetics)
            i += 1
            continue
        if line.startswith("Results for Meas A"):
            print("[DEBUG] Znaleziono 'Results for Meas A' na linii", i)
            i += 1
            if i >= len(lines):
                break
            header_line = lines[i].strip()
            header = next(csv.reader(io.StringIO(header_line), delimiter=',')) 
            header = [h.strip() for h in header if h.strip() != ""]
            print("[DEBUG] Nagłówek Results for Meas A:", header)
            i += 1
            while i < len(lines) and lines[i].strip() != "":
                row_line = lines[i].strip()
                if ',' not in row_line:
                    break
                row = next(csv.reader(io.StringIO(row_line), delimiter=',')) 
                row = [x.strip() for x in row if x.strip() != ""]
                if row:
                    row_letter = row[0]
                    for j, col in enumerate(header):
                        value = row[j+1] if j+1 < len(row) else ""
                        if value == "":
                            continue
                        try:
                            col_num = int(col)
                        except:
                            col_num = col
                        well = f"{row_letter}{col_num}"
                        data_measA.append({
                            "Measurement": "Meas A",
                            "Kinetics": current_kinetics,
                            "Row": row_letter,
                            "Column": col,
                            "Well": well,
                            "Value": value
                        })
                i += 1
            continue
        if line.startswith("Results for Meas B"):
            print("[DEBUG] Znaleziono 'Results for Meas B' na linii", i)
            i += 1
            if i >= len(lines):
                break
            header_line = lines[i].strip()
            header = next(csv.reader(io.StringIO(header_line), delimiter=',')) 
            header = [h.strip() for h in header if h.strip() != ""]
            print("[DEBUG] Nagłówek Results for Meas B:", header)
            i += 1
            while i < len(lines) and lines[i].strip() != "":
                row_line = lines[i].strip()
                if ',' not in row_line:
                    break
                row = next(csv.reader(io.StringIO(row_line), delimiter=',')) 
                row = [x.strip() for x in row if x.strip() != ""]
                if row:
                    row_letter = row[0]
                    for j, col in enumerate(header):
                        value = row[j+1] if j+1 < len(row) else ""
                        if value == "":
                            continue
                        try:
                            col_num = int(col)
                        except:
                            col_num = col
                        well = f"{row_letter}{col_num}"
                        data_measB.append({
                            "Measurement": "Meas B",
                            "Kinetics": current_kinetics,
                            "Row": row_letter,
                            "Column": col,
                            "Well": well,
                            "Value": value
                        })
                i += 1
            continue
        i += 1

    import pandas as pd
    df_measA = pd.DataFrame(data_measA)
    df_measB = pd.DataFrame(data_measB)
    print("[DEBUG] Liczba rekordów Meas A:", len(df_measA))
    print("[DEBUG] Liczba rekordów Meas B:", len(df_measB))
    df_measA["Value"] = pd.to_numeric(df_measA["Value"], errors="coerce")
    df_measB["Value"] = pd.to_numeric(df_measB["Value"], errors="coerce")
    if sample_mapping is None:
        sample_mapping = parse_platemap(file_path)
    print("[DEBUG] Używana mapa próbek:", sample_mapping)
    for df in [df_measA, df_measB]:
        df["Sample"] = df["Well"].map(sample_mapping)
        df.dropna(subset=["Sample"], inplace=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    os.makedirs(output_folder, exist_ok=True)
    fluor_path = os.path.join(output_folder, "long_measA.csv")
    od_path = os.path.join(output_folder, "long_measB.csv")
    df_measA.to_csv(fluor_path, index=False)
    df_measB.to_csv(od_path, index=False)
    print("[DEBUG] Pliki long zapisano w folderze:", output_folder)
    return fluor_path

class SampleEditDialog(tk.Toplevel):
    def __init__(self, master, old_name):
        super().__init__(master)
        self.title("Edytuj próbę")
        self.old_name = old_name
        self.new_name = None
        tk.Label(self, text=f"Podaj nową nazwę dla próby '{old_name}':").pack(padx=10, pady=5)
        self.entry = tk.Entry(self, width=30)
        self.entry.pack(padx=10, pady=5)
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        ok_btn = tk.Button(btn_frame, text="OK", command=self.on_ok)
        ok_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Anuluj", command=self.destroy).pack(side=tk.LEFT, padx=5)
        self.entry.focus_set()
        self.bind("<Return>", lambda event: self.on_ok())
        self.grab_set()
        self.wait_window()
    
    def on_ok(self):
        new = self.entry.get().strip()
        if not new:
            messagebox.showerror("Błąd", "Nazwa nie może być pusta.")
            return
        self.new_name = new
        self.destroy()

class SingleWindowGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Konfiguracja eksperymentu")
        self.master.geometry("1000x700")
        self.master.minsize(900, 600)
        style = ttk.Style()
        style.configure("TNotebook.Tab", padding=[10, 10], font=('Helvetica', 11, 'bold'))

        self.config = {}
        self.file_path_var = tk.StringVar()
        self.interval_var = tk.DoubleVar(value=0.0)  # Domyślnie 0, użytkownik musi wpisać

        self.notebook = ttk.Notebook(self.master, style="TNotebook")
        self.tab_samples = ttk.Frame(self.notebook)
        self.tab_mapping = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_samples, text="Próby i Przypisz")
        self.notebook.add(self.tab_mapping, text="Mapping i Stosunki")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.ratio_rows = []
        self.measurement_entries = {}

        self.create_samples_tab()
        self.create_mapping_tab()

        self.master.bind_all("<Shift-A>", lambda event: self.add_sample() or self.master.focus_set())
        self.master.bind_all("<Shift-E>", lambda event: self.edit_sample() or self.master.focus_set())
        self.master.bind_all("<Shift-Z>", lambda event: self.select_all() or self.master.focus_set())
        self.master.bind_all("<Shift-N>", lambda event: self.next_sample_assignment() or self.master.focus_set())

    def create_samples_tab(self):
        self.top_frame = tk.Frame(self.tab_samples)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Label(self.top_frame, text="Plik z danymi (EnSpire):").grid(row=0, column=0, sticky="w")
        tk.Entry(self.top_frame, textvariable=self.file_path_var, width=50).grid(row=0, column=1, padx=5)
        tk.Button(self.top_frame, text="Przeglądaj...", command=self.browse_file).grid(row=0, column=2, padx=5)

        tk.Label(self.top_frame, text="Interwał pomiarów (min):").grid(row=1, column=0, sticky="w")
        self.interval_entry = tk.Entry(self.top_frame, textvariable=self.interval_var, width=10, bg="white")
        self.interval_entry.grid(row=1, column=1, sticky="w", padx=5)
        tk.Button(self.top_frame, text="Zatwierdź interwał", command=self.confirm_interval).grid(row=1, column=2, padx=5)

        tk.Button(self.top_frame, text="Załaduj dane", command=self.load_data).grid(row=2, column=1, pady=5)

        tk.Button(self.top_frame, text="Dalej =>", command=lambda: self.notebook.select(self.tab_mapping)).grid(row=2, column=2, padx=5)

        self.well_assignments = {f"{r}{c}": None for r in ['A','B','C','D','E','F','G','H'] for c in range(1,13)}
        self.prepopulated = {}
        self.sample_names = ["BLANK"]  # BLANK jako pierwsza próba
        self.options = ["BLANK"]
        self.dragging = False
        self.drag_assignment = None
        self.well_buttons = {}

        self.grid_container = tk.Frame(self.tab_samples)
        self.grid_container.pack(side=tk.TOP, padx=10, pady=5)

        tk.Label(self.grid_container, text="", width=4, height=2).grid(row=0, column=0)
        self.col_buttons_frame = tk.Frame(self.grid_container)
        self.col_buttons_frame.grid(row=0, column=1)
        for col in range(1, 13):
            btn = tk.Button(self.col_buttons_frame, text=str(col), width=4, height=2,
                            command=lambda c=str(col): self.assign_column(c))
            btn.grid(row=0, column=col-1, padx=1, pady=1)
        self.row_buttons_frame = tk.Frame(self.grid_container)
        self.row_buttons_frame.grid(row=1, column=0, sticky="ns")
        for r in ['A','B','C','D','E','F','G','H']:
            btn = tk.Button(self.row_buttons_frame, text=r, width=4, height=2,
                            command=lambda rr=r: self.assign_row(rr))
            btn.grid(row=ord(r)-65, column=0, padx=1, pady=1)
        self.cells_frame = tk.Frame(self.grid_container)
        self.cells_frame.grid(row=1, column=1)

        bottom_frame = tk.Frame(self.tab_samples, bd=2, relief=tk.GROOVE)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        left_bottom = tk.Frame(bottom_frame)
        left_bottom.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Label(left_bottom, text="Próby:").pack()
        self.sample_listbox = tk.Listbox(left_bottom, selectmode=tk.MULTIPLE, width=20, height=8)
        self.sample_listbox.pack(padx=5, pady=5)
        self.sample_listbox.bind("<<ListboxSelect>>", self.on_sample_select)
        self.sample_listbox.bind("<Return>", self.check_or_add_sample)
        btn_samples = tk.Frame(left_bottom)
        btn_samples.pack(pady=5)
        tk.Button(btn_samples, text="Dodaj próbę (Shift+A)", command=self.add_sample).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_samples, text="Edytuj próbę (Shift+E)", command=self.edit_sample).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_samples, text="Usuń próbę", command=self.remove_samples).pack(side=tk.LEFT, padx=2)
        tk.Button(left_bottom, text="Zaznacz wszystko (Shift+Z)", command=self.select_all).pack(pady=5)
        right_bottom = tk.Frame(bottom_frame)
        right_bottom.pack(side=tk.RIGHT, padx=5, pady=5)
        tk.Label(right_bottom, text="Przypisz:").pack(side=tk.LEFT)
        self.current_assignment = tk.StringVar(value="BLANK")
        self.mode_menu = ttk.Combobox(right_bottom, textvariable=self.current_assignment, state="readonly")
        self.mode_menu.pack(side=tk.LEFT, padx=5)
        self.mode_menu.bind("<KeyPress-Tab>", self.on_tab_assignment)

    def confirm_interval(self):
        try:
            val = float(self.interval_entry.get())
            if val <= 0:
                raise ValueError
            self.interval_var.set(val)
            self.interval_entry.configure(bg="white")
        except:
            self.interval_entry.configure(bg="red")
            messagebox.showerror("Błąd", "Interwał pomiarów musi być dodatnią liczbą!")

    def ignore_blank(self):
        # Usuwa "BLANK" z listy prób (jeśli użytkownik nie chce go przypisywać)
        if "BLANK" in self.sample_names:
            self.sample_names.remove("BLANK")
            self.refresh_sample_list()
            self.draw_cells()

    def create_mapping_tab(self):
        self.mapping_frame = tk.LabelFrame(self.tab_mapping, text="Przypisz opisy dla wykrytych pomiarów (np. Fluorescencja, OD, Luminescencja)")
        self.mapping_frame.pack(fill=tk.X, padx=10, pady=5)
        self.ratio_frame = tk.LabelFrame(self.tab_mapping, text="Definicje stosunków (po korekcie BLANK)")
        self.ratio_frame.pack(fill=tk.X, padx=10, pady=5)
        self.btn_add_ratio = tk.Button(self.ratio_frame, text="Dodaj stosunek", command=self.add_ratio_row)
        self.btn_add_ratio.pack(side=tk.BOTTOM, pady=5)
        confirm_frame = tk.Frame(self.tab_mapping)
        confirm_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        tk.Button(confirm_frame, text="Potwierdź", command=self.confirm).pack(side=tk.RIGHT, padx=5)

    def add_ratio_row(self):
        frame = tk.Frame(self.ratio_frame)
        frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(frame, text="Licznik:").pack(side=tk.LEFT, padx=2)
        num_var = tk.StringVar()
        num_menu = ttk.Combobox(frame, textvariable=num_var, state="readonly")
        tk.Label(frame, text="/").pack(side=tk.LEFT, padx=2)
        tk.Label(frame, text="Mianownik:").pack(side=tk.LEFT, padx=2)
        den_var = tk.StringVar()
        den_menu = ttk.Combobox(frame, textvariable=den_var, state="readonly")
        num_menu.pack(side=tk.LEFT, padx=2)
        den_menu.pack(side=tk.LEFT, padx=2)
        btn_delete = tk.Button(frame, text="Usuń", command=lambda: self.delete_ratio_row(frame))
        btn_delete.pack(side=tk.LEFT, padx=5)
        measurements = list(self.config.get('measurement_mapping', {}).keys())
        if not measurements:
            measurements = []
        num_menu['values'] = measurements
        den_menu['values'] = measurements
        if len(measurements) > 0:
            num_var.set(measurements[0])
        if len(measurements) > 1:
            den_var.set(measurements[1])
        self.ratio_rows.append({"numerator": num_var, "denominator": den_var, "frame": frame})

    def delete_ratio_row(self, frame):
        for i, row in enumerate(self.ratio_rows):
            if row["frame"] == frame:
                self.ratio_rows.pop(i)
                break
        frame.destroy()

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Wybierz plik EnSpire",
            filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.load_data()

    def load_data(self):
        file_path = self.file_path_var.get().strip()
        if not file_path:
            messagebox.showerror("Błąd", "Nie wybrano pliku.")
            return
        try:
            val = float(self.interval_entry.get())
            if val <= 0:
                raise ValueError
            self.interval_entry.configure(bg="white")
        except:
            self.interval_entry.configure(bg="red")
            return
        if "BLANK" not in self.sample_names:
            self.sample_names.insert(0, "BLANK")
        if not hasattr(self, 'blank_info'):
            self.blank_info = tk.Label(self.top_frame, text="Przypisz BLANK do dołków (kliknij)", fg="red", font=("Helvetica", 10, "bold"))
            self.blank_info.grid(row=3, column=0, columnspan=3, pady=5)
            tk.Button(self.top_frame, text="Zignoruj dodanie BLANK", command=self.ignore_blank).grid(row=3, column=2, padx=5)


        self.prepopulated = parse_platemap(file_path)
        print("[DEBUG] Prepopulated mapa:", self.prepopulated)
        for well in self.well_assignments.keys():
            self.well_assignments[well] = self.prepopulated.get(well, None)
        self.sample_names = sorted(list({v for v in self.prepopulated.values() if v}))
        if "BLANK" not in self.sample_names:
            self.sample_names.insert(0, "BLANK")
        print("[DEBUG] Lista prób:", self.sample_names)
        self.options = self.sample_names + ["BLANK"]
        self.mode_menu['values'] = self.options
        if self.options:
            self.current_assignment.set(self.options[0])
        self.refresh_sample_list()
        self.draw_cells()

        with open(file_path, "r", encoding="latin1") as f:
            content = f.read()
        import re
        measurements = re.findall(r"Results for (Meas [A-Z])", content)
        measurements = sorted(set(measurements))
        if measurements:
            for widget in self.mapping_frame.winfo_children():
                widget.destroy()
            tk.Label(self.mapping_frame, text="Przypisz opisy dla wykrytych pomiarów (np. Fluorescencja, OD, Luminescencja):").pack(anchor="w", padx=5, pady=5)
            self.config['measurement_mapping'] = {}
            for meas in measurements:
                rowf = tk.Frame(self.mapping_frame)
                rowf.pack(fill=tk.X, padx=5, pady=2)
                tk.Label(rowf, text=f"{meas}:").pack(side=tk.LEFT, padx=5)
                ent = tk.Entry(rowf)
                ent.insert(0, meas)
                ent.pack(side=tk.LEFT, padx=5)
                self.config['measurement_mapping'][meas] = ent
            if not self.ratio_rows and len(measurements) >= 2:
                self.add_ratio_row()

    def refresh_sample_list(self):
        self.sample_listbox.delete(0, tk.END)
        for sample in sorted(self.sample_names):
            self.sample_listbox.insert(tk.END, sample)
        self.sample_listbox.insert(tk.END, "BLANK")
        self.options = sorted(self.sample_names) + ["BLANK"]
        self.mode_menu['values'] = self.options
        current = self.current_assignment.get()
        all_items = self.sample_listbox.get(0, tk.END)
        if current in all_items:
            idx = all_items.index(current)
            self.sample_listbox.selection_clear(0, tk.END)
            self.sample_listbox.selection_set(idx)

    def draw_cells(self):
        for widget in self.cells_frame.winfo_children():
            widget.destroy()
        rows = ['A','B','C','D','E','F','G','H']
        cols = [str(i) for i in range(1, 13)]
        self.well_buttons = {}
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                well = f"{r}{c}"
                assign = self.well_assignments.get(well)
                color = "white"
                if assign == "BLANK":
                    color = "salmon"
                elif assign:
                    color = get_color_from_sample(assign)
                btn = tk.Button(self.cells_frame, text=well, width=4, height=2, bg=color)
                btn.grid(row=i, column=j, padx=1, pady=1)
                btn.bind("<ButtonPress-1>", lambda event, w=well: self.on_button_press(event, w))
                btn.bind("<Enter>", lambda event, w=well: self.on_button_enter(event, w))
                btn.bind("<ButtonRelease-1>", lambda event, w=well: self.on_button_release(event, w))
                btn.bind("<Button-3>", lambda event, w=well: self.popup_menu(event, w))
                self.well_buttons[well] = btn
        self.highlight_wells()

    def on_button_press(self, event, well):
        self.dragging = True
        current_sample = self.well_assignments.get(well)
        if current_sample and current_sample != "BLANK":
            try:
                idx = self.sample_names.index(current_sample)
                self.sample_listbox.selection_clear(0, tk.END)
                self.sample_listbox.selection_set(idx)
            except ValueError:
                pass
        self.drag_assignment = self.current_assignment.get()
        self.set_assignment(well, self.drag_assignment)

    def on_button_enter(self, event, well):
        if self.dragging:
            self.set_assignment(well, self.drag_assignment)

    def on_button_release(self, event, well):
        self.dragging = False

    def on_tab_assignment(self, event):
        return self.next_sample_assignment()


    def popup_menu(self, event, well):
        menu = tk.Menu(self.master, tearoff=0)
        # "Usuń przypisanie" na samej górze
        menu.add_command(label="Usuń przypisanie", command=lambda w=well: self.set_assignment(w, None))
        for opt in self.options:
            menu.add_command(label=opt, command=lambda o=opt, w=well: self.set_assignment(w, o))
        menu.post(event.x_root, event.y_root)

    def set_assignment(self, well, assignment):
        self.well_assignments[well] = assignment
        if well not in self.well_buttons:
            return
        if assignment == "BLANK":
            color = "salmon"
        elif assignment:
            color = get_color_from_sample(assignment)
        else:
            color = "white"
        self.well_buttons[well].configure(bg=color)
        self.highlight_wells()

    def on_sample_select(self, event):
        selected_indices = self.sample_listbox.curselection()
        if len(selected_indices) == 1:
            selected = self.sample_listbox.get(selected_indices[0])
            self.current_assignment.set(selected)
        self.highlight_wells()

    def check_or_add_sample(self, event):
        if not self.sample_listbox.curselection():
            self.add_sample()

    def highlight_wells(self):
        selected_indices = self.sample_listbox.curselection()
        selected_samples = [self.sample_listbox.get(i) for i in selected_indices]
        for well, btn in self.well_buttons.items():
            assign = self.well_assignments.get(well)
            if assign in selected_samples:
                btn.configure(relief="solid", bd=3)
            else:
                btn.configure(relief="raised", bd=1)

    def add_sample(self):
        new_sample = simpledialog.askstring("Dodaj próbę", "Podaj nazwę nowej próby:")
        if new_sample:
            new_sample = new_sample.strip()
            if new_sample in self.sample_names:
                messagebox.showerror("Błąd", "Próba o takiej nazwie już istnieje.")
                return
            self.sample_names.append(new_sample)
            self.sample_names = sorted(self.sample_names)
            self.refresh_sample_list()
            self.draw_cells()
            self.current_assignment.set(new_sample)

    def edit_sample(self):
        try:
            idx = self.sample_listbox.curselection()[0]
        except IndexError:
            messagebox.showerror("Błąd", "Wybierz próbę do edycji.")
            return
        old_name = self.sample_listbox.get(idx)
        dialog = SampleEditDialog(self.master, old_name)
        new_name = dialog.new_name
        if new_name and new_name != old_name:
            self.sample_names[idx] = new_name
            for well, assign in self.well_assignments.items():
                if assign == old_name:
                    self.well_assignments[well] = new_name
                    if well in self.well_buttons:
                        self.well_buttons[well].configure(bg=get_color_from_sample(new_name))
            self.refresh_sample_list()
            self.draw_cells()

    def remove_samples(self):
        indices = self.sample_listbox.curselection()
        if not indices:
            messagebox.showerror("Błąd", "Wybierz próbę/próby do usunięcia.")
            return
        samples_to_remove = [self.sample_listbox.get(i) for i in indices]
        if messagebox.askyesno("Potwierdzenie", f"Usunąć prób(y): {', '.join(samples_to_remove)}?"):
            for sample in samples_to_remove:
                if sample in self.sample_names:
                    self.sample_names.remove(sample)
                for well, assign in self.well_assignments.items():
                    if assign == sample:
                        self.well_assignments[well] = None
                        if well in self.well_buttons:
                            self.well_buttons[well].configure(bg="white")
            self.refresh_sample_list()
            self.draw_cells()

    def next_sample_assignment(self):
        options = [s for s in self.sample_names if s]
        if not options:
            return "break"
        current = self.current_assignment.get()
        if current not in options:
            self.current_assignment.set(options[0])
        else:
            idx = options.index(current)
            new_idx = (idx + 1) % len(options)
            self.current_assignment.set(options[new_idx])
        all_items = self.sample_listbox.get(0, tk.END)
        if self.current_assignment.get() in all_items:
            idx = all_items.index(self.current_assignment.get())
            self.sample_listbox.selection_clear(0, tk.END)
            self.sample_listbox.selection_set(idx)
        return "break"

    def select_all(self):
        self.sample_listbox.select_set(0, tk.END)
        self.highlight_wells()

    def confirm(self):
        # Sprawdzamy poprawność interwału
        try:
            interval = float(self.interval_entry.get())
            if interval <= 0:
                raise ValueError
        except:
            messagebox.showerror("Błąd", "Interwał pomiarów musi być dodatnią liczbą!")
            return

        sample_assignments = {sample: [] for sample in self.sample_names}
        blank_wells = []
        for well, assignment in self.well_assignments.items():
            if assignment:
                if assignment == "BLANK":
                    blank_wells.append(well)
                else:
                    sample_assignments[assignment].append(well)
        self.config['file_path'] = self.file_path_var.get().strip()
        self.config['measurement_interval'] = interval
        self.config['sample_assignments'] = sample_assignments
        self.config['blank_wells'] = blank_wells

        if 'measurement_mapping' not in self.config:
            self.config['measurement_mapping'] = {}
        else:
            final_mapping = {}
            for meas, entry in self.config['measurement_mapping'].items():
                final_mapping[meas] = entry.get().strip()
            self.config['measurement_mapping'] = final_mapping

        ratio_mappings = []
        for row in self.ratio_rows:
            ratio_mappings.append({
                "numerator": row["numerator"].get(),
                "denominator": row["denominator"].get()
            })
        self.config['ratio_mapping'] = ratio_mappings

        input_file = self.config['file_path']
        if not input_file:
            messagebox.showerror("Błąd", "Nie wybrano pliku z danymi.")
            return
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_folder = f"{base_name}_results"
        os.makedirs(output_folder, exist_ok=True)

        assignment_file = os.path.join(output_folder, "well-to-plate-assignment.csv")
        with open(assignment_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Well", "Assignment"])
            for well in sorted(self.well_assignments.keys()):
                writer.writerow([well, self.well_assignments[well] if self.well_assignments[well] else ""])

        parse_enspire_file(self.config['file_path'], output_folder, sample_mapping=self.well_assignments)
        long_measA_path = os.path.join(output_folder, "long_measA.csv")
        self.config['long_file'] = long_measA_path

        config_file = os.path.join(output_folder, "config.txt")
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(f"file_path = {self.config['file_path']}\n")
                f.write(f"measurement_interval = {self.config['measurement_interval']}\n")
                f.write(f"long_file = {self.config['long_file']}\n")
                for key, val in self.config['measurement_mapping'].items():
                    f.write(f"{key} = {val}\n")
                for i, rm in enumerate(self.config['ratio_mapping']):
                    f.write(f"ratio_{i+1}_numerator = {rm.get('numerator')}\n")
                    f.write(f"ratio_{i+1}_denominator = {rm.get('denominator')}\n")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się zapisać config.txt: {e}")

        messagebox.showinfo("Informacja", f"Wyniki zapisane w folderze:\n{output_folder}")
        self.master.destroy()

def launch_gui():
    root = tk.Tk()
    root.state('zoomed')  # Otwórz na pełnym pulpicie (Windows)
    root.minsize(900, 600)
    app = SingleWindowGUI(root)
    root.mainloop()
    return app.config

if __name__ == '__main__':
    config = launch_gui()
    print("Plik:", config.get('file_path'))
    print("Interwał pomiarów:", config.get('measurement_interval'))
