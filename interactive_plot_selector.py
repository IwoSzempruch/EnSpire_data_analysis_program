#######################################
# interactive_plot_selector.py - zmodyfikowana wersja
#######################################
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plik: interactive_plot_selector.py

Interaktywny interfejs umożliwiający wyświetlenie wykresów:
  - Raw Measurements, Blank Corrected oraz F/OD Ratio
  (dane po obróbce, wynikającej z wcześniejszych analiz).
  
Funkcjonalności:
  - Globalne przypisanie kolorów do prób – dodawanie/odejmowanie danych nie zmienia przypisanych kolorów.
  - Nazwy pomiarów wyświetlane są zgodnie z mappingiem nadanym przez użytkownika (przez gui.py).
  - Suwak "Maksimum X" ustawia zakres osi X (maksymalna wartość ustawiona na podstawie maks. Time_min z danych).
  - Pozwala wyświetlać trendline (tylko liniowy i wielomianowy 2nd stopnia) oraz edytować opcje wykresu.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser, simpledialog
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class DraggableText:
    def __init__(self, text):
        self.text = text
        self.press = None
        self.cidpress = self.text.figure.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = self.text.figure.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion = self.text.figure.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def on_press(self, event):
        if event.inaxes != self.text.axes:
            return
        contains, _ = self.text.contains(event)
        if not contains:
            return
        x0, y0 = self.text.get_position()
        self.press = (x0, y0, event.xdata, event.ydata)

    def on_motion(self, event):
        if self.press is None or event.inaxes != self.text.axes:
            return
        x0, y0, xpress, ypress = self.press
        dx = event.xdata - xpress
        dy = event.ydata - ypress
        self.text.set_position((x0 + dx, y0 + dy))
        self.text.figure.canvas.draw()

    def on_release(self, event):
        self.press = None
        self.text.figure.canvas.draw()

    def disconnect(self):
        self.text.figure.canvas.mpl_disconnect(self.cidpress)
        self.text.figure.canvas.mpl_disconnect(self.cidrelease)
        self.text.figure.canvas.mpl_disconnect(self.cidmotion)

