from PyQt5.QtGui import QFont

def init_fonts(app):
    """初始化字体设置"""
    font = QFont()
    font.setFamily("Microsoft YaHei")
    app.setFont(font)