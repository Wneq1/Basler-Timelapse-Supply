# Basler Time-Lapse with Power Supply Control

Python tools for long-running image acquisition with a Basler USB3 Vision camera
synchronized with a Keysight E36313A programmable power supply.

## Scripts

### `timelapse_supply.py` — 24-hour voltage time-lapse
Runs an automated experiment for 24 hours from start:

- **Channel 3** is held at a constant **9 V** for the whole run.
- **Channel 2** is set to a random voltage (0–20 V) every **60 s**.
- One second after each voltage change, the camera takes a photo, saved as a PNG
  at the camera's full bit depth.
- File names contain the voltage read back from the supply, the time and a
  sequence number, e.g. `17.86V_132018_0001.png`.
- The console shows the photo number, timestamp and voltage for every frame.

**Safety handling**
- `Ctrl+C` turns off both channels (CH2 and CH3).
- On any error, both channels are switched off and two emergency frames are
  saved (the current one and one more after the interval).
- After a normal 24 h finish, only CH2 is switched off; CH3 stays at 9 V.

### `continuous_camera_pylon.py` — live preview
Opens a live camera view, always showing the newest frame.

| Key | Action |
|-----|--------|
| `s` | save the current frame as JPG (quality 95) to `zdjecia/` |
| `q` | quit (closing the window also works) |

### `basler_camera.py` — shared camera helper
Finds the camera by serial number, grabs single frames, sets exposure and gain,
and converts frames to 8 bits for preview and JPG. Both scripts above need it.

## Requirements

- Windows, **Python 3.14 (64-bit)**
- **Basler pylon Camera Software Suite** with the USB3 Vision driver.
  The camera must use the Basler driver, not NI-IMAQdx.
- **NI-VISA** or **Keysight IO Libraries Suite**, for the power supply over LAN
- The camera connected to a **USB 3.0** port

```bash
python -m pip install -r requirements.txt
```

## Configuration

| Setting | File | Default |
|---------|------|---------|
| `SERIAL` (camera serial number, `None` = first camera found) | `basler_camera.py` | `"40026524"` |
| `SUPPLY_ADDRESS` | `timelapse_supply.py` | `TCPIP0::192.168.98.48::inst0::INSTR` |
| `CHANNEL` / `MIN_VOLTAGE` / `MAX_VOLTAGE` | `timelapse_supply.py` | `CH2`, 0–20 V |
| `CONST_CHANNEL` / `CONST_VOLTAGE` | `timelapse_supply.py` | `CH3`, 9 V |
| `INTERVAL` | `timelapse_supply.py` | 60 s |
| `DURATION` | `timelapse_supply.py` | 24 h |

To list the connected cameras and their serial numbers, run `python list_cameras.py`.

## Usage

```bash
python continuous_camera_pylon.py   # check framing and focus first
python timelapse_supply.py          # start the 24 h measurement
```

Photos are saved to the `zdjecia/` folder.
