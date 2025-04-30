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
from pynput import keyboard


class User_UI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.k_listener = None  # Listener for keyboard during bind
        self.temp_pressed = None  # Temp set for pressed keys/buttons during bind
        self.m_listener = None  # Listener for mouse during bind
        self.ui = None
        self.clicks_count = 0
        self.clicker = None
        self.clicker_work = False
        self.bind_combo = {keyboard.Key.f8}  # Default bind: set
        self.waiting_for_bind = False
        self.current_pressed = set()  # Currently pressed keys/buttons
        self.load_ui()
        self.start_global_listener()  # Start global listeners for hotkey

    def load_ui(self):
        self.ui = uic.loadUi(self.get_rel_path("form.ui"), self)
        self.ui.sleep_up_slider.valueChanged.connect(self.change_slider)
        self.ui.sleep_to_slider.valueChanged.connect(self.change_slider)
        self.ui.start_btn.clicked.connect(self.start_clicker)
        self.ui.key_bind_pushButton.clicked.connect(self.wait_for_bind)
        self.update_bind_button()
        self.ui.show()

    def update_bind_button(self):
        names = []
        for key in self.bind_combo:
            if isinstance(key, keyboard.Key):
                names.append(str(key).replace('Key.', '').upper())
            elif isinstance(key, keyboard.KeyCode):
                names.append(str(key).replace("'", "").upper())
            elif isinstance(key, mouse.Button):
                names.append(str(key).replace('Button.', 'MOUSE ').upper())
        self.ui.key_bind_pushButton.setText('+'.join(sorted(names)))  # Show combo on button

    def wait_for_bind(self):
        self.waiting_for_bind = True
        self.ui.key_bind_pushButton.setText('...')
        self.bind_combo = set()
        self.temp_pressed = set()
        # Start temporary listeners for binding
        self.k_listener = keyboard.Listener(on_press=self.on_bind_key_press, on_release=self.on_bind_key_release)
        self.m_listener = mouse.Listener(on_click=self.on_bind_mouse_click)
        self.k_listener.start()
        self.m_listener.start()

    def on_bind_key_press(self, key):
        self.temp_pressed.add(key)

    def on_bind_key_release(self, key):
        # Save combo when last key is released
        if self.waiting_for_bind:
            self.bind_combo = set(self.temp_pressed)
            self.waiting_for_bind = False
            self.update_bind_button()
            self.k_listener.stop()
            self.m_listener.stop()
            self.temp_pressed = set()

    def on_bind_mouse_click(self, x, y, button, pressed):
        if pressed and self.waiting_for_bind:
            self.temp_pressed.add(button)

    def on_key_press(self, key):
        self.current_pressed.add(key)
        self.check_combo()  # Check if combo is pressed

    def on_key_release(self, key):
        self.current_pressed.discard(key)

    def on_mouse_press(self, x, y, button, pressed):
        if pressed:
            self.current_pressed.add(button)
            self.check_combo()  # Check if combo is pressed
        else:
            self.current_pressed.discard(button)

    def check_combo(self):
        # If all elements of combo are pressed, toggle clicker
        if self.bind_combo and self.bind_combo.issubset(self.current_pressed):
            self.toggle_clicker()

    def start_global_listener(self):
        import threading
        def listen_keyboard():
            with keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release) as listener:
                listener.join()
        def listen_mouse():
            with mouse.Listener(on_click=self.on_mouse_press) as listener:
                listener.join()
        # Start global listeners in background threads
        threading.Thread(target=listen_keyboard, daemon=True).start()
        threading.Thread(target=listen_mouse, daemon=True).start()

    def change_slider(self):
        self.ui.sleep_up_lineEdit.setText(str(self.ui.sleep_up_slider.value()))
        self.ui.sleep_to_lineEdit.setText(str(self.ui.sleep_to_slider.value()))
        self.ui.sleep_up_slider.setMaximum(int(self.ui.sleep_to_slider.value()) - 2)
        self.ui.sleep_to_slider.setMinimum(int(self.ui.sleep_up_slider.value()) + 2)
        avg = (self.ui.sleep_to_slider.value() + self.ui.sleep_up_slider.value()) / 2
        if avg > 0:
            cps = round(1000 / avg, 3)
        else:
            cps = 0
        self.ui.label_cpm.setText(f"{cps} CPS")

    def start_clicker(self):
        if not self.clicker_work:
            self.elem_inactive()
            self.clicks_count = 0
            self.update_clicks()
            self.clicker_work = True
            self.clicker = Clicker(
                int(self.ui.sleep_up_slider.value()),
                int(self.ui.sleep_to_slider.value()),
                int(self.ui.spinBox_cycle_clicks.value())
            )
            self.clicker.click_sig.connect(self.update_clicks)
            self.clicker.finished.connect(self.clicker_stopped)
            self.clicker.start()
        else:
            if self.clicker:
                self.clicker.stop()

    def toggle_clicker(self):
        # Toggle clicker on/off by hotkey
        if not self.clicker_work:
            self.start_clicker()
        else:
            if self.clicker:
                self.clicker.stop()

    def clicker_stopped(self):
        self.clicker = None
        self.elem_active()
        self.clicker_work = False

    def elem_inactive(self):
        self.ui.sleep_up_lineEdit.setEnabled(False)
        self.ui.sleep_to_lineEdit.setEnabled(False)
        self.ui.sleep_up_slider.setEnabled(False)
        self.ui.sleep_to_slider.setEnabled(False)
        self.ui.start_btn.setText("Выключить")
        QtTest.QTest.qWait(50)

    def elem_active(self):
        self.ui.sleep_up_lineEdit.setEnabled(True)
        self.ui.sleep_to_lineEdit.setEnabled(True)
        self.ui.sleep_up_slider.setEnabled(True)
        self.ui.sleep_to_slider.setEnabled(True)
        self.ui.start_btn.setText("Включить")
        QtTest.QTest.qWait(50)

    def update_clicks(self):
        self.clicks_count += 1
        self.ui.label_clicks.setText(f"{self.clicks_count} Кликов")

    def get_rel_path(self, data_path):
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
        self._running = True

    def run(self):
        while self._running:
            with mouse.Events() as events:
                for event in events:
                    if not self._running:
                        break
                    if hasattr(event, "button") and event.button == mouse.Button.x2 and event.pressed:
                        for _ in range(self.cycle_clicks):
                            if not self._running:
                                break
                            # Mouse press
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            time.sleep(float(fastrand.pcg32randint(self.time_up, self.time_to)) * 0.00001)
                            # Mouse release
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            time.sleep(float(fastrand.pcg32randint(self.time_up, self.time_to)) * 0.001)
                            self.click_sig.emit()
                    if not self._running:
                        break

    def stop(self):
        self._running = False
        self.wait(1000)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = User_UI()
    sys.exit(app.exec())
