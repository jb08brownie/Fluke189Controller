# Fluke189Controller
A Python desktop application for interfacing with the Fluke 189 digital multimeter using its infrared serial port. It provides a live meter display, real-time trend plotting, CSV data logging, and the ability to download and export the meter's internal memory log — all through a modern, custom GUI built with CustomTkinter.

This project grew out of reverse-engineering the Fluke 189's serial protocol, since Fluke's own software (FlukeView) is dated and expensive. The full writeup of how the protocol was reverse-engineered, and how the IR interface cable was built, is on my blog [here](https://jonathanbrown95.wixsite.com/jonny-brown/post/fluke-189-ir-cable-software).

<img width="602" height="473" alt="Screenshot 2026-07-18 104626" src="https://github.com/user-attachments/assets/25c9ed86-cd62-4d21-b54b-cad0fdbb9baf" />

## Features


- **Live meter display** — mirrors the Fluke 189's primary and secondary readings, units, and active mode indicators (HOLD, AutoHOLD, MIN/MAX, AVG, REL/REL%, LOG) in a large, easy-to-read display.
- **Front-panel button control** — send the meter's front-panel commands (HOLD, REL Δ, MIN/MAX, RANGE, Hz/%/ms, and the up/down range buttons) directly from the app.
- **Live trend plotting** — a rolling, fixed-width graph of the last 100 readings, automatically re-scaled and re-labelled when the meter's function or range changes.
- **Live CSV logging** — log readings to a CSV file in real time while trend plotting, with a running timestamp column.
- **Meter memory log download** — pull the readings stored in the meter's internal memory and export them as:
  - a CSV file
  - a PNG plot, with an optional custom title and a choice of an elapsed-time or clock-time x-axis.
- **Automatic unit and mode decoding** — decodes the Fluke 189's binary status bytes into the correct measurement mode, unit, and prefix (V, mV, Ω, Hz, dB, AC/DC, etc.), including special cases like duty cycle and pulse width.
- **Serial port management** — auto-detects available COM ports, with a one-click refresh, and confirms the meter's identity (model, firmware, serial number) on connect.
- **Packaged as a standalone Windows executable** - via PyInstaller, so it can be run without a Python environment installed.

## Hardware requirement: IR serial lead

The Fluke 189 communicates over an infrared serial interface on the top of the meter. To use this software, you need an IR-to-serial interface cable that attaches onto the meter's IR port.

There are two options:

1. **Buy one.** Fluke sells an official IR interface cable (sold as part of the FlukeView software/cable kits).
2. **Build one.** I built my own from scratch — an FT232R-based USB-to-serial converter driving an IR LED (TSAL6400) through a transistor stage (2N3906), with a photo-transistor (BPV11) for the return path, all housed in a 3D-printed enclosure. Full schematic, parts list, and build notes are in my blog post [here](https://jonathanbrown95.wixsite.com/jonny-brown/post/fluke-189-ir-cable-software).

## Requirements

- Python 3.9+
- Dependencies:

  customtkinter
  pyserial
  matplotlib
  pillow
  pyglet

- An IR serial interface cable (see above)
- Windows, macOS, or Linux (the packaged .exe build is Windows-only; running from source works cross-platform, though the app has primarily been tested on Windows)


## Installation

**Option 1: Run from source**

```bash
git clone [https://github.com/<your-username>/<your-repo>](https://github.com/jb08brownie/Fluke189Controller).git
cd <your-repo>
pip install -r requirements.txt
python fluke189_controller.py
```

**Option 2: Download the packaged executable**

Grab the latest .exe from the Releases page — no Python installation required. (Windows only.)

## Usage

1. Plug in your IR serial cable and point it at the Fluke 189's IR window on the back of the meter.
2. Launch the app, select the correct COM port, and click Connect. On success, the meter's model, firmware version, and serial number will be displayed.
3. Use the Trend Plot tab to view live readings, click Run to start plotting, and optionally enable CSV logging alongside it.
4. Use the Download tab to pull the meter's stored memory log and export it as CSV and/or a plotted PNG.
5. Use the button panel to remotely trigger HOLD, REL, MIN/MAX, RANGE, and other front-panel functions.

**Building the executable yourself**

The packaged .exe is built with PyInstaller. If you want to rebuild it after making changes:

```bash
git clone https://github.com/jb08brownie/Fluke189Controller.git
cd Fluke189Controller
pip install -r requirements.txt
python fluke189_controller.py
```

The resulting executable will be in the dist/ folder. The --add-data flags are required so the app icon and the DSEG7 display font are bundled correctly, matching the resource_path() lookup used at runtime.

## Background

The Fluke 189's serial protocol isn't publicly documented by Fluke. This app is the result of systematically logging and decoding the meter's QD 0 (live reading) and QD 2 (memory dump) binary responses to work out the mode, range, unit, and value encoding used internally. If you're interested in the reverse-engineering process itself, or in building your own IR interface cable, see the full writeup [here](https://jonathanbrown95.wixsite.com/jonny-brown/post/fluke-189-ir-cable-software).

## Disclaimer

This is an independent, community project and is not affiliated with, endorsed by, or supported by Fluke Corporation. Use at your own risk.

## License

MIT: https://rem.mit-license.org
