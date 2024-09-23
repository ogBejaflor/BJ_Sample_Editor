# Main_Sample_Editor_appv2.py
import sys
from PyQt5.QtWidgets import QApplication
from UI_Sample_Editor_app import SampleChopperApp

def main():
    app = QApplication(sys.argv)
    window = SampleChopperApp()  # Match the class name from the UI file
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
