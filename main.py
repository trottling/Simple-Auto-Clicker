import ctypes
import os
import sys
import time

import fastrand
from PyQt6 import uic, QtTest
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QApplication
from pynput import mouse
from pynput.mouse import Controller


class User_UI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = None
        self.clicks_count = 0
        self.clicker = None
        self.clicker_work = False
        Load(self)


def Load(self):
    self.ui = uic.loadUi(GetRelPath("form.ui"), self)

    self.ui.sleep_up_slider.valueChanged.connect(lambda: ChangeSlider(self))
    self.ui.sleep_to_slider.valueChanged.connect(lambda: ChangeSlider(self))
    self.ui.start_btn.clicked.connect(lambda: Start(self))

    self.ui.show()


def ChangeSlider(self):
    # Show curr value
    self.ui.sleep_up_lineEdit.setText(str(self.ui.sleep_up_slider.value()))
    self.ui.sleep_to_lineEdit.setText(str(self.ui.sleep_to_slider.value()))
    # Set sliders min and max values
    self.ui.sleep_up_slider.setMaximum(int(self.ui.sleep_to_slider.value()) - 2)
    self.ui.sleep_to_slider.setMinimum(int(self.ui.sleep_up_slider.value()) + 2)
    # Calculate CPS
    self.ui.label_cpm.setText(f"{str(round(float(1000 / ((self.ui.sleep_to_slider.value() + self.ui.sleep_up_slider.value()) / 2)), 3))} CPS")


def Start(self):
    if not self.clicker_work:
        ElemInactive(self)
        self.clicker_work = True
        self.clicker = Clicker(int(self.ui.sleep_up_slider.value()),
                               int(self.ui.sleep_to_slider.value()),
                               int(self.ui.spinBox_cycle_clicks.value()))
        self.clicker.click_sig.connect(lambda: UpdateClicks(self))
        self.clicker.start()
    else:
        self.clicker.stop()
        self.clicker = None
        ElemActive(self)
        self.clicker_work = False


def ElemInactive(self):
    self.ui.sleep_up_lineEdit.setEnabled(False)
    self.ui.sleep_to_lineEdit.setEnabled(False)
    self.ui.sleep_up_slider.setEnabled(False)
    self.ui.sleep_to_slider.setEnabled(False)
    self.ui.start_btn.setText("Выключить")
    QtTest.QTest.qWait(50)


def ElemActive(self):
    self.ui.sleep_up_lineEdit.setEnabled(True)
    self.ui.sleep_to_lineEdit.setEnabled(True)
    self.ui.sleep_up_slider.setEnabled(True)
    self.ui.sleep_to_slider.setEnabled(True)
    self.ui.start_btn.setText("Включить")
    QtTest.QTest.qWait(50)


def UpdateClicks(self):
    self.clicks_count += 1
    self.ui.label_clicks.setText(f"{self.clicks_count} Кликов")


def GetRelPath(data_path):
    if getattr(sys, 'frozen', False):
        try:
            base_path = sys._MEIPASS
        except Exception:
            return ""
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return str(os.path.join(base_path, data_path))


class Clicker(QThread):
    click_sig = pyqtSignal()

    def __init__(self, time_up, time_down, cycle_clicks):
        super().__init__(parent=None)
        self.time_up = time_up
        self.time_to = time_down
        self.cycle_clicks = cycle_clicks
        self.virt_mouse = Controller()

    def run(self):
        while True:
            with mouse.Events() as events:
                for event in events:
                    if hasattr(event, "button") and event.button == mouse.Button.x2 and event.pressed:
                        for _ in range(self.cycle_clicks):
                            # Press
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            # Sleep
                            time.sleep(float(fastrand.pcg32randint(self.time_up, self.time_to)) * 0.00001)
                            # Release
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            # Sleep 1 / 100 of sleep time on press
                            time.sleep(float(fastrand.pcg32randint(self.time_up, self.time_to)) * 0.001)
                            # Send click res
                            self.click_sig.emit()

    def stop(self):
        self.terminate()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    User_UI()
    sys.exit(app.exec())
