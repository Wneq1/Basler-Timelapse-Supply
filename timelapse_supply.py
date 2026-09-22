import basler_camera
from PIL import Image
from datetime import datetime
import os
import time
import pyvisa
import random as rd

number = 1
last_voltage = 0.0
basler = None
supply = None
rm = None

SUPPLY_ADDRESS = "TCPIP0::192.168.98.48::inst0::INSTR"
CHANNEL = "CH2"
CONST_CHANNEL = "CH3"  # kanal ze stalym napieciem przez caly pomiar
CONST_VOLTAGE = 9
FOLDER = "zdjecia"
INTERVAL = 60  # sekundy miedzy zdjeciami
SETTLE_TIME = 1  # sekundy od ustawienia napiecia do zdjecia
MIN_VOLTAGE = 0
MAX_VOLTAGE = 20
DURATION = 24 * 3600  # sekundy - jak dlugo robic zdjecia od startu

def create_folder(folder_name):
    os.makedirs(folder_name, exist_ok=True)

def set_start_parameters(device):

    device_id = device.query("*IDN?").strip()
    print("Połączono z:", device_id)

    device.write("*RST")
    device.write("*CLS")
    device.write("SYST:BEEP")
    device.write(f"INST {CHANNEL}")

def random_voltage(min_val, max_val):
    return rd.randint(min_val * 100, max_val * 100) / 100

def const_channel_on(device):
    device.write(f"INST {CONST_CHANNEL}")
    device.write(f"VOLT {CONST_VOLTAGE}")
    device.write("OUTP ON")
    print(f"Kanał {CONST_CHANNEL} włączony: {CONST_VOLTAGE} V")

    # dalsze komendy VOLT dotycza kanalu ze zmiennym napieciem
    device.write(f"INST {CHANNEL}")

def read_set_voltage(device):
    global last_voltage

    # wartosc ustawiona (nie zmierzona) na wybranym kanale
    last_voltage = float(device.query("VOLT?").strip())
    return last_voltage

def supply_off(device):
    # przerwanie lub blad - wylacza oba kanaly
    ok = True
    # CHANNEL na koncu - zostaje wybrany, wiec VOLT? w klatkach awaryjnych czyta jego napiecie
    for channel in (CONST_CHANNEL, CHANNEL):
        try:
            device.write(f"INST {channel}")
            device.write("OUTP OFF")
            print(f"Kanał {channel} wyłączony")
        except Exception as e:
            print(f"Blad wylaczenia kanalu {channel}:", e)
            ok = False
    return ok

def take_photo(cam, voltage):
    global number

    create_folder(FOLDER)

    teraz = datetime.now()
    czas = teraz.strftime("%H%M%S")
    name = os.path.join(FOLDER, f"{voltage:05.2f}V_{czas}_{number:04d}.png")

    frame = basler_camera.snap(cam)
    image = Image.fromarray(frame)
    image.save(name)

    if not os.path.exists(name):
        raise Exception(f"Nie zapisano pliku {name}")

    print(f"Zdjęcie nr {number} | {teraz:%Y-%m-%d %H:%M:%S} | {voltage:.2f} V | {name}")
    number += 1
    return name

def safe_photo(cam, device):
    # zdjecie awaryjne - nie moze rzucic wyjatku
    try:
        voltage = read_set_voltage(device)
    except Exception as e:
        print("Blad odczytu napiecia, uzywam ostatniego:", e)
        voltage = last_voltage

    try:
        name = take_photo(cam, voltage)
        print("^ klatka awaryjna")
    except Exception as e:
        print("Blad zdjecia awaryjnego:", e)

def emergency_stop(device, cam):
    # blad: wylacz kanal, zapisz biezaca klatke i jeszcze jedna kolejna
    if device is not None:
        supply_off(device)

    if cam is None:
        print("Brak kamery - pomijam klatki awaryjne")
        return

    safe_photo(cam, device)
    time.sleep(INTERVAL)
    safe_photo(cam, device)

def acquire_timelapse(device, camera):
    start = time.monotonic()
    koniec = datetime.fromtimestamp(time.time() + DURATION)
    print(f"Zdjęcie co {INTERVAL} s przez {DURATION / 3600:g} h "
          f"(do {koniec:%Y-%m-%d %H:%M:%S}), Ctrl+C aby zakończyć")

    device.write(f"INST {CHANNEL}")
    device.write("OUTP ON")

    next_shot = start
    while time.monotonic() - start < DURATION:
        device.write(f"VOLT {random_voltage(MIN_VOLTAGE, MAX_VOLTAGE)}")
        time.sleep(SETTLE_TIME)

        # do nazwy wartosc odczytana z zasilacza - potwierdza, ze sie ustawila
        voltage = read_set_voltage(device)
        take_photo(camera, voltage)

        # stały odstęp niezależnie od czasu ustawiania i zapisu zdjęcia
        next_shot += INTERVAL
        time.sleep(max(0, next_shot - time.monotonic()))

    # koniec 24 h: wylacza tylko kanal zmienny, CONST_CHANNEL zostaje wlaczony
    device.write(f"INST {CHANNEL}")
    device.write("OUTP OFF")
    print(f"Koniec pomiaru. Kanał {CHANNEL} wyłączony, {CONST_CHANNEL} nadal {CONST_VOLTAGE} V")

try:
    rm = pyvisa.ResourceManager()
    supply = rm.open_resource(SUPPLY_ADDRESS)
    set_start_parameters(supply)
    const_channel_on(supply)

    basler = basler_camera.open_camera()

    acquire_timelapse(supply, basler)

except KeyboardInterrupt:
    print("STOP")
    # wyjscie bylo wlaczone przez skrypt - nie zostawiamy go pod napieciem
    if supply is not None:
        supply_off(supply)

except Exception as e:
    print("BLAD:", e)
    try:
        emergency_stop(supply, basler)
    except KeyboardInterrupt:
        print("Przerwano zapis klatek awaryjnych")

finally:
    for zamkniecie in (basler.Close if basler else None,
                       supply.close if supply else None,
                       rm.close if rm else None):
        if zamkniecie is not None:
            try:
                zamkniecie()
            except Exception as e:
                print("Blad zamykania:", e)
