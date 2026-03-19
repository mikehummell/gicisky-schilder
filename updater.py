from bitmap import Bitmap
import asyncio
from typing import Optional, List

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic, uuids
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from enum import Enum


import struct
import sys

DISCOVERY_TIMEOUT_SEC=30
CONNECT_TIMEOUT_SEC=60
COMPANY_IDENTIFIER=20563
FILTER_PRIMARY_SERVICE_UUID="0000fef0-0000-1000-8000-00805f9b34fb"

class Resolution(Enum):
    LCD_212x104_PIXELS = (0, 212, 104, "212x104")
    LCD_296x128_PIXELS = (1, 296, 128, "296x128")
    LCD_400x300_PIXELS = (2, 400, 300, "400x300")
    LCD_640x384_PIXELS = (3, 640, 384, "640x384")
    LCD_960x640_PIXELS = (4, 960, 640, "960x640")
    LCD_250x132_PIXELS = (5, 250, 132, "250x132")
    LCD_196x96_PIXELS = (6, 196, 96, "196x96")
    LCD_640x480_PIXELS = (7, 640, 480, "640x480")
    LCD_250x122_PIXELS = (8, 250, 122, "250x122")
    LCD_800x480_PIXELS = (9, 800, 480, "800x480")
    LCD_280x480_PIXELS = (10, 280, 480, "280x480")
    LCD_1360X480_PIXELS = (11, 1360, 480, "1360x480")
    LCD_168x384_PIXELS = (12, 168, 384, "168x384")
    LCD_210x480_PIXELS = (13, 210, 480, "210x480")
    LCD_1024x576_PIXELS = (14, 1024, 576, "1024x576")
    LCD_384x168_PIXELS = (15, 384, 168, "384x168")
    LCD_480x210_PIXELS = (16, 480, 210, "480x210")
    LCD_240x416_PIXELS = (17, 240, 416, "240x416")

    def __init__(self, index, width, height, description):
        self.index = index
        self.width = width
        self.height = height
        self.description = description

    def __str__(self):
        return self.description

    @classmethod
    def map(cls, tag_type: int):
        index = (tag_type >> 5) & 63
        for res in cls:
            if res.index == index:
                return res
        raise ValueError(f"No Resolution found for index {tag_type}")


class Technology(Enum):
        TFT = (0, "TFT")
        EPA = (1, "EPA")
        EPA_1 = (2, "EPA_1")
        EPA_2 = (3, "桌牌")

        def __init__(self, index, description):
            self.index = index
            self.description = description

        def __str__(self):
            return self.description

        @classmethod
        def map(cls, tag_type: int):
            index = (tag_type >> 3) & 3
            for res in cls:
                if res.index == index:
                    return res
            raise ValueError(f"No Technology found for index {tag_type}")

class Color(Enum):
    BLANK_WHITE = (0, "blank/white")
    BLANK_WHITE_RED = (1, "blank/white/red")
    BLANK_WHITE_YELLOW = (2, "blank/white/yellow")
    BLANK_WHITE_RED_YELLOW = (3, "blank/white/red/yellow")
    BLANK_WHITE_RED_GREEN_BLUE_YELLOW_ORANGE = (4, "blank/white/red/green/blue/yellow/orange")
    BLANK_WHITE_RED_GREEN_BLUE_YELLOW_ORANGE_P = (5, "blank/white/red/green/blue/yellow/orange/P")
    BLANK_WHITE_RED_GREEN_BLUE_YELLOW = (6, "blank/white/red/green/blue/yellow")

    def __init__(self, index, description):
        self.index = index
        self.description = description

    def __str__(self):
        return self.description

    @classmethod
    def map(cls, tag_type: int):
        index = ((tag_type >> 1) & 3) + ((tag_type >> 10) & 12)
        for res in cls:
            if res.index == index:
                return res
        raise ValueError(f"No Color found for index {tag_type}")

class MirrorMode(Enum):
    """
    likely the e-ink switching technology
    double mirror is inverting the colors twice, to reduce ghosting of previous image
    """
    SingleMirror = (0, "SingleMirror") # java enums start with 0
    DoubleMirror = (1, "DoubleMirror")

    def __init__(self, index, description):
        self.index = index
        self.description = description

    def __str__(self):
        return self.description

    @classmethod
    def map(cls, tag_type: int):
        index = tag_type & 1
        for res in cls:
            if res.index == index:
                return res
        raise ValueError(f"No MirrorMode found for index {tag_type}")


class BleDeviceContext:
    def __init__(self: "BleDeviceContext", device: BLEDevice, advertisement_data: AdvertisementData):
        self._device = device
        self._advertisement_data = advertisement_data

    @property
    def device(self) -> BLEDevice:
        return self._device

    @property
    def advertisement_data(self) -> AdvertisementData:
        return self._advertisement_data


