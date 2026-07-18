import customtkinter
import serial
import time
import struct
import matplotlib.pyplot as plt
import csv
from datetime import datetime
import serial.tools.list_ports
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import sys, os, pyglet
import matplotlib.dates as mdates

# Global variables
BUFFER_SIZE = 100
ser = None
plotting = False
logging_csv = False
log_start_time = None
start_time = None
csv_file = None
csv_writer = None
current_unit_str = ""
current_meter_function = None
current_function_range = None
error_log = ""

# Meter functions and units lookup tables
modes = {
    1:  {'name': 'Volts AC',           'unit': 'V AC',     'needs_prefix': False},
    2:  {'name': 'milliVolts AC',      'unit': 'mV AC',    'needs_prefix': False},
    3:  {'name': 'Volts DC',           'unit': 'V DC',     'needs_prefix': False},
    4:  {'name': 'milliVolts DC',      'unit': 'mV DC',    'needs_prefix': False},
    5:  {'name': 'AC+DC Volts',        'unit': 'V AC+DC',  'needs_prefix': False},
    6:  {'name': 'AC+DC milliVolts',   'unit': 'mV AC+DC', 'needs_prefix': False},
    9:  {'name': 'Ohms',               'unit': 'Ω',        'needs_prefix': True},
    10: {'name': 'Conductance',        'unit': 'S',        'needs_prefix': True},
    11: {'name': 'Continuity',         'unit': 'Ω',        'needs_prefix': False},
    12: {'name': 'Capacitance',        'unit': 'F',        'needs_prefix': True},
    13: {'name': 'Volts DC (Diode)',   'unit': 'V DC',     'needs_prefix': False},
    14: {'name': 'Amps AC',            'unit': 'A AC',     'needs_prefix': False},
    15: {'name': 'milliAmps AC',       'unit': 'mA AC',    'needs_prefix': False},
    16: {'name': 'microAmps AC',       'unit': 'µA AC',    'needs_prefix': False},
    17: {'name': 'Amps DC',            'unit': 'A DC',     'needs_prefix': False},
    18: {'name': 'milliAmps DC',       'unit': 'mA DC',    'needs_prefix': False},
    19: {'name': 'microAmps DC',       'unit': 'µA DC',    'needs_prefix': False},
    26: {'name': 'Temperature',        'unit': '°C',       'needs_prefix': False},
    27: {'name': 'Temperature',        'unit': '°F',       'needs_prefix': False},
    65: {'name': 'Frequency',          'unit': 'Hz',       'needs_prefix': False},
    132:{'name': 'Duty Cycle',         'unit': '%',        'needs_prefix': False},
    194:{'name': 'Pulse Width',        'unit': 'ms',       'needs_prefix': False},
}

prefix_map = {0: '', -1: 'm', -2: 'µ', -3: 'n', 1: 'k', 2: 'M'}

def set_icon():
    icon_path = resource_path("logo.png")
    icon_img = ImageTk.PhotoImage(file=icon_path)
    app.iconphoto(False, icon_img)
    app._icon_ref = icon_img

