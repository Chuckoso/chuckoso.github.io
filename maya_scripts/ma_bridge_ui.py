# -*- coding: ascii -*-
# ma_bridge_ui.py

import os
import sys

from PySide2 import QtWidgets, QtCore, QtGui
import shiboken2
import maya.OpenMayaUI as omui

try:
    import ma_bridge_listener as bridge
    import ma_bridge_sender as sender
    reload(bridge)
    reload(sender)
except:
    raise ImportError("Could not import bridge modules")

def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return shiboken2.wrapInstance(long(ptr), QtWidgets.QMainWindow)

class BridgeUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(BridgeUI, self).__init__(parent)
        self.setWindowTitle("WAUR Bridge")
        self.setMinimumWidth(240)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        self.setObjectName("waurBridgeUI")

        self.connected_once = False
        self.build_ui()
        self.update_status()

        bridge.set_on_connect_callback(self.on_client_connected)

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Maya - Blender Bridge", self)
        label.setAlignment(QtCore.Qt.AlignCenter)

        font = QtGui.QFont()
        font.setBold(True)
        font.setPointSize(12)
        label.setFont(font)

        layout.addWidget(label)

        self.toggle_button = QtWidgets.QPushButton("Start / Stop Listener", self)
        self.toggle_button.clicked.connect(self.toggle_listener)
        layout.addWidget(self.toggle_button)

        self.send_button = QtWidgets.QPushButton("Send Selection to Blender", self)
        self.send_button.clicked.connect(self.send_selection)
        layout.addWidget(self.send_button)

        self.status_label = QtWidgets.QLabel("Status", self)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: red; color: white; padding: 4px;")
        layout.addWidget(self.status_label)

    def toggle_listener(self):
        if bridge.is_running():
            bridge.stop_listener()
            self.connected_once = False
        else:
            bridge.start_listener()
            self.connected_once = False
        self.update_status()

    def update_status(self):
        if not bridge.is_running():
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("background-color: red; color: white; padding: 4px;")
        elif not self.connected_once:
            self.status_label.setText("Awaiting Connection")
            self.status_label.setStyleSheet("background-color: orange; color: black; padding: 4px;")
        else:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("background-color: green; color: white; padding: 4px;")

    def on_client_connected(self):
        self.connected_once = True
        self.update_status()

    def send_selection(self):
        sender.send_selected_object_to_blender()

def show():
    for widget in QtWidgets.QApplication.allWidgets():
        if widget.objectName() == "waurBridgeUI":
            widget.close()
            widget.deleteLater()
            break

    parent = get_maya_main_window()
    dialog = BridgeUI(parent)
    dialog.show()
