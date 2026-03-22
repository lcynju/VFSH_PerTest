import sys
import time
from random import random

import serial
import serial.tools.list_ports
import threading
from utils.system_logger import get_logger
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt5.QtCore import pyqtSignal, QObject

class SerialReader(QObject):
    data_received = pyqtSignal(str)

    def __init__(self, port='COM7', baudrate=9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self._running = True  # 程序启动就开始运行
        self._sending_data = False  # 控制是否发送数据的变量
        self.thread = None
        self._test_thread_started = False
        # 程序启动就开始读取数据
        # TODO：正式时启动下面的解除
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            # Test用self.test函数
            self.thread = threading.Thread(target=self.test)
            #self.thread = threading.Thread(target=self.read_data)
            self.thread.daemon = True
            self.thread.start()
        except serial.SerialException as e:
            print(e)
            self.data_received.emit(f"[串口错误] {e}")

    def start(self):
        # 只修改控制发送数据的变量，不重新启动线程
        self._sending_data = True
        # TODO:正式时删去
        self._test_thread_started = True
        # print("开始发送数据")

    def stop(self):
        # 只修改控制发送数据的变量，不停止线程
        self._sending_data = False
        # TODO:正式时删去
        self._test_thread_started = False
        # print("停止发送数据")

    def stop_test_thread(self):
        """停止测试线程"""
        if self._test_thread_started:
            # print("正在停止测试线程...")
            self._running = False  # 设置停止标志
            
            # 等待线程结束
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)  # 等待最多2秒
                if self.thread.is_alive():
                    # pass
                    get_logger().warning("测试线程未能正常停止")
                else:
                    # pass
                    get_logger().info("测试线程已成功停止")
            
            self._test_thread_started = False
            self._running = True  # 重置运行标志，以便下次启动

    def start_test_thread(self):
        """手动启动测试线程（仅在用户点击开始按钮时调用）"""
        if not self._test_thread_started:
            try:
                # 测试条件下是test函数，正式条件下是read_data函数
                self.thread = threading.Thread(target=self.test)
                self.thread.daemon = True
                self.thread.start()
                self._test_thread_started = True
                # print("测试线程已启动")
            except Exception as e:
                # print(f"启动测试线程时出错: {e}")
                self.data_received.emit(f"[测试线程错误] {e}")

    def read_data(self):
        print("开始读取数据")
        buffer = ""
        try:
            while self._running:
                try:
                    if self.ser and self.ser.is_open:
                        bytes_to_read = self.ser.in_waiting
                        if bytes_to_read > 0:
                            raw_data = self.ser.read(bytes_to_read).decode(errors='ignore')
                            buffer += raw_data

                            while ':' in buffer:
                                start_index = buffer.find(':')
                                next_start_index = buffer.find(':', start_index + 1)

                                if next_start_index == -1:
                                    break

                                one_record = buffer[start_index:next_start_index]
                                buffer = buffer[next_start_index:]

                                # ----------------- 解析报文 -----------------
                                try:
                                    hex_str = one_record[1:]  # 去掉前导冒号
                                    data_bytes = bytes.fromhex(hex_str)
                                    # print(data_bytes.hex())
                                    # 这里根据你前面的结构，3个寄存器数据从第 7 字节开始
                                    # [功能码02 10] [寄存器地址00 00] [寄存器数量00 03] [字节数06]
                                    # => 实际数据部分从索引 7 开始，共 6 个字节（3*2）
                                    if len(data_bytes) >= 13:  # 确保长度够
                                        force = int.from_bytes(data_bytes[7:9], byteorder="big", signed=False)
                                        distance = int.from_bytes(data_bytes[9:11], byteorder="big", signed=False)
                                        status = int.from_bytes(data_bytes[11:13], byteorder="big", signed=False)

                                        parsed = {
                                            "raw": one_record,
                                            "distance": distance,
                                            "force": force,
                                            "status": status,
                                        }
                                        # print(parsed)
                                        data = f"({force * 9.8 / 1000}, {distance}, {status})"
                                        with open("data.txt", "a") as f:
                                            f.write(data + "\n")
                                            
                                        # 无条件发送数据，确保data_display能接收到
                                        self.data_received.emit(data)
                                    else:
                                        # pass
                                        get_logger().warning("无效报文: %s", one_record)

                                except Exception as e:
                                    # print(f"解析错误: {e}, 报文={one_record}")
                                    # 无条件发送错误信息，确保data_display能接收到
                                    self.data_received.emit(one_record)
                except Exception as e:
                    # 无条件发送错误信息，确保data_display能接收到
                    self.data_received.emit(f"[读取错误] {e}")
                    # 不中断循环，继续尝试读取数据
                    time.sleep(0.1)
        finally:
            # 线程退出时关闭串口，以便下次开始能重新打开
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None



    # 测试函数，生成随机数据，逻辑与read_data保持一致
    def test(self):
        from random import uniform
        y = 0
        i = 0
        # print("开始测试模式，生成随机数据")
        while self._running:
            try:
                if i <= 800:
                    y += 1
                    x = uniform(23.2, 60.6) 
                
                data = f"({x}, {y}, 18432)"
                print("send data:", data, self._sending_data)
                self.data_received.emit(data)
                    
                i += 1
                time.sleep(0.1)
            except Exception as e:
                # print(f"测试模式错误: {e}")
                # 只有当_sending_data为True时才发送错误信息
                if self._sending_data:
                    self.data_received.emit(f"[测试错误] {e}")
                # 不中断循环，继续尝试
                time.sleep(0.1)




