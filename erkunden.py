import asyncio
from bleak import BleakClient

ADRESSE = "FF:FF:92:10:84:97"  # Dein Preisschild

async def erkunde():
    print(f"Verbinde mit {ADRESSE}...\n")
    
    async with BleakClient(ADRESSE) as client:
        print(f"Verbunden: {client.is_connected}\n")
        
        for service in client.services:
            print(f"SERVICE: {service.uuid}")
            print(f"         {service.description}")
            
            for char in service.characteristics:
                print(f"  CHAR:  {char.uuid}")
                print(f"         {char.description}")
                print(f"         Eigenschaften: {', '.join(char.properties)}")
            print()

asyncio.run(erkunde())