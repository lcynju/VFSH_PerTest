"""通过网线（Modbus TCP）从汇川 PLC 读取两个模拟量输入通道的原始数据。

汇川 H5U / H3U / AM 等系列在 AutoShop 中于以太网口启用「Modbus TCP 从站」后，
上位机使用 Modbus TCP 连接（默认端口 502）。

说明（汇川 H5U Modbus 协议手册）：
- 字元件 D0–D7999 的 Modbus 地址 = D 编号（D0→0，D100→100），功能码 03/04 均可读。
- IW（模拟量输入）不能由 Modbus 直接访问，须在 PLC 程序里将 AI 值写入 D 区，例如：
    D100 := IW0;   // 通道1
    D101 := IW2;   // 通道2
  再将 CHANNEL_*_ADDRESS 设为对应 D 编号。
- pymodbus 请求地址为 0 起始，与 D 编号一致，无需 +40001 偏移。
"""

import os
import sys

# 支持 python utils/plc_reader.py 直接运行
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal
from pymodbus.client import ModbusTcpClient

from utils.system_logger import get_logger

# -------------------- 汇川 PLC 全局配置（按现场修改）--------------------
PLC_IP = "192.168.1.88"
PLC_PORT = 502
MODBUS_UNIT_ID = 1

# 两路模拟量在 PLC 中映射到的 D 寄存器编号（Modbus 字地址与 D 号相同）
# 默认 D100、D101：请在 AutoShop 中将 IW0/IW2 等写入这两个 D
CHANNEL_1_ADDRESS = 100
CHANNEL_2_ADDRESS = 101

# 汇川 D/R 区使用保持寄存器读法（功能码 03；04 在 H5U 从站上等效）
REGISTER_TYPE = "holding"
READ_INTERVAL_SEC = 0.1


class PlcReader(QObject):
    """后台线程轮询汇川 PLC，通过 data_received 上报两路模拟量原始字值。"""

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

    def _read_registers(self, address, count):
        if self.register_type == "holding":
            return self._client.read_holding_registers(
                address, count=count, device_id=self.unit_id
            )
        return self._client.read_input_registers(
            address, count=count, device_id=self.unit_id
        )

    def _read_both_channels(self):
        """连续 D 地址时一次读 2 字，减少汇川 PLC 通信次数。"""
        a1, a2 = self.channel_1_address, self.channel_2_address
        if a2 == a1 + 1:
            result = self._read_registers(a1, 2)
            if result.isError():
                return result, None
            return None, (result.registers[0], result.registers[1])

        r1 = self._read_registers(a1, 1)
        if r1.isError():
            return r1, None
        r2 = self._read_registers(a2, 1)
        if r2.isError():
            return r2, None
        return None, (r1.registers[0], r2.registers[0])

    def read_data(self):
        while self._running:
            try:
                if not self._connect():
                    self.data_received.emit(
                        f"[汇川PLC连接错误] 无法连接 {self.ip}:{self.port}"
                    )
                    time.sleep(1.0)
                    continue

                err, values = self._read_both_channels()
                if err is not None:
                    self.data_received.emit(f"[汇川PLC读取错误] {err}")
                    time.sleep(READ_INTERVAL_SEC)
                    continue

                ch1_raw, ch2_raw = values
                data = f"({ch1_raw}, {ch2_raw})"
                self.data_received.emit(data)

            except Exception as e:
                get_logger().warning("汇川 PLC 读取异常: %s", e)
                self.data_received.emit(f"[汇川PLC读取错误] {e}")
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


def read_channels_once(
    ip=None,
    port=None,
    unit_id=None,
    channel_1_address=None,
    channel_2_address=None,
    register_type=None,
):
    """同步读取一次两路通道，不依赖 Qt 线程。返回 (成功与否, 说明, (ch1, ch2) 或 None)。"""
    ip = ip if ip is not None else PLC_IP
    port = port if port is not None else PLC_PORT
    unit_id = unit_id if unit_id is not None else MODBUS_UNIT_ID
    channel_1_address = (
        channel_1_address if channel_1_address is not None else CHANNEL_1_ADDRESS
    )
    channel_2_address = (
        channel_2_address if channel_2_address is not None else CHANNEL_2_ADDRESS
    )
    register_type = register_type if register_type is not None else REGISTER_TYPE

    client = ModbusTcpClient(host=ip, port=port)
    try:
        if not client.connect():
            return False, f"无法连接 {ip}:{port}", None

        def _read(address, count):
            if register_type == "holding":
                return client.read_holding_registers(
                    address, count=count, device_id=unit_id
                )
            return client.read_input_registers(
                address, count=count, device_id=unit_id
            )

        a1, a2 = channel_1_address, channel_2_address
        if a2 == a1 + 1:
            result = _read(a1, 2)
            if result.isError():
                return False, str(result), None
            ch1_raw, ch2_raw = result.registers[0], result.registers[1]
        else:
            r1 = _read(a1, 1)
            if r1.isError():
                return False, f"D{a1} 读取失败: {r1}", None
            r2 = _read(a2, 1)
            if r2.isError():
                return False, f"D{a2} 读取失败: {r2}", None
            ch1_raw, ch2_raw = r1.registers[0], r2.registers[0]

        return True, "ok", (ch1_raw, ch2_raw)
    except Exception as e:
        return False, str(e), None
    finally:
        try:
            client.close()
        except Exception:
            pass


def main():
    """命令行测试：验证汇川 PLC Modbus TCP 是否能读到两路原始数据。"""
    import argparse
    import sys

    from PyQt5.QtWidgets import QApplication

    parser = argparse.ArgumentParser(description="测试汇川 PLC 网线读取")
    parser.add_argument(
        "--watch",
        type=float,
        default=0,
        metavar="SEC",
        help="持续监听秒数；默认 0 表示只同步读一次",
    )
    args = parser.parse_args()

    print("=== 汇川 PLC 读取测试 ===")
    print(f"IP/端口:     {PLC_IP}:{PLC_PORT}")
    print(f"从站号:      {MODBUS_UNIT_ID}")
    print(f"通道1地址:   D{CHANNEL_1_ADDRESS} (Modbus {CHANNEL_1_ADDRESS})")
    print(f"通道2地址:   D{CHANNEL_2_ADDRESS} (Modbus {CHANNEL_2_ADDRESS})")
    print(f"寄存器类型:  {REGISTER_TYPE}")
    print()

    if args.watch <= 0:
        ok, msg, values = read_channels_once()
        if ok:
            print(f"读取成功: 通道1={values[0]}, 通道2={values[1]}")
            sys.exit(0)
        print(f"读取失败: {msg}")
        sys.exit(1)

    app = QApplication(sys.argv)
    ok_count = 0
    err_count = 0
    deadline = time.time() + args.watch

    def on_data(data):
        nonlocal ok_count, err_count
        if data.startswith("["):
            err_count += 1
            print(f"[错误] {data}")
        else:
            ok_count += 1
            print(f"[数据] {data}")

    reader = PlcReader()
    reader.data_received.connect(on_data)

    print(f"持续监听 {args.watch} 秒（Ctrl+C 可提前结束）...")
    try:
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        reader.close()

    print()
    print(f"统计: 成功 {ok_count} 条, 错误 {err_count} 条")
    if ok_count > 0:
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
