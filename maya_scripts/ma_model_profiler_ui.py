# -*- coding: utf-8 -*-

import maya.cmds as mc
from PySide2 import QtWidgets, QtCore, QtGui
import ma_model_profiler as profiler

class ModelProfilerUI(QtWidgets.QDialog):
    def __init__(self):
        parent = self.get_maya_window()
        super(ModelProfilerUI, self).__init__(parent)
        self.setWindowTitle("Model Profiler")
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setMinimumWidth(420)
        self.setStyleSheet(self.get_stylesheet())
        self.build_ui()

    def get_maya_window(self):
        import shiboken2
        import maya.OpenMayaUI as omui
        ptr = omui.MQtUtil.mainWindow()
        return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)

    def get_stylesheet(self):
        return """
        QDialog {
            background-color: #2b2b2b;
            color: #dddddd;
            border: 1px solid #444444;
            border-radius: 8px;
        }
        QPushButton {
            background-color: #4a90e2;
            color: white;
            padding: 8px;
            border-radius: 6px;
        }
        QPushButton:hover {
            background-color: #357ab8;
        }
        QListWidget {
            background-color: #1e1e1e;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 4px;
        }
        QListWidget::item {
            padding: 4px;
        }
        """

    def build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Model Validation Report")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 6px;")
        layout.addWidget(title)

        self.result_list = QtWidgets.QListWidget()
        layout.addWidget(self.result_list)

        self.check_button = QtWidgets.QPushButton("Run Checks")
        self.check_button.clicked.connect(self.run_checks)
        layout.addWidget(self.check_button)

    def run_checks(self):
        self.result_list.clear()
        results = profiler.run_all_checks()

        if "error" in results:
            passed, message = results["error"]
            item = QtWidgets.QListWidgetItem(message)
            item.setForeground(QtGui.QColor("yellow"))
            self.result_list.addItem(item)
            return

        for check_name, result in results.items():
            if not isinstance(result, tuple) or len(result) != 2:
                item = QtWidgets.QListWidgetItem("[{}] Unexpected result format".format(check_name))
                item.setForeground(QtGui.QColor("orange"))
                self.result_list.addItem(item)
                continue

            passed, message = result
            display = "[{}] {}".format(check_name.replace("_", " ").title(), message)
            item = QtWidgets.QListWidgetItem(display)
            color = QtGui.QColor("lime") if passed else QtGui.QColor("yellow")
            item.setForeground(color)
            self.result_list.addItem(item)

def show_profiler_ui():
    global profiler_ui_instance
    try:
        profiler_ui_instance.close()
        profiler_ui_instance.deleteLater()
    except:
        pass
    profiler_ui_instance = ModelProfilerUI()
    profiler_ui_instance.show()
