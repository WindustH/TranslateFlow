# v1.0
import tkinter as tk
from tkinter import filedialog
import ctypes


def CreateWindow():
    #告诉操作系统使用程序自身的dpi适配
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    #获取屏幕的缩放因子
    ScaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
    root = tk.Tk()
    root.tk.call('tk', 'scaling', ScaleFactor / 75)
    root.withdraw()
    return root


def Directory(title="Ask for directory"):
    root = CreateWindow()
    return filedialog.askdirectory(title=title)


def File(title="Ask for a file"):
    root = CreateWindow()
    return filedialog.askopenfilename(title=title)


def Paths(title="Ask for paths"):
    root = CreateWindow()
    return filedialog.askopenfilenames(title=title)