class InteractivePlotSelector(tk.Toplevel):
    def __init__(self, master, base_dir, config=None):
        super().__init__(master)
        self.title("Interaktywny wybór wykresów")
        self.base_dir = base_dir
        self.config = config if config is not None else {}
        self.data = None
        self.data_history = []  
        self.samples = []
        self.trendlines = {}  
        self.draggable_texts = []
        self.equation_font_size = 10
        # Globalna mapa kolorów – nie jest resetowana przy dodawaniu danych
        self.custom_colors = self.config.get("custom_colors", {}) 

        self.mode_var = tk.StringVar(value="F/OD Ratio")
        self.mode_options = ["F/OD Ratio", "Blank Corrected", "Raw Measurements"]

        self.measurement_var = tk.StringVar(value="Meas A")
        self.measurement_options = ["Meas A", "Meas B"]

        self.trend_type_var = tk.StringVar(value="Liniowy")
        self.trend_type_options = ["Liniowy", "Wielomianowy (2nd stopnia)"]

        self.show_data_var = tk.BooleanVar(value=True)

        self.create_widgets()
        self.load_data()
        self.plot_data()

    def get_selected_samples(self):
        indices = self.sample_listbox.curselection()
        return [self.sample_listbox.get(i) for i in indices]

    def reselect_samples(self, selected_samples):
        for idx, sample in enumerate(self.samples):
            if sample in selected_samples:
                self.sample_listbox.selection_set(idx)

    def create_widgets(self):
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Label(top_frame, text="Tryb analizy:").pack(side=tk.LEFT, padx=5)
        self.mode_combo = ttk.Combobox(top_frame, textvariable=self.mode_var, values=self.mode_options, state="readonly")
        self.mode_combo.pack(side=tk.LEFT, padx=5)
        self.mode_combo.bind("<<ComboboxSelected>>", lambda e: self.on_mode_change())
        self.measurement_frame = tk.Frame(top_frame)
        tk.Label(self.measurement_frame, text="Wybierz pomiar:").pack(side=tk.LEFT, padx=5)
        self.measurement_combo = ttk.Combobox(self.measurement_frame, textvariable=self.measurement_var, values=self.measurement_options, state="readonly")
        self.measurement_combo.pack(side=tk.LEFT, padx=5)
        self.measurement_combo.bind("<<ComboboxSelected>>", lambda e: self.on_mode_change())
        if self.mode_var.get() != "F/OD Ratio":
            self.measurement_frame.pack(side=tk.LEFT, padx=5)
        self.trend_type_frame = tk.Frame(top_frame)
        tk.Label(self.trend_type_frame, text="Typ trendu:").pack(side=tk.LEFT, padx=5)
        self.trend_type_combo = ttk.Combobox(top_frame, textvariable=self.trend_type_var, values=self.trend_type_options, state="readonly")
        self.trend_type_combo.pack(side=tk.LEFT, padx=5)
        self.show_data_check = tk.Checkbutton(top_frame, text="Pokaż dane", variable=self.show_data_var, command=self.plot_data)
        self.show_data_check.pack(side=tk.LEFT, padx=5)
        self.btn_select_all = tk.Button(top_frame, text="Zaznacz wszystkie", command=self.select_all_samples)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)
        self.btn_deselect_all = tk.Button(top_frame, text="Odznacz wszystkie", command=self.deselect_all_samples)
        self.btn_deselect_all.pack(side=tk.LEFT, padx=5)
        self.btn_add_data = tk.Button(top_frame, text="Dodaj dane z kolejnej analizy", command=self.add_data)
        self.btn_add_data.pack(side=tk.LEFT, padx=5)
        self.btn_undo = tk.Button(top_frame, text="Cofnij dodanie danych", command=self.undo_add_data)
        self.btn_undo.pack(side=tk.LEFT, padx=5)
        self.btn_reverse_names = tk.Button(top_frame, text="Odwróć nazwy", command=self.reverse_names)
        self.btn_reverse_names.pack(side=tk.LEFT, padx=5)

        left_frame = tk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        tk.Label(left_frame, text="Wybierz próbki (podwójny klik zmienia kolor):").pack()
        self.sample_listbox = tk.Listbox(left_frame, selectmode=tk.MULTIPLE, height=15, exportselection=False)
        self.sample_listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.sample_listbox.bind("<<ListboxSelect>>", lambda event: self.plot_data())
        self.sample_listbox.bind("<Double-Button-1>", self.change_color_for_sample)
        self.btn_rename_sample = tk.Button(left_frame, text="Zmień nazwę próby", command=self.rename_sample)
        self.btn_rename_sample.pack(pady=5)

        self.trend_control_frame = tk.Frame(self)
        self.trend_control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.btn_show_trend = tk.Button(self.trend_control_frame, text="Pokaż trendline", command=self.show_trendline)
        self.btn_show_trend.pack(side=tk.LEFT, padx=5)
        self.btn_hide_trend = tk.Button(self.trend_control_frame, text="Ukryj trendline", command=self.hide_trendline)
        self.btn_hide_trend.pack(side=tk.LEFT, padx=5)
        self.font_size_scale = tk.Scale(self.trend_control_frame, from_=6, to=20, orient=tk.HORIZONTAL, command=self.update_font_size)
        self.font_size_scale.set(self.equation_font_size)
        # Suwak nie pakowany domyślnie

        self.plot_options_frame = tk.Frame(self)
        self.plot_options_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Label(self.plot_options_frame, text="Etykieta osi X:").grid(row=0, column=0, sticky="e")
        self.x_label_entry = tk.Entry(self.plot_options_frame, width=15)
        self.x_label_entry.insert(0, "Czas (min)")
        self.x_label_entry.grid(row=0, column=1, padx=5)
        tk.Label(self.plot_options_frame, text="Etykieta osi Y:").grid(row=0, column=2, sticky="e")
        self.y_label_entry = tk.Entry(self.plot_options_frame, width=15)
        self.y_label_entry.grid(row=0, column=3, padx=5)
        tk.Label(self.plot_options_frame, text="Tytuł wykresu:").grid(row=0, column=4, sticky="e")
        self.title_entry = tk.Entry(self.plot_options_frame, width=20)
        self.title_entry.grid(row=0, column=5, padx=5)
        self.btn_update_plot = tk.Button(self.plot_options_frame, text="Aktualizuj wykres", command=self.update_plot_options)
        self.btn_update_plot.grid(row=0, column=6, padx=5)
        self.btn_save_plot = tk.Button(self.plot_options_frame, text="Zapisz wykres", command=self.save_plot)
        self.btn_save_plot.grid(row=0, column=7, padx=5)
        tk.Label(self.plot_options_frame, text="Maksimum X:").grid(row=1, column=0, sticky="e")
        self.x_max_scale = tk.Scale(self.plot_options_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.update_x_range)
        self.x_max_scale.grid(row=1, column=1, padx=5)

        self.fig, self.ax = plt.subplots(figsize=(8,6))
        self.ax.set_xlabel("Czas (min)")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def update_x_range(self, value):
        try:
            max_val = float(value)
            self.ax.set_xlim(right=max_val)
            self.plot_data()
        except Exception as e:
            messagebox.showerror("Błąd", f"Błędna wartość zakresu: {e}")

    def select_all_samples(self):
        self.sample_listbox.select_set(0, tk.END)
        self.plot_data()

    def deselect_all_samples(self):
        self.sample_listbox.selection_clear(0, tk.END)
        self.plot_data()

    def rename_sample(self):
        selection = self.sample_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Wybierz próbkę do zmiany nazwy.")
            return
        index = selection[0]
        old_name = self.sample_listbox.get(index)
        new_name = simpledialog.askstring("Zmień nazwę próby", f"Podaj nową nazwę dla próby '{old_name}':")
        if new_name and new_name.strip():
            self.data.loc[self.data["Sample"] == old_name, "Sample"] = new_name.strip()
            if old_name in self.custom_colors:
                self.custom_colors[new_name.strip()] = self.custom_colors.pop(old_name)
            self.samples = sorted(self.data["Sample"].unique())
            self.sample_listbox.delete(0, tk.END)
            for sample in self.samples:
                self.sample_listbox.insert(tk.END, sample)
            self.plot_data()

    def reverse_names(self):
        old_selected = self.get_selected_samples()
        file_path = filedialog.askopenfilename(title="Wybierz well-to-plate-assignment.csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        try:
            mapping = pd.read_csv(file_path, encoding="latin1")
            if not set(["Well", "Assignment"]).issubset(mapping.columns):
                raise ValueError("Plik musi zawierać kolumny 'Well' i 'Assignment'.")
            def reverse_name(name):
                base = name.split("_")[0]
                sub = mapping[mapping["Assignment"] == base]
                if not sub.empty:
                    return str(sub.iloc[0]["Well"])
                return name
            self.data["Sample"] = self.data["Sample"].apply(reverse_name)
            self.samples = sorted(self.data["Sample"].unique())
            self.sample_listbox.delete(0, tk.END)
            for sample in self.samples:
                self.sample_listbox.insert(tk.END, sample)
            new_selected = [reverse_name(s) for s in old_selected]
            for sample in new_selected:
                try:
                    idx = self.samples.index(sample)
                    self.sample_listbox.selection_set(idx)
                except ValueError:
                    pass
            self.plot_data()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się odwrócić nazw: {e}")

    def add_data(self):
        folder = filedialog.askdirectory(title="Wybierz folder z analizą")
        if not folder:
            return
        mode = self.mode_var.get()
        try:
            if mode == "F/OD Ratio":
                file_path = os.path.join(folder, "blank_corrected_analysis", "blank_corrected_summary.csv")
                if not os.path.isfile(file_path):
                    raise FileNotFoundError(f"Brak pliku: {file_path}")
                df_bc = pd.read_csv(file_path, encoding="latin1")
                df_A = df_bc[df_bc["Measurement"]=="Meas A"].copy()
                df_B = df_bc[df_bc["Measurement"]=="Meas B"].copy()
                if df_A.empty or df_B.empty:
                    raise ValueError("Brak danych dla obu pomiarów w analizie.")
                df_A = df_A.rename(columns={"Corrected": "Corrected_A"})
                df_B = df_B.rename(columns={"Corrected": "Corrected_B"})
                df_merged = pd.merge(df_A, df_B, on=["Sample", "Kinetics", "Time_min"], suffixes=("_A", "_B"))
                df_merged["Ratio"] = df_merged["Corrected_A"] / df_merged["Corrected_B"]
                df_new = df_merged[["Sample", "Time_min", "Ratio"]].copy()
            elif mode == "Blank Corrected":
                file_path = os.path.join(folder, "blank_corrected_analysis", "blank_corrected_summary.csv")
                if not os.path.isfile(file_path):
                    raise FileNotFoundError(f"Brak pliku: {file_path}")
                df_new = pd.read_csv(file_path, encoding="latin1")
                required = {"Sample", "Time_min", "Corrected", "Measurement"}
                if not required.issubset(df_new.columns):
                    raise ValueError("Plik blank_corrected_summary.csv nie zawiera wymaganych kolumn.")
                meas_choice = self.measurement_var.get()
                df_new = df_new[df_new["Measurement"] == meas_choice]
            elif mode == "Raw Measurements":
                file_path = os.path.join(self.base_dir, "long_merged.csv")
                if not os.path.isfile(file_path):
                    file_path = os.path.join(self.base_dir, "long_measA.csv")
                if not os.path.isfile(file_path):
                    raise FileNotFoundError(f"Brak pliku raw: {file_path}")
                df_new = pd.read_csv(file_path, encoding="latin1")
                if "Time_min" not in df_new.columns:
                    interval = self.get_measurement_interval()
                    df_new['Kinetics'] = pd.to_numeric(df_new['Kinetics'], errors="coerce")
                    df_new['Time_min'] = (df_new['Kinetics'] - 1) * interval
                required = {"Sample", "Time_min", "Value", "Measurement"}
                if not required.issubset(df_new.columns):
                    raise ValueError("Plik raw nie zawiera wymaganych kolumn.")
                meas_choice = self.measurement_var.get()
                df_new = df_new[df_new["Measurement"] == meas_choice]
                grouped = df_new.groupby(['Sample','Time_min'])['Value'].agg(['mean','std']).reset_index()
                grouped.rename(columns={"mean": "Value_mean", "std": "Value_std"}, inplace=True)
                df_new = grouped
            else:
                return

            if self.data is not None:
                self.data_history.append(self.data.copy())
            else:
                self.data_history.append(pd.DataFrame())

            default_suffix = f"_{os.path.basename(folder)}"
            custom = simpledialog.askstring("Sufiks", f"Podaj sufiks dla wszystkich prób z folderu {os.path.basename(folder)} (pozostaw puste, by użyć domyślnego '{default_suffix}'):")            
            suffix = f"_{custom.strip()}" if custom and custom.strip() != "" else default_suffix
            df_new['Sample'] = df_new['Sample'].astype(str) + suffix

            if self.data is None:
                self.data = df_new
            else:
                self.data = pd.concat([self.data, df_new], ignore_index=True)
            if "Sample" in self.data.columns:
                self.samples = sorted(self.data["Sample"].unique())
                self.sample_listbox.delete(0, tk.END)
                for sample in self.samples:
                    self.sample_listbox.insert(tk.END, sample)
            self.plot_data()
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def undo_add_data(self):
        if not self.data_history:
            messagebox.showinfo("Info", "Brak operacji do cofnięcia.")
            return
        self.data = self.data_history.pop()
        if "Sample" in self.data.columns:
            self.samples = sorted(self.data["Sample"].unique())
            self.sample_listbox.delete(0, tk.END)
            for sample in self.samples:
                self.sample_listbox.insert(tk.END, sample)
        else:
            self.samples = []
        self.plot_data()
        messagebox.showinfo("Info", "Ostatnie dodanie danych zostało cofnięte.")

    def on_mode_change(self):
        old_selected = self.get_selected_samples()
        if self.mode_var.get() == "F/OD Ratio":
            self.measurement_frame.pack_forget()
        else:
            self.measurement_frame.pack(side=tk.LEFT, padx=5)
        self.load_data()
        self.reselect_samples(old_selected)
        self.plot_data()

    def get_measurement_interval(self):
        config_path = os.path.join(self.base_dir, "config.txt")
        interval = 20
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r") as f:
                    for line in f:
                        if "measurement_interval" in line:
                            interval = float(line.split("=")[1].strip())
                            break
            except Exception:
                interval = 20
        return interval

    def load_data(self):
        mode = self.mode_var.get()
        try:
            if mode == "F/OD Ratio":
                bc_file = os.path.join(self.base_dir, "blank_corrected_analysis", "blank_corrected_summary.csv")
                if not os.path.isfile(bc_file):
                    raise FileNotFoundError(f"Brak pliku: {bc_file}")
                df_bc = pd.read_csv(bc_file, encoding="latin1")
                df_A = df_bc[df_bc["Measurement"]=="Meas A"].copy()
                df_B = df_bc[df_bc["Measurement"]=="Meas B"].copy()
                if df_A.empty or df_B.empty:
                    raise ValueError("Brak danych dla obu pomiarów w pliku blank_corrected_summary.csv.")
                df_A = df_A.rename(columns={"Corrected": "Corrected_A"})
                df_B = df_B.rename(columns={"Corrected": "Corrected_B"})
                df_merged = pd.merge(df_A, df_B, on=["Sample", "Kinetics", "Time_min"], suffixes=("_A", "_B"))
                df_merged["Ratio"] = df_merged["Corrected_A"] / df_merged["Corrected_B"]
                ratio_file = os.path.join(self.base_dir, "Fluorescence_to_OD_ratio", "ratio_summary.csv")
                if os.path.isfile(ratio_file):
                    df_ratio = pd.read_csv(ratio_file, encoding="latin1")
                    df_final = pd.merge(df_merged, df_ratio[["Sample", "Time_min", "Ratio_std"]], on=["Sample", "Time_min"], how="left")
                else:
                    df_final = df_merged
                self.data = df_final
                self.y_label_entry.delete(0, tk.END)
                self.y_label_entry.insert(0, "F/OD Ratio")
            elif mode == "Blank Corrected":
                file_path = os.path.join(self.base_dir, "blank_corrected_analysis", "blank_corrected_summary.csv")
                if not os.path.isfile(file_path):
                    raise FileNotFoundError(f"Brak pliku: {file_path}")
                df = pd.read_csv(file_path, encoding="latin1")
                required = {"Sample", "Time_min", "Corrected", "Measurement"}
                if not required.issubset(df.columns):
                    raise ValueError("Plik blank_corrected_summary.csv nie zawiera wymaganych kolumn.")
                meas_choice = self.measurement_var.get()
                df = df[df["Measurement"] == meas_choice]
                self.data = df
                self.y_label_entry.delete(0, tk.END)
                self.y_label_entry.insert(0, "Corrected Value")
            elif mode == "Raw Measurements":
                file_path = os.path.join(self.base_dir, "long_merged.csv")
                if not os.path.isfile(file_path):
                    file_path = os.path.join(self.base_dir, "long_measA.csv")
                if not os.path.isfile(file_path):
                    raise FileNotFoundError(f"Brak pliku raw: {file_path}")
                df = pd.read_csv(file_path, encoding="latin1")
                if "Time_min" not in df.columns:
                    interval = self.get_measurement_interval()
                    df['Kinetics'] = pd.to_numeric(df['Kinetics'], errors="coerce")
                    df['Time_min'] = (df['Kinetics'] - 1) * interval
                required = {"Sample", "Time_min", "Value", "Measurement"}
                if not required.issubset(df.columns):
                    raise ValueError("Plik raw nie zawiera wymaganych kolumn.")
                meas_choice = self.measurement_var.get()
                df = df[df["Measurement"] == meas_choice]
                grouped = df.groupby(['Sample','Time_min'])['Value'].agg(['mean','std']).reset_index()
                grouped.rename(columns={"mean": "Value_mean", "std": "Value_std"}, inplace=True)
                self.data = grouped
                self.y_label_entry.delete(0, tk.END)
                self.y_label_entry.insert(0, "Value")
            else:
                self.data = None
        except Exception as e:
            messagebox.showerror("Błąd", str(e))
            self.data = None
            return

        if self.data is not None and "Sample" in self.data.columns:
            self.samples = sorted(self.data["Sample"].unique())
            self.sample_listbox.delete(0, tk.END)
            for sample in self.samples:
                self.sample_listbox.insert(tk.END, sample)
            max_time = self.data["Time_min"].max()
            self.x_max_scale.config(to=max_time)
            self.x_max_scale.set(max_time)
        else:
            self.samples = []

    def plot_data(self):
        if self.data is None:
            return
        self.ax.clear()
        mode = self.mode_var.get()
        if mode == "F/OD Ratio":
            self.ax.set_ylabel("F/OD Ratio")
        elif mode == "Blank Corrected":
            self.ax.set_ylabel("Corrected Value")
        elif mode == "Raw Measurements":
            self.ax.set_ylabel("Value")
        self.ax.set_xlabel("Czas (min)")
        self.ax.grid(True)
        self.trendlines.clear()
        self.draggable_texts = []
        x_max = self.x_max_scale.get()
        selected_indices = self.sample_listbox.curselection()
        if not selected_indices:
            selected_samples = self.samples
        else:
            selected_samples = [self.sample_listbox.get(i) for i in selected_indices]
        self.sample_lines = {}
        colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        color_map = {sample: self.custom_colors.get(sample, colors[i % len(colors)]) for i, sample in enumerate(selected_samples)}
        for sample in selected_samples:
            df_sample = self.data[self.data["Sample"] == sample].copy()
            df_sample = df_sample.sort_values("Time_min")
            df_sample = df_sample[df_sample["Time_min"] <= x_max]
            if df_sample.empty:
                continue
            x = df_sample["Time_min"].values
            if self.show_data_var.get():
                if mode == "F/OD Ratio":
                    y = df_sample["Ratio"].values
                    yerr = df_sample["Ratio_std"].values if "Ratio_std" in df_sample.columns else None
                    line, caps, bars = self.ax.errorbar(x, y, yerr=yerr, fmt='-o', capsize=5,
                                                         label=sample, color=color_map[sample])
                elif mode == "Blank Corrected":
                    y = df_sample["Corrected"].values
                    yerr = df_sample["Sample_std"].values if "Sample_std" in df_sample.columns else None
                    line, caps, bars = self.ax.errorbar(x, y, yerr=yerr, fmt='-o', capsize=5,
                                                         label=sample, color=color_map[sample])
                elif mode == "Raw Measurements":
                    y = df_sample["Value_mean"].values
                    yerr = df_sample["Value_std"].values
                    line, caps, bars = self.ax.errorbar(x, y, yerr=yerr, fmt='-o', capsize=5,
                                                         label=sample, color=color_map[sample])
                else:
                    continue
            else:
                line = None
            if line is not None:
                self.sample_lines[sample] = line
        self.ax.legend()
        self.canvas.draw()

    def show_trendline(self):
        if self.data is None:
            return
        mode = self.mode_var.get()
        selected = self.sample_listbox.curselection()
        if not selected:
            selected_samples = self.samples
        else:
            selected_samples = [self.sample_listbox.get(i) for i in selected]
        self.font_size_scale.pack(side=tk.LEFT, padx=5)
        x_max = self.x_max_scale.get()
        for sample in selected_samples:
            df_sample = self.data[self.data["Sample"] == sample].copy()
            df_sample = df_sample.sort_values("Time_min")
            df_sample = df_sample[df_sample["Time_min"] <= x_max]
            if df_sample.empty or len(df_sample) < 2:
                continue
            x = df_sample["Time_min"].values
            if mode == "F/OD Ratio":
                y = df_sample["Ratio"].values
            elif mode == "Blank Corrected":
                y = df_sample["Corrected"].values
            elif mode == "Raw Measurements":
                y = df_sample["Value_mean"].values
            else:
                continue
            trend_type = self.trend_type_var.get()
            if trend_type == "Liniowy":
                coeffs = np.polyfit(x, y, 1)
                trend_func = np.poly1d(coeffs)
                eq_text = f"y = {coeffs[0]:.2f}x + {coeffs[1]:.2f}"
            elif trend_type == "Wielomianowy (2nd stopnia)":
                coeffs = np.polyfit(x, y, 2)
                trend_func = np.poly1d(coeffs)
                eq_text = f"y = {coeffs[0]:.2f}x² + {coeffs[1]:.2f}x + {coeffs[2]:.2f}"
            else:
                continue

            x_fit = np.linspace(x.min(), x.max(), 100)
            y_fit = trend_func(x_fit)
            color = (self.sample_lines[sample].get_color() if sample in self.sample_lines 
                     else self.custom_colors.get(sample, 'black'))
            if sample in self.trendlines:
                self.trendlines[sample].append((self.ax.plot(x_fit, y_fit, '--', color=color)[0],
                                                self.ax.text(x_fit.max(), trend_func(x_fit.max()), eq_text,
                                                             fontsize=self.equation_font_size,
                                                             color=color, verticalalignment='bottom',
                                                             horizontalalignment='right',
                                                             backgroundcolor='white', picker=True)))
            else:
                self.trendlines[sample] = [(self.ax.plot(x_fit, y_fit, '--', color=color)[0],
                                            self.ax.text(x_fit.max(), trend_func(x_fit.max()), eq_text,
                                                         fontsize=self.equation_font_size,
                                                         color=color, verticalalignment='bottom',
                                                         horizontalalignment='right',
                                                         backgroundcolor='white', picker=True))]
            draggable = DraggableText(self.trendlines[sample][-1][1])
            self.draggable_texts.append(draggable)
        self.canvas.draw()

    def hide_trendline(self):
        selected = self.sample_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Wybierz próbki, dla których chcesz ukryć trendline.")
            return
        selected_samples = [self.sample_listbox.get(i) for i in selected]
        for sample in selected_samples:
            if sample in self.trendlines:
                for trend_line, text_obj in self.trendlines[sample]:
                    trend_line.remove()
                    text_obj.remove()
                del self.trendlines[sample]
        self.font_size_scale.pack_forget()
        self.canvas.draw()

    def update_font_size(self, value):
        self.equation_font_size = int(value)
        for sample, trend_list in self.trendlines.items():
            for trend_line, text_obj in trend_list:
                text_obj.set_fontsize(self.equation_font_size)
        self.canvas.draw()

    def update_plot_options(self):
        x_label = self.x_label_entry.get()
        y_label = self.y_label_entry.get()
        title = self.title_entry.get()
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_title(title)
        self.canvas.draw()

    def save_plot(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("Pliki PNG", "*.png"), ("Wszystkie pliki", "*.*")],
                                                 title="Zapisz wykres")
        if file_path:
            self.fig.savefig(file_path)
            messagebox.showinfo("Informacja", f"Wykres zapisano do:\n{file_path}")

    def change_color_for_sample(self, event):
        index = self.sample_listbox.nearest(event.y)
        if index is None:
            return "break"
        sample = self.sample_listbox.get(index)
        color = colorchooser.askcolor()[1]
        if color:
            self.custom_colors[sample] = color
            self.plot_data()
        return "break"

def launch_plot_selector(base_dir, config=None):
    root = tk.Tk()
    root.withdraw()
    app = InteractivePlotSelector(root, base_dir, config)
    root.mainloop()

if __name__ == "__main__":
    import sys
    root = tk.Tk()
    root.withdraw()
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = filedialog.askdirectory(title="Wybierz folder roboczy")
        if not base_dir:
            print("Nie wybrano folderu. Zakończenie programu.")
            sys.exit(1)
    root.destroy()
    launch_plot_selector(base_dir)