def resource_path(relative_path):
    """Get absolute path to resource for canvas image and app icon"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def refresh_ports():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    port_dropdown.configure(values=ports)

    if ports:
        port_dropdown.set(ports[0])

def connect():
    global ser
    try:
        port = port_dropdown.get()
        ser = serial.Serial(port, 9600, timeout=0.5)
        ser.write(b'ID\r')
        response = ser.read(256)
        if b'FLUKE' in response:    
            status_label.configure(text="Connected", text_color="green")
            response_str = response.decode('ascii')
            id_string = response_str.split('\r')[-2]
            parts = id_string.split(',')
            model = parts[0].strip()       
            firmware = parts[1].strip()    
            serial_no = parts[2].strip()   
            device_info_label.configure(text=f"Model: {model.title()}  Firmware: {firmware}  S/No: {serial_no}", text_color="grey")
        else:
            ser.close()
            ser = None
            status_label.configure(text="No meter found", text_color="red")
    except Exception as e:
        error_log.append(e)
        ser = None
        status_label.configure(text="Not Connected", text_color="red")

def button_press(command):
    ser.write(f'{command}\r'.encode('utf-8'))
    time.sleep(0.3)
    ser.reset_input_buffer() # clear any leftover bytes

def get_units(mode, byte36, byte37, pri_prefix, sec_prefix):
    base_mode = mode & 0x3F
    hz_modifier = mode & 0xC0
    is_db_pri = bool(byte37 & 0x08)
    is_db_sec = bool(byte37 & 0x10)

    acdc_state = byte36 & 0x03
    
    m = modes.get(base_mode, {'name': 'Unknown', 'unit': '?', 'needs_prefix': False})
    
    # Base unit strings with prefixes applied
    if m['needs_prefix']:
        base_pri = pri_prefix + m['unit']
        base_sec = sec_prefix + m['unit']
    else:
        base_pri = m['unit']
        base_sec = m['unit']
    
    # --- Primary unit ---
    if is_db_pri:
        pri_unit = "dB" + m['unit'].split()[0]
    elif hz_modifier == 0x40:
        pri_unit = "Hz"
    elif hz_modifier == 0x80:
        pri_unit = "%"
    elif hz_modifier == 0xC0:
        pri_unit = "ms"
    elif acdc_state == 0x01:
        base = m['unit'].replace('AC+DC', '').strip()
        pri_unit = base + " AC"
    elif acdc_state == 0x02:
        base = m['unit'].replace('AC+DC', '').strip()
        pri_unit = base + " DC"
    else:
        pri_unit = base_pri
    
    # --- Secondary unit ---
    if is_db_sec:
        sec_unit = "dB" + m['unit'].split()[0]
    elif hz_modifier in (0x80, 0xC0):
        sec_unit = "Hz"
    elif acdc_state == 0x01:
        base = m['unit'].replace('AC+DC', '').strip()
        sec_unit = base + " DC"
    elif acdc_state == 0x02:
        base = m['unit'].replace('AC+DC', '').strip()
        sec_unit = base + " AC"
    else:
        sec_unit = base_sec
    
    return pri_unit, sec_unit, m

def get_decimal(byte):
    if byte & 0x80:
        return (byte & 0x7F) + 1
    return byte

def switch_view(value):
    if value == "TrendPlot":
        download_frame.pack_forget()
        live_frame.pack(fill="both", expand=True)
    else:
        live_frame.pack_forget()
        download_frame.pack(fill="both", expand =True)

def toggle_plot():
    global plotting, start_time
    plotting = not plotting
    if plotting:
        start_time = time.time()
        run_pause_button.configure(text="⏸ Pause", fg_color="red")
    else:
        run_pause_button.configure(text="▶ Run", fg_color="green")

def open_log_options():
    if set_live_log.get():
        live_data_timing.configure(state="normal")
        trend_plot_logging.configure(state="normal")
    else:
        live_data_timing.configure(state="disabled")
        trend_plot_logging.configure(state="disabled")

def toggle_logging():
    global logging_csv, log_start_time, csv_file, csv_writer
    if not logging_csv:
        filepath = customtkinter.filedialog.asksaveasfilename(defaultextension='.csv')
        log_start_time = None
        if filepath:
            csv_file = open(filepath, 'w', newline='', encoding='utf-8-sig')
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['Timestamp', current_unit_str])
            logging_csv = True
            trend_plot_logging.configure(text="⏹ Stop Log", fg_color="red")
    else:
        csv_file.close()
        logging_csv = False
        trend_plot_logging.configure(text="LOG", fg_color="green")

def check_download_options():
    if save_csv_var.get() or save_png_var.get():
        download_button.configure(state="normal")
    else:
        download_button.configure(state="disabled")
    if save_png_var.get():
        plot_title.configure(state="normal")
    else:
        plot_title.configure(state="disabled")

def download_logs():
    filepath = customtkinter.filedialog.asksaveasfilename(
        defaultextension="",
        filetypes=[("All files", "*.*")]
    )
    if not filepath:
        return
    base = filepath.rsplit('.',1)[0] if '.' in filepath else filepath

    ser.write(b'QD 2\r')
    time.sleep(5)        # wait for meter to send everything
    response = b''
    while True:
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            break
        response += chunk
        time.sleep(0.5)
    
    data = response[28:]
    header = response[10:28]
    mode = header[12]
    units_byte = struct.unpack('b', bytes([header[7]]))[0]
    prefix = prefix_map.get(units_byte, '')
    pri_unit, sec_unit, m = get_units(mode, 0, 0, prefix, '')
    unit = pri_unit
    name = m['name']

    timing = download_data_timing.get()
    entries = []
    first_ts = None
    for i in range(1000):
        entry = data[i*32:(i+1)*32]
        if len(entry) < 32:
            break
        try:
            ts = struct.unpack('<I', entry[0:4])[0]
            raw_total = struct.unpack('<I', entry[14:18])[0]
            # Skip invalid entries (0x70 in high byte)
            if (raw_total >> 24) == 0x70:
                continue
            total = struct.unpack('<i', entry[14:18])[0]
            count = struct.unpack('<i', entry[22:26])[0]
            min_val = struct.unpack('<i', entry[6:10])[0]
            max_val = struct.unpack('<i', entry[10:14])[0]
            decimal_point = get_decimal(entry[4])
            status = entry[26]
            seconds = (ts / 10) % 86400
            if first_ts is None:
                first_ts = seconds
            if timing == "Clock":
                h = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                timestamp = f"{h:02d}:{mins:02d}:{s:02d}"
            else:
                timestamp = round(seconds - first_ts, 1)
            reading = round((total / count) / (10 ** decimal_point), decimal_point)
            entries.append((timestamp, reading))

        except Exception as e:
            error_log.append(e)
            break

    if save_csv_var.get():
        with open(base + '.csv', 'w', newline='', encoding='utf-8-sig') as f:
            wr = csv.writer(f)
            wr.writerow(['timestamp', f'{name} {unit}'])
            wr.writerows(entries)

    if save_png_var.get():
        timestamps = [e[0] for e in entries]
        readings = [e[1] for e in entries]
        
        fig, ax = plt.subplots(figsize=(12, 4))
        
        if timing == "Elapsed":
            ax.plot(timestamps, readings)
            ax.set_xlabel('Time (s)')
            ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=15))
        else:
            dt_timestamps = [datetime.strptime(t, '%H:%M:%S') for t in timestamps]
            ax.plot(dt_timestamps, readings)
            ax.set_xlabel('Time')
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            fig.autofmt_xdate()
        
        ax.margins(x=0)
        if name == "Temperature":
            ax.set_ylabel(f'{name} ({unit})')
        else:
            ax.set_ylabel(f'{name}')
        ax.set_title(plot_title.get())  # empty string gives no title cleanly
        
        plt.tight_layout()
        plt.savefig(base + '.png', bbox_inches='tight')
        plt.close(fig)

def update_reading():
    global current_unit_str, current_meter_function, current_function_range, plotting, readings_buffer, time_buffer, log_start_time
    if ser is None:
        app.after(500, update_reading)
        return
    try:
        ser.write(b'QD 0\r')
        response = ser.read(1024)
        data = response[10:]
        
        primary_value = struct.unpack('<I', data[4:8])[0]
        primary_decimal = get_decimal(data[8])
        primary_units = struct.unpack('b', bytes([data[9]]))[0]
        pri_prefix = prefix_map.get(primary_units, '')
        sec_units_byte = struct.unpack('b', bytes([data[15]]))[0]
        sec_prefix = prefix_map.get(sec_units_byte, '')
        mode = data[34]

        pri_unit, sec_unit, m = get_units(mode, data[36], data[37], pri_prefix, sec_prefix)
        current_unit_str = pri_unit

        # Mode change detection
        if current_meter_function is not None and mode != current_meter_function:
            # Re-initialize with None rather than completely clearing them out
            readings_buffer = [None] * BUFFER_SIZE
            time_buffer = [""] * BUFFER_SIZE
            
            plotting = False
            run_pause_button.configure(text="▶ Run", fg_color="green")
            ax.clear()
            ax.set_facecolor('#1a1a2e')
            ax.grid(True, color='#cccccc', linewidth=0.5)
            ax.tick_params(colors='white')
            fig.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.10)
            canvas.draw()

        current_meter_function = mode

        # HOLD detection
        if data[30] & 0x02:
            plotting = False
            run_pause_button.configure(text="▶ Run", fg_color="green")

        # Primary reading
        reading_str = "OL"
        if (primary_value >> 24) == 0x70:
            primary_label.configure(text="OL")
            units_label.configure(text=pri_unit)
        else:
            primary_value = struct.unpack('<i', data[4:8])[0]
            reading = primary_value / (10 ** primary_decimal)
            reading_str = f'{reading:.{primary_decimal}f}'
            primary_label.configure(text=reading_str)
            units_label.configure(text=pri_unit)
        
        # Secondary reading
        secondary_value = struct.unpack('<I', data[10:14])[0]
        if (secondary_value >> 24) == 0x70:
            secondary_label.configure(text="")
            secondary_units_label.configure(text="")
        else:
            secondary_value = struct.unpack('<i', data[10:14])[0]
            sec_decimal = get_decimal(data[14])
            sec_units = struct.unpack('b', bytes([data[15]]))[0]
            sec_prefix = prefix_map.get(sec_units, '')
            sec_reading = secondary_value / (10 ** sec_decimal)
            sec_reading_str = f'{sec_reading:.{sec_decimal}f}'
            secondary_label.configure(text=sec_reading_str)
            secondary_units_label.configure(text=sec_unit)

        # Settings
        settings = []
        if data[30] & 0x03 == 0x03:
            settings.append("AutoHOLD")
        elif data[30] & 0x02:
            settings.append("HOLD")
        if data[30] & 0x04: settings.append("LOG")
        if data[30] & 0x08: settings.append("AVG")
        if data[30] & 0x10: settings.append("MAX")
        if data[30] & 0x20: settings.append("MIN")
        if data[37] == 0x81: settings.append("REL")
        if data[37] == 0x82: settings.append("REL%")
        settings_label.configure(text=" · ".join(settings))
        
        # Timing
        timing = live_data_timing.get()
        if timing == "Elapsed" and start_time is not None:
            t = round(time.time() - start_time, 1)
        else:
            t = datetime.now().strftime("%H:%M:%S")

        # Plot
        if plotting and reading_str != "OL":
            # Append new values to the end of the fixed-size array
            readings_buffer.append(float(reading_str))
            time_buffer.append(t)
            
            # Slice the lists to strictly keep the most recent 200 elements
            readings_buffer = readings_buffer[-BUFFER_SIZE:]
            time_buffer = time_buffer[-BUFFER_SIZE:]
            
            ax.clear()
            
            # Set explicit X limits so the graph area never shifts or resizes horizontally
            ax.set_xlim(0, BUFFER_SIZE - 1)
            
            # Plot using your static X positions. Matplotlib completely ignores 'None' values.
            ax.plot(x_positions, readings_buffer, color='#00ff88', linewidth=1)
            
            # Reapply your custom styling wiped by ax.clear()
            ax.set_facecolor('#1a1a2e')
            ax.grid(True, color='#cccccc', linewidth=0.5)
            ax.get_xaxis().set_visible(False) # Ensure X axis stays hidden
            ax.tick_params(colors='white')
            ax.set_ylabel(pri_unit, color='white')
            
            # Reapply the custom tight visual spacing we set up earlier
            fig.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.10)
            
            canvas.draw()

        # CSV logging
        if logging_csv:
            if log_start_time is None:
                log_start_time = time.time()
                print(f"Log start time set: {log_start_time}")
            log_t = round(time.time() - log_start_time, 1)
            print(f"Log t: {log_t}")
            csv_writer.writerow([log_t, reading_str])
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
    
    app.after(100, update_reading)

# --- App setup ---
ports = [port.device for port in serial.tools.list_ports.comports()]
customtkinter.set_appearance_mode("dark")
app = customtkinter.CTk()
app.geometry("800x600")
app.title("Fluke 189 Controller")
app.after(250, set_icon)
save_csv_var = customtkinter.BooleanVar(value=False)
save_png_var = customtkinter.BooleanVar(value=False)
set_live_log =  customtkinter.BooleanVar(value=False)
pyglet.font.add_file(resource_path("fonts/dseg7.ttf"))
display_font = customtkinter.CTkFont(family="DSEG7 Classic", size=80)
secondary_font = customtkinter.CTkFont(family="DSEG7 Classic", size=55)

# --- Connection bar ---
connection_frame = customtkinter.CTkFrame(app)
connection_frame.pack(fill="x", padx=10, pady=5)

refresh_button = customtkinter.CTkButton(connection_frame, text="↻", width=30, command=refresh_ports, fg_color="transparent")
refresh_button.pack(side="left", padx=5)

port_dropdown = customtkinter.CTkComboBox(connection_frame, values=ports, width=120)
port_dropdown.pack(side="left", padx=5)

connect_btn = customtkinter.CTkButton(connection_frame, text="Connect", command=connect, width=100)
connect_btn.pack(side="left", padx=5)

status_label = customtkinter.CTkLabel(connection_frame, text="Not Connected", text_color="red")
status_label.pack(side="left", padx=10)

device_info_label = customtkinter.CTkLabel(connection_frame, text = "--")
device_info_label.pack(side="right", padx=5)

# --- Meter Display ---
display_frame = customtkinter.CTkFrame(app, fg_color="#dde6ea", corner_radius=10)
display_frame.pack(fill="x", padx=10, pady=5)

display_frame.columnconfigure(0, weight=1)  # empty space pushes left
display_frame.columnconfigure(1, weight=0)  # reading stays tight
display_frame.columnconfigure(2, weight=0)  # units stays tight

primary_label = customtkinter.CTkLabel(display_frame, text="-----", font=display_font, text_color="black")
primary_label.grid(row=0, column=2, sticky="e", padx=10, pady=10)

units_label = customtkinter.CTkLabel(display_frame, text="", font=("Arial", 24), text_color="black")
units_label.grid(row=0, column=3, sticky="w", padx=(0, 20))

secondary_label = customtkinter.CTkLabel(display_frame, text="----", font=secondary_font, text_color="black")
secondary_label.grid(row=1, column=2, columnspan=1, sticky="e", padx=10, pady=5)

secondary_units_label = customtkinter.CTkLabel(display_frame, text="", font=("Arial", 15), text_color="black")
secondary_units_label.grid(row=1, column=3, sticky="w", padx=(0, 20))

settings_label = customtkinter.CTkLabel(display_frame, text="", font=("Arial", 30), text_color="black")
settings_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)

# --- Button Panel ---
button_panel = customtkinter.CTkFrame(app)
button_panel.pack(fill="x", padx=10, pady=5)

blue_button = customtkinter.CTkButton(button_panel, text = "", command=lambda: button_press("SF 10"), width=45, height=25, corner_radius=10, fg_color="sky blue")
blue_button.grid(row=0, column=1, padx=5, pady=5)

hold_button = customtkinter.CTkButton(button_panel, text="HOLD", command=lambda: button_press("SF 11"), width=90, height=25, corner_radius=10, border_color="white")
hold_button.grid(row=0, column=5, padx=5, pady=5)

rel_button = customtkinter.CTkButton(button_panel, text="REL Δ", command=lambda: button_press("SF 13"), width=90, height=25, corner_radius=10, border_color="white")
rel_button.grid(row=0, column=4, padx=5, pady=5)

shift_button = customtkinter.CTkButton(button_panel, text = "", command=lambda: button_press("SF 15"), width=90, height=25, corner_radius=10, fg_color="yellow")
shift_button.grid(row=0, column=2, padx=5, pady=5)

min_max_avg = customtkinter.CTkButton(button_panel, text="MIN/MAX", command=lambda: button_press("SF 12"), width=90, height=25, corner_radius=10, border_color="white")
min_max_avg.grid(row=0, column=6, padx=5, pady=5)

hertz_button = customtkinter.CTkButton(button_panel, text="Hz % ms", command=lambda: button_press("SF 16"), width=90, height=25, corner_radius=10, border_color="white")
hertz_button.grid(row=0, column=7, padx=5, pady=5)

up_button = customtkinter.CTkButton(button_panel, text="↑", command=lambda: button_press("SF 14"), width=45, height=25, corner_radius=10, border_color="white")
up_button.grid(row=0, column=8, padx=5, pady=5)

down_button = customtkinter.CTkButton(button_panel, text="↓", command=lambda: button_press("SF 18"), width=45, height=25, corner_radius=10, border_color="white")
down_button.grid(row=0, column=9, padx=5, pady=5)

range_button = customtkinter.CTkButton(button_panel, text="RANGE", command=lambda: button_press("SF 17"), width=90, height=25, corner_radius=10, border_color="white")
range_button.grid(row=0, column=3, padx=5, pady=5)

# --- Trend plot / download section ---
lower_section_frame = customtkinter.CTkFrame(app)
lower_section_frame.pack(fill="both", expand=True, padx=10, pady=5)
lower_section_frame.pack_propagate(False)
# # Toggle switch between trend plot and downloading logged data options
live_dl_seg_button = customtkinter.CTkSegmentedButton(lower_section_frame, values=["TrendPlot", "Download"], command=switch_view)
live_dl_seg_button.pack(fill="x", padx=5, pady=5)
live_dl_seg_button.set("TrendPlot")

# # Trend plot frame
live_frame = customtkinter.CTkFrame(lower_section_frame)
lower_section_toolbar = customtkinter.CTkFrame(live_frame, fg_color="transparent")
lower_section_toolbar.pack(fill='x', pady=5)
run_pause_button = customtkinter.CTkButton(lower_section_toolbar, text="▶ Run", fg_color="green", width=100, command=toggle_plot)
run_pause_button.pack(side="left", expand=True)
live_log_checkbox = customtkinter.CTkCheckBox(lower_section_toolbar, text="Log data to CSV", variable=set_live_log, command=open_log_options)
live_log_checkbox.pack(side="left", expand=True)
choice_label = customtkinter.CTkLabel(lower_section_toolbar, text="Independent Variable:   ")
choice_label.pack(side="left")
live_data_timing = customtkinter.CTkComboBox(lower_section_toolbar, values=['Clock', 'Elapsed'])
live_data_timing.configure(state="disabled")
live_data_timing.set("Clock")
live_data_timing.pack(side="left")
trend_plot_logging = customtkinter.CTkButton(lower_section_toolbar, text="LOG", fg_color="salmon", width=75, command=toggle_logging, state="disabled")
trend_plot_logging.pack(side="left", expand=True)
trend_plot_panel = customtkinter.CTkFrame(live_frame, fg_color="transparent")
trend_plot_panel.pack(fill="both", expand="True", padx=10, pady=5)

fig = Figure(figsize=(7, 4), facecolor='#2b2b2b')
ax = fig.add_subplot(111)
ax.set_facecolor('#1a1a2e')
ax.grid(True, color='#cccccc', linewidth=0.5)
ax.get_xaxis().set_visible(False)
ax.tick_params(colors='white')
ax.margins(x=0)
ax.set_ylabel('Value', color='white')
ax.set_xlabel('Time', color='white')
fig.subplots_adjust(left=0.065, right=0.96, top=0.95, bottom=0.10)

canvas = FigureCanvasTkAgg(fig, master=trend_plot_panel)
canvas.get_tk_widget().pack(fill="both", expand=True)
live_frame.pack(fill="both", expand=True)
# Download logged data from meter section
download_frame = customtkinter.CTkFrame(lower_section_frame)
# Select timing option for logged data
download_data_timing = customtkinter.CTkComboBox(download_frame, values=['Clock', "Elapsed"])
download_data_timing.pack(padx=10, pady=10)

download2csv = customtkinter.CTkCheckBox(download_frame, text="Save data to CSV file",variable=save_csv_var, command=check_download_options)
download2csv.pack(padx=10, pady=10)

download2png = customtkinter.CTkCheckBox(download_frame, text="Plot readings and save to PNG", variable=save_png_var,  command=check_download_options)
download2png.pack(padx=10, pady=10)

plot_title = customtkinter.CTkEntry(download_frame, placeholder_text="Enter plot title", width=500)
plot_title.pack(padx=10, pady=10)
plot_title.configure(state="disabled")

download_button = customtkinter.CTkButton(download_frame, text="Download", fg_color='green', state="disabled", command=download_logs)
download_button.pack(padx=10, pady=10)

# Create a fixed-size buffer filled with None so the graph starts "empty" on the left
readings_buffer = [None] * BUFFER_SIZE
time_buffer = [""] * BUFFER_SIZE  # Keeps your timestamps aligned for CSV/logs if needed

# A static list of numbers from 0 to 199 to act as the horizontal screen positions
x_positions = list(range(BUFFER_SIZE))

app.after(1000, update_reading)
app.mainloop()