class EinkDevice:
    PRIMARY_SERVICE_UUID=0xfef0
    CONFIG_CHARACTERISTIC_UUID=0xfef1
    DATA_CHARACTERISTIC_UUID=0xfef2

    def __init__(self: "EinkDevice", device: BLEDevice, manufacturer_data: bytes):
        self._notification_queue = asyncio.Queue(maxsize=1)

        self._config_characteristic = None
        #self._notify_characteristic = None
        self._data_characteristic = None

        self._tag_type = self._extract_hardware_type(manufacturer_data)
        self._hardware_version = self._extract_hardware_version(manufacturer_data)
        self._software_version = self._extract_software_version(manufacturer_data)
        self._power_level = self._extract_power_level(manufacturer_data)
        print(f"tag_type: {hex(self._tag_type)}")
        print(f"hardware_version: {self._hardware_version}")
        print(f"software_version: {self._software_version}")
        print(f"power_level: {self._power_level}")

        print(f"resolution: {Resolution.map(self._tag_type)}")
        print(f"technology: {Technology.map(self._tag_type)}")
        print(f"color: {Color.map(self._tag_type)}")
        print(f"mirror: {MirrorMode.map(self._tag_type)}")

        self._ble_client = BleakClient(device, timeout=CONNECT_TIMEOUT_SEC)


    async def _load_characteristics(self: "EinkDevice"):
        found_primary_service = False
        for handke, gatt_service in self._ble_client.services.services.items():
            if uuids.normalize_uuid_16(self.PRIMARY_SERVICE_UUID) == gatt_service.uuid:
                found_primary_service = True
                for characteristic in gatt_service.characteristics:
                    if uuids.normalize_uuid_16(self.CONFIG_CHARACTERISTIC_UUID) == characteristic.uuid:
                        self._config_characteristic = characteristic
                    elif uuids.normalize_uuid_16(self.DATA_CHARACTERISTIC_UUID) == characteristic.uuid:
                        self._data_characteristic = characteristic
            if found_primary_service:
                break

        if not found_primary_service:
            raise Exception(f"Necessary primary service {uuids.normalize_uuid_16(self.PRIMARY_SERVICE_UUID)} not found!")

        if not self._config_characteristic:
            raise Exception(f"Necessary characteristic {uuids.normalize_uuid_16(self.CONFIG_CHARACTERISTIC_UUID)} not found!")

        if not self._data_characteristic:
            raise Exception(f"Necessary characteristic {uuids.normalize_uuid_16(self.DATA_CHARACTERISTIC_UUID)} not found!")


    async def _notification_callback(self: "EinkDevice", sender: BleakGATTCharacteristic, data: bytes):
        await self._notification_queue.put(data)


    async def _send_block_size_request(self: "EinkDevice") -> int:
        cmd = 0x01.to_bytes(1, 'little')
        print(f"request: {cmd.hex()}")
        await self._ble_client.write_gatt_char(self._config_characteristic, cmd, response=False)
        data = await self._notification_queue.get()
        print(f"response: {data.hex()}")
        if len(data) == 3 and data[0] == 0x01:
            return (data[2] & 0xff << 8) & 0xff00 | (data[1] & 0xff)
        else:
            raise Exception(f"Expected block size, got {data.hex()}")


    async def _send_enable_screen_update_command(self: "EinkDevice", total_size: int) -> bool:
        cmd = 0x02.to_bytes(1, 'little') + struct.pack("<I", total_size) + 0x01.to_bytes(1, 'little')
        print(f"request: {cmd.hex()}")
        await self._ble_client.write_gatt_char(self._config_characteristic, cmd, response=False)
        data = await self._notification_queue.get()
        print(f"response: {data.hex()}")
        if len(data) == 3 and data[0] == 0x02 and data[1] == 0:
            return True

        return False


    async def _send_start_process_command(self: "EinkDevice") -> int:
        cmd = 0x03.to_bytes(1, 'little')
        print(f"request: {cmd.hex()}")
        #ClientGotEnableUpdateScreenResponse
        await self._ble_client.write_gatt_char(self._config_characteristic, cmd, response=False)
        data = await self._notification_queue.get()
        print(f"response: {data.hex()}")
        if len(data) == 6 and data[0] == 0x05 and data[5] == 0:
            return struct.unpack('<I', data[1:5])[0]

        raise Exception(f"Expected start at block number, got {data.hex()}")


    async def _transfer_bitmap_blocks(self: "EinkDevice", bitmap: Bitmap, block_size: int) -> bool:
        total_size = bitmap.size
        curr_pos = 0
        block_number = 0
        payload_size = block_size - 4 # block number has 4 bytes

        print(f"total_size: {total_size}")
        print(f"payload_size: {payload_size}")

        while curr_pos < (total_size - 1):
            print(f"curr_pos: {curr_pos}")
            print(f"block_number: {block_number}")

            bitmap_block = []
            block_len = 0
            if (total_size - curr_pos) >= payload_size:
                block_len = payload_size
                bitmap_block = bitmap.bitmap[curr_pos:(curr_pos + payload_size)]
            else:
                block_len = total_size - curr_pos
                bitmap_block = bitmap.bitmap[curr_pos:(curr_pos + block_len)]

            send_block = struct.pack("<I", block_number) + bitmap_block
            #print(send_block.hex())

            curr_pos += block_len
            block_number += 1

            await self._ble_client.write_gatt_char(self._data_characteristic, send_block, response=False)
            await asyncio.sleep(0.01)

        data = await self._notification_queue.get()
        if len(data) == 6 and data[0] == 0x05 and data[1] == 0x08:
            return True

        return False

    async def send_bitmap(self: "EinkDevice", bitmap: Bitmap):
        await self._ble_client.connect()
        if not self._ble_client.is_connected:
            raise Exception("Cannot connect to BLE device!")

        await self._load_characteristics()

        print("Start notification listener...")
        await self._ble_client.start_notify(self._config_characteristic, self._notification_callback)
        await asyncio.sleep(0.5)

        block_size = await self._send_block_size_request()
        print(f"Received bitmap block size: {block_size}")
        await asyncio.sleep(0.2)
        await self._send_enable_screen_update_command(bitmap.size)
        await asyncio.sleep(0.2)
        start_block_number = await self._send_start_process_command()
        if start_block_number != 0:
            raise Exception(f"Expected start at block 0, got {start_block_number}")

        if not await self._transfer_bitmap_blocks(bitmap, block_size):
            raise Exception(f"Sending bitmap failed!")

    def _decode_hardware_type(self: "EinkDevice", b2, b3) -> int:
        """
            from sources/com/picksmart/BluetoothleTransfer/e.java
            public static int a(byte b2, byte b3)
        """
        return (((b2 & 0xff) << 8) & 0xFF00) | (b3 & 0xff)


    def _extract_hardware_type(self: "EinkDevice", manufacturer_data: bytes) -> int:
        """ from m5020d() """
        if len(manufacturer_data) > 4:
            return self._decode_hardware_type(manufacturer_data[4], manufacturer_data[0])
        else:
            return manufacturer_data[0] & 0xff


    def _extract_hardware_version(self: "EinkDevice", manufacturer_data: bytes) -> int:
        """ from m5021e() """
        if len(manufacturer_data) > 3:
            return manufacturer_data[3] & 0xff
        return 1


    def _extract_software_version(self: "EinkDevice", manufacturer_data: bytes) -> int:
        """ from m5025i() """
        if len(manufacturer_data) > 2:
            return manufacturer_data[2] & 0xff
        return 1


    def _extract_power_level(self: "EinkDevice", manufacturer_data: bytes) -> int:
        """ from m5023g() """
        if len(manufacturer_data) > 1:
            return manufacturer_data[1] & 0xff
        return 1


