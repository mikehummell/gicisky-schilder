import asyncio
from bleak import BleakScanner

async def scan():
    print("Scanne nach BLE Geräten... (10 Sekunden)\n")
    
    devices_and_adv = await BleakScanner.discover(timeout=10.0, return_adv=True)
    
    for device, adv_data in devices_and_adv.values():
        name = device.name or "(kein Name)"
        rssi = adv_data.rssi
        print(f"Name: {name:<30} Adresse: {device.address}  Signal: {rssi} dBm")

asyncio.run(scan())