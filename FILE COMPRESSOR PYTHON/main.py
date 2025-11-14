# main.py
import os
import logging
from gui.main_window import CompressMasterApp
from utils.helpers import setup_logging

if __name__ == "__main__":
    setup_logging()
    app = CompressMasterApp()
    app.run()
