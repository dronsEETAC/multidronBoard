import subprocess
import tkinter as tk
from PIL import Image, ImageTk

#subprocess.call(" python controladores.py", shell=True)

ventana = tk.Tk()
ventana.title("Selección de aplicación")
ventana.geometry('700x500')

# El panel principal tiene una fila y dos columnas
ventana.rowconfigure(0, weight=1)
ventana.rowconfigure(1, weight=1)
ventana.columnconfigure(0, weight=1)
ventana.columnconfigure(1, weight=1)

def controladores (event):
    subprocess.call(" python controladores.py", shell=True)

def carreras (event):
    subprocess.call(" python carreras.py", shell=True)

def carrerasCheck (event):
    subprocess.call(" python carrerasCheck.py", shell=True)


def multidronBoard (event):
    subprocess.call(" python multidronBoardConMobile.py", shell=True)






img = Image.open('images/controladores.png')
tkimage1 = img.resize((300, 200), Image.LANCZOS)
tkimage1 = ImageTk.PhotoImage(tkimage1)
controladoresLbl = tk.Label(ventana, image=tkimage1)
controladoresLbl.grid (row=0, column= 0)
controladoresLbl.bind("<Button-1>", controladores)

img = Image.open('images/multidronboard.png')
tkimage2 = img.resize((300, 200), Image.LANCZOS)
tkimage2 = ImageTk.PhotoImage(tkimage2)
multidronBoardLbl = tk.Label(ventana, image=tkimage2)
multidronBoardLbl.grid (row=0, column= 1)
multidronBoardLbl.bind("<Button-1>", multidronBoard)

img = Image.open('images/carrerascheck.png')
tkimage3 = img.resize((300, 200), Image.LANCZOS)
tkimage3 = ImageTk.PhotoImage(tkimage3)
carrerasCheckLbl = tk.Label(ventana, image=tkimage3)
carrerasCheckLbl.grid (row=1, column= 0)
carrerasCheckLbl.bind("<Button-1>", carrerasCheck)

img = Image.open('images/carreras.png')
tkimage4 = img.resize((300, 200), Image.LANCZOS)
tkimage4 = ImageTk.PhotoImage(tkimage4)
carrerasLbl = tk.Label(ventana, image=tkimage4)
carrerasLbl.grid (row=1, column= 1)
carrerasLbl.bind("<Button-1>", carreras)


ventana.mainloop()
