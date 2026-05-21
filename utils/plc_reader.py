"""通过网线（Modbus TCP）从 PLC 读取两个模拟量输入通道的原始数据。"""

import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal
from pymodbus.client import ModbusTcpClient

from utils.system_logger import get_logger

# -------------------- 全局配置（按现场 PLC 修改）--------------------
PLC_IP = "192.168.0.10"
PLC_PORT = 502
MODBUS_UNIT_ID = 1
# 模拟量输入通道1、通道2 的寄存器地址（与 PLC 手册一致，一般为 0 起始）
CHANNEL_1_ADDRESS = 0
CHANNEL_2_ADDRESS = 1
# "input"：功能码 04（输入寄存器）； "holding"：功能码 03（保持寄存器）
REGISTER_TYPE = "input"
READ_INTERVAL_SEC = 0.1


class PlcReader(QObject):
    """后台线程轮询 PLC，通过 data_received 上报两路模拟量原始值。"""

    data_received = pyqtSignal(str)

    def __init__(
        self,
        ip=None,
        port=None,
        unit_id=None,
        channel_1_address=None,
        channel_2_address=None,
        register_type=None,
    ):
        super().__init__()
        self.ip = ip if ip is not None else PLC_IP
        self.port = port if port is not None else PLC_PORT
        self.unit_id = unit_id if unit_id is not None else MODBUS_UNIT_ID
        self.channel_1_address = (
            channel_1_address if channel_1_address is not None else CHANNEL_1_ADDRESS
        )
        self.channel_2_address = (
            channel_2_address if channel_2_address is not None else CHANNEL_2_ADDRESS
        )
        self.register_type = register_type if register_type is not None else REGISTER_TYPE

        self._client = None
        self._running = True
        self._sending_data = False
        self.thread = None

        self.thread = threading.Thread(target=self.read_data)
        self.thread.daemon = True
        self.thread.start()

    def start(self):
        self._sending_data = True

    def stop(self):
        self._sending_data = False

    def _connect(self):
        if self._client is not None and self._client.connected:
            return True
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = ModbusTcpClient(host=self.ip, port=self.port)
        if not self._client.connect():
            return False
        return True

    def _read_register(self, address):
        if self.register_type == "holding":
            return self._client.read_holding_registers(
                address, count=1, device_id=self.unit_id
            )
        return self._client.read_input_registers(
            address, count=1, device_id=self.unit_id
        )

    def read_data(self):
        while self._running:
            try:
                if not self._connect():
                    self.data_received.emit(f"[PLC连接错误] 无法连接 {self.ip}:{self.port}")
                    time.sleep(1.0)
                    continue

                r1 = self._read_register(self.channel_1_address)
                r2 = self._read_register(self.channel_2_address)

                if r1.isError():
                    self.data_received.emit(
                        f"[PLC读取错误] 通道1 地址={self.channel_1_address}: {r1}"
                    )
                    time.sleep(READ_INTERVAL_SEC)
                    continue
                if r2.isError():
                    self.data_received.emit(
                        f"[PLC读取错误] 通道2 地址={self.channel_2_address}: {r2}"
                    )
                    time.sleep(READ_INTERVAL_SEC)
                    continue

                ch1_raw = r1.registers[0]
                ch2_raw = r2.registers[0]
                data = f"({ch1_raw}, {ch2_raw})"
                self.data_received.emit(data)

            except Exception as e:
                get_logger().warning("PLC 读取异常: %s", e)
                self.data_received.emit(f"[PLC读取错误] {e}")
                if self._client is not None:
                    try:
                        self._client.close()
                    except Exception:
                        pass
                    self._client = None
                time.sleep(0.5)
            else:
                time.sleep(READ_INTERVAL_SEC)

        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def close(self):
        self._running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
