import sys
from PyQt5.QtWidgets import QApplication
from app import MainWindow
from utils.style import init_fonts


def main():
    # 创建应用实例
    app = QApplication(sys.argv)

    # 初始化字体
    init_fonts(app)

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()