# def find_my_uuid(ble_devices: List[BleDeviceContext]) -> BleDeviceContext | None:
#     for device in ble_devices:
#         if FILTER_PRIMARY_SERVICE_UUID in device.advertisement_data.service_uuids:
#             return device

#     return None

def find_my_uuid(ble_devices: List[BleDeviceContext], target_name: str = None) -> BleDeviceContext | None:
    for device in ble_devices:
        if FILTER_PRIMARY_SERVICE_UUID in device.advertisement_data.service_uuids:
            if target_name is None or device.advertisement_data.local_name == target_name:
                return device
    return None


def restructure_discovered_devices(devices: dict) -> List[BleDeviceContext]:
    """ Make the dict of tuples to a list of dicts"""

    device_list = []
    for address, device_advertisement in devices.items():
        device, advertisement = device_advertisement
        device_list.append(BleDeviceContext(device, advertisement))

    return device_list


async def main():
    bitmap = Bitmap('test.png')
    print(f"Bitmap loaded: {bitmap.width}x{bitmap.height}, {bitmap.size} bytes")

    scanner = BleakScanner()
    print("Discovering BLE devices...")
    devices = await scanner.discover(timeout=20, return_adv=True)
    devices = restructure_discovered_devices(devices)

    device = find_my_uuid(devices, target_name="NEMR61623009")
    if not device:
        raise Exception(f"Found no compatible devices")
    # device = find_my_uuid(devices)
    # if not device:
    #     raise Exception(f"Found no compatible devices")

    print(f"Discovered device: {device.advertisement_data.local_name}")
    manufacturer_data = None
    for company_identifier, data in device.advertisement_data.manufacturer_data.items():
        print(f"{company_identifier} -> {hex(company_identifier)}")
        if company_identifier == COMPANY_IDENTIFIER:
            manufacturer_data = data

    if not manufacturer_data:
        raise Exception(f"Discovered device has incompatible company identifier (expected {hex(COMPANY_IDENTIFIER)})")


    eink_device = EinkDevice(device.device, manufacturer_data)
    await eink_device.send_bitmap(bitmap)

if __name__ == "__main__":
    asyncio.run(main())
