import json
import tkinter as tk
import os
from tkinter import ttk

from tkinter import messagebox
from tkinter.simpledialog import askstring

import tkintermapview
from PIL import Image, ImageTk
import pyautogui
import win32gui
import glob
from dronLink.Dron import Dron
import geopy.distance
from geographiclib.geodesic import Geodesic

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import paho.mqtt.client as mqtt


'''
Ejemplo de estructura de datos que representa un escenario para múltiples jugadores (multi escenario).
Los jugadores son el red, blue y green (el cuarto sería el yellow).
Para cada jugador tenemos una lista de fences. El primero es el de inclusión, que puede ser un poligono o un círculo.
El resto (si hay) son fences que representan obstáculos y pueden ser polígonos o círculos.

{
  "numPlayers": 3,
  "scenarios": [
    {
      "player": "red",
      "scenario": [
        {
          "type": "polygon",
          "waypoints": [
            {
              "lat": 41.27644776935058,
              "lon": 1.9882548704865997
            },
            {
              "lat": 41.27656972362127,
              "lon": 1.988883848500592
            },
            {
              "lat": 41.27648304540272,
              "lon": 1.9889368907028029
            },
            {
              "lat": 41.276382256631756,
              "lon": 1.9883025482707808
            }
          ]
        },
        {
          "type": "polygon",
          "waypoints": [
            {
              "lat": 41.276464903435425,
              "lon": 1.9884165421539137
            },
            {
              "lat": 41.27648304540272,
              "lon": 1.9885359004550764
            },
            {
              "lat": 41.27644776935058,
              "lon": 1.9885399237685988
            },
            {
              "lat": 41.27643063526124,
              "lon": 1.9884500697665999
            }
          ]
        }
      ]
    },
    {
      "player": "blue",
      "scenario": [
        {
          "type": "polygon",
          "waypoints": [
            {
              "lat": 41.27635524622633,
              "lon": 1.9883578031226534
            },
            {
              "lat": 41.27645704292634,
              "lon": 1.9889009504481692
            },
            {
              "lat": 41.27635855031422,
              "lon": 1.9888875394030947
            },
            {
              "lat": 41.276282958606416,
              "lon": 1.988344392077579
            }
          ]
        },
        {
          "type": "circle",
          "lat": 41.276362581869506,
          "lon": 1.9885468988582033,
          "radius": 2.669351637531348
        }
      ]
    },
    {
      "player": "green",
      "scenario": [
        {
          "type": "polygon",
          "waypoints": [
            {
              "lat": 41.27657020663036,
              "lon": 1.9889331369563479
            },
            {
              "lat": 41.27659943530579,
              "lon": 1.989017626540317
            },
            {
              "lat": 41.276431118271354,
              "lon": 1.9891021161242861
            },
            {
              "lat": 41.27640692896127,
              "lon": 1.9889894633456606
            }
          ]
        },
        {
          "type": "polygon",
          "waypoints": [
            {
              "lat": 41.276526867535786,
              "lon": 1.9889827578231234
            },
            {
              "lat": 41.27653089908068,
              "lon": 1.9890136032267947
            },
            {
              "lat": 41.27648755996002,
              "lon": 1.9890310375853915
            },
            {
              "lat": 41.276476473203594,
              "lon": 1.9890042154952425
            }
          ]
        }
      ]
    }
  ]
}
'''

# clase para gestionar los parámetros del dron
class ParameterManager:
    # con esta clase gestionamos los parámetros de un dron
    def __init__(self, window, swarm, pos):
        self.window = window
        self.swarm = swarm
        self.pos = pos
        self.on_off = 0 # indica si el geofence está habilitado (1) o no (0)
        # preparo el color correspondiente al dron (identificado del 0 en adelante)
        color = ['red', 'blue', 'green', 'yellow'][pos]


        self.managementFrame = tk.LabelFrame (window, text = 'Dron '+str(pos+1), fg=color)
        self.managementFrame.rowconfigure(0, weight=1)
        self.managementFrame.rowconfigure(1, weight=1)
        self.managementFrame.rowconfigure(2, weight=1)
        self.managementFrame.rowconfigure(3, weight=1)
        self.managementFrame.rowconfigure(4, weight=1)
        self.managementFrame.rowconfigure(5, weight=1)
        self.managementFrame.rowconfigure(6, weight=1)
        self.managementFrame.rowconfigure(7, weight=1)
        self.managementFrame.rowconfigure(8, weight=1)
        self.managementFrame.rowconfigure(9, weight=1)


        self.managementFrame.columnconfigure(0, weight=1)
        self.managementFrame.columnconfigure(1, weight=1)

        # muestro los diferentes parámetros que quiero poder modificar

        tk.Label(self.managementFrame, text='FENCE_ENABLE') \
            .grid(row=0, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        self.on_offBtn = tk.Button(self.managementFrame, text = 'OFF', bg = 'red', fg = 'white', command = self.on_off_btnClick)
        self.on_offBtn.grid(row=0, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        tk.Label(self.managementFrame, text='FENCE_ACTION') \
            .grid(row=1, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        self.fence_action_options = ["Break", "Land", "RTL"]
        self.fence_action_option = tk.StringVar(self.managementFrame)
        self.fence_action_option.set("Break")
        self.fence_action_option_menu = tk.OptionMenu(self.managementFrame, self.fence_action_option, *self.fence_action_options)
        self.fence_action_option_menu.grid(row=1, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        tk.Label(self.managementFrame, text='RTL_ALT') \
            .grid(row=2, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        self.RTL_ALT_Sldr = tk.Scale(self.managementFrame, label="RTL_ALT", resolution=1, from_=0, to=10, tickinterval=2,
                            orient=tk.HORIZONTAL)
        self.RTL_ALT_Sldr.grid(row=2, column=0, columnspan = 2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

        self.FENCE_MARGIN_Sldr = tk.Scale(self.managementFrame, label="FENCE_MARGIN", resolution=1, from_=0, to=10, tickinterval=2,
                            orient=tk.HORIZONTAL)
        self.FENCE_MARGIN_Sldr.grid(row=3, column=0, columnspan = 2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

        self.PILOT_SPEED_UP_Sldr = tk.Scale(self.managementFrame, label="PILOT_SPEED_UP", resolution=50, from_=50, to=200,
                                          tickinterval=50,
                                          orient=tk.HORIZONTAL)
        self.PILOT_SPEED_UP_Sldr.grid(row=4, column=0, columnspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

        self.FENCE_ALT_MAX_Sldr = tk.Scale(self.managementFrame, label="FENCE_ALT_MAX", resolution=1, from_=1,
                                            to=10,
                                            tickinterval=2,
                                            orient=tk.HORIZONTAL)
        self.FENCE_ALT_MAX_Sldr.grid(row=5, column=0, columnspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)
        # este parámetro es el que determina la acción que se realiza al colocar el swith de los modos de vuelo de la emisora
        # en la posición inferior
        tk.Label(self.managementFrame, text='FLTMODE6') \
            .grid(row=6, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        self.switch_action_options = ["Land", "RTL"]
        self.switch_action_option = tk.StringVar(self.managementFrame)
        self.switch_action_option.set("Land")
        self.switch_action_option_menu = tk.OptionMenu(self.managementFrame, self.switch_action_option,
                                                      *self.switch_action_options)
        self.switch_action_option_menu.grid(row=6, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        self.NAV_SPEED_Sldr = tk.Scale(self.managementFrame, label="NAV_SPEED", resolution=1, from_=1,
                                            to=10,
                                            tickinterval=1,
                                            orient=tk.HORIZONTAL)
        self.NAV_SPEED_Sldr.grid(row=7, column=0, columnspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)


        # acciones que quiero poder hacer con los parámetros
        # leer los valores que tiene el dron en ese momento
        tk.Button(self.managementFrame, text='Leer valores', bg="dark orange", command=self.read_params) \
            .grid(row=8, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        # enviar al dron los valores que he seleccionado
        tk.Button(self.managementFrame, text='Enviar valores', bg="dark orange", command=self.write_params) \
            .grid(row=8, column=1, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        # en el caso del primer dron quiero poder copiar sus valores en todos los demás
        if pos == 0:
            tk.Button(self.managementFrame, text='Copiar valores en todos los drones', bg="dark orange",
                      command=self.copy_params) \
                .grid(row=9, column=0, columnspan=2, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        else:
            # en el respo de los casos simplemente pongo un botón invisible para que se vean todos los managers alineados
            b = tk.Button(self.managementFrame, state=tk.DISABLED, bd=0)
            b.grid(row=9, column=0, columnspan=2, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

    # Esto se activa si pulso el boton de activar/desactivar el geofence
    def on_off_btnClick (self):
        if self.on_off == 0:
            self.on_off = 1
            self.on_offBtn['text'] = 'ON'
            self.on_offBtn['bg'] = 'green'
        else:
            self.on_off = 0
            self.on_offBtn['text'] = 'OFF'
            self.on_offBtn['bg'] = 'red'



    def buildFrame (self):
        return self.managementFrame

    # me guardo la lista de managers porque tengo que poder enviar info de unos a otros
    def setManagers (self, managers):
        self.managers = managers

    # aqui voy a leer del dron los valores de los parámetros de interés
    def read_params (self):
        parameters = [
            "RTL_ALT",
            "PILOT_SPEED_UP",
            "FENCE_ACTION",
            "FENCE_ENABLE",
            "FENCE_MARGIN",
            "FENCE_ALT_MAX",
            "FLTMODE6"
        ]
        result = self.swarm[self.pos].getParams(parameters)
        # coloco cada valor en su sitio
        # RTL_ALT viene en cm
        self.RTL_ALT_Sldr.set (int(result [0]['RTL_ALT']/100))
        self.PILOT_SPEED_UP_Sldr.set (result[1]['PILOT_SPEED_UP'])
        self.FENCE_MARGIN_Sldr.set(result[4]['FENCE_MARGIN'])
        self.FENCE_ALT_MAX_Sldr.set(result[5]['FENCE_ALT_MAX'])
        self.fence_action_option.set([None,'RTL', 'Land', None, 'Break'][int(result[2]['FENCE_ACTION'])])
        if int(result[6]['FLTMODE6']) == 6:
            self.switch_action_option.set ('RTL')
        elif int(result[6]['FLTMODE6']) == 9:
            self.switch_action_option.set('Land')
        if result[3]['FENCE_ENABLE'] == 0:
            self.on_off = 0
            self.on_offBtn['text'] = 'OFF'
            self.on_offBtn['bg'] = 'red'
        else:
            self.on_off = 1
            self.on_offBtn['text'] = 'ON'
            self.on_offBtn['bg'] = 'green'
        self.NAV_SPEED_Sldr.set (self.swarm[self.pos].navSpeed)
    # escribo en el dron los valores seleccionados
    def write_params (self):
        if self.switch_action_option.get () == 'Land':
            switch_option = 9
        elif self.switch_action_option.get () == 'RTL':
            switch_option = 6
        parameters = [
            {'ID': "FENCE_ENABLE", 'Value': float(self.on_off)},
            {'ID': "FENCE_ACTION", 'Value': float([None,'RTL', 'Land', None, 'Break'].index(self.fence_action_option.get()))},
            {'ID': "PILOT_SPEED_UP", 'Value': float(self.PILOT_SPEED_UP_Sldr.get())},
            {'ID': "PILOT_SPEED_DN", 'Value': 0}, # Para que use el mismo valor que se ha fijado para UP
            {'ID': "RTL_ALT", 'Value': float(self.RTL_ALT_Sldr.get()*100)},
            {'ID': "FENCE_MARGIN", 'Value': float(self.FENCE_MARGIN_Sldr.get())},
            {'ID': "FENCE_ALT_MAX", 'Value': float(self.FENCE_ALT_MAX_Sldr.get())},
            {'ID': "FLTMODE6", 'Value': float(switch_option)}
        ]
        self.swarm[self.pos].setParams(parameters)
        self.swarm[self.pos].navSpeed = float(self.NAV_SPEED_Sldr.get())
        messagebox.showinfo( "showinfo", "Parámetros enviados", parent=self.window)

    # copio los valores de los parámetros del dron primero en todos los demás
    def copy_params (self):

        for i in range (1,len(self.swarm)):
            dronManager = self.managers[i]

            dronManager.RTL_ALT_Sldr.set(self.RTL_ALT_Sldr.get())
            dronManager.PILOT_SPEED_UP_Sldr.set(self.PILOT_SPEED_UP_Sldr.get())
            dronManager.FENCE_MARGIN_Sldr.set(self.FENCE_MARGIN_Sldr.get())
            dronManager.FENCE_ALT_MAX_Sldr.set(self.FENCE_ALT_MAX_Sldr.get())
            dronManager.fence_action_option.set(self.fence_action_option.get())
            dronManager.switch_action_option.set(self.switch_action_option.get())
            dronManager.NAV_SPEED_Sldr.set(self.NAV_SPEED_Sldr.get())

            dronManager.on_off =  self.on_off
            dronManager.on_offBtn['text'] = self.on_offBtn['text']
            dronManager.on_offBtn['bg'] =  self.on_offBtn['bg']

# procesado de los datos de telemetría
def processTelemetryInfo (id, telemetry_info):
    global dronIcons, myZone, myZoneWidget
    # recupero la posición en la que está el dron
    lat = telemetry_info['lat']
    lon = telemetry_info['lon']
    alt = telemetry_info['alt']

    # si es el primer paquete de este dron entonces ponemos en el mapa el icono de ese dron
    if not dronIcons[id]:
        dronIcons[id] = map_widget.set_marker(lat, lon,
                        icon=dronPictures[id],icon_anchor="center")
    # si no es el primer paquete entonces muevo el icono a la nueva posición
    else:
        dronIcons[id].set_position(lat,lon)
    # actrualizo la altitud
    altitudes[id]['text'] = str (round(alt,2))

    point = Point(lat,lon)

    for i in range(0, len(zones)):
        polygon = Polygon([zones[i][0],zones[i][1],zones[i][2],zones[i][3]])
        if polygon.contains(point):
            if myZone[id] != i:
                myZone[id] = i
                if myZoneWidget[id]:
                    myZoneWidget[id].delete()
                    #print('El dron  ', id, 'esta en la zona', i)
                myZoneWidget[id] = map_widget.set_polygon([zones[i][0],zones[i][1],zones[i][2],zones[i][3]], outline_color=colors[id], fill_color = colors[id] , border_width=1)

    # veamos si algun dron ha atrapado a alguno de sus rivales
    for i in range (0,len(swarm)):
        # veamos si el dron i ha atrapado a alguien
        if myZone [i]:
            for j in range(0, len(swarm)):
                if i!= j and myZone[j]:
                    # veamos si el dron i ha atrapado al dron j
                    if (myZone[j] - myZone[i]) % len(zones) == 1:
                        swarm[j].Land(blocking=False)


########## Funciones para la creación de multi escenarios #################################

def createBtnClick ():
    global scenario, polys, markers
    scenario = []
    # limpiamos el mapa de los elementos que tenga
    clear()
    # quitamos los otros frames
    selectFrame.grid_forget()
    superviseFrame.grid_forget()
    # visualizamos el frame de creación
    createFrame.grid(row=1, column=0,  columnspan=3, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)

    createBtn['text'] = 'Creando...'
    createBtn['fg'] = 'white'
    createBtn['bg'] = 'green'

    selectBtn['text'] = 'Seleccionar'
    selectBtn['fg'] = 'black'
    selectBtn['bg'] = 'dark orange'

    superviseBtn['text'] = 'Supervisar'
    superviseBtn['fg'] = 'black'
    superviseBtn['bg'] = 'dark orange'



# cerramos el fence
def closeFence(coords):
    global poly, polys, fence, zonas, cerrado
    pos = len(puntos)
    print (pos)
    if pos%4 == 0:
        map_widget.set_polygon([puntos [pos-2], puntos [pos-1], puntos [0], puntos[1]], outline_color='black', border_width=1)
        zonas.append ([puntos [pos-2], puntos [pos-1], puntos [0], puntos[1]])
    else:
        map_widget.set_polygon([puntos[pos - 2], puntos[pos - 1], puntos[1], puntos[0]], outline_color='black',
                               border_width=1)
        zonas.append ([puntos [pos-2], puntos [pos-1], puntos [1], puntos[0]])

    i = 0
    externo = []
    interno = []
    while i < len(puntos):
        externo.append(puntos[i])
        externo.append(puntos [i+3])
        interno.append (puntos[i+1])
        interno.append(puntos[i+2])
        i = i+4
    map_widget.set_polygon(externo, outline_color='red',
                           border_width=3)

    map_widget.set_polygon(interno, outline_color='blue',
                           border_width=3)
    cerrado = True

# genera el poligono que aproxima al círculo
'''def getCircle ( lat, lon, radius):
    # aquí creo el polígono que aproxima al círculo
    geod = Geodesic.WGS84
    points = []
    for angle in range(0, 360, 5):  # 5 grados de separación para suavidad
        # me da las coordenadas del punto que esta a una distancia radius del centro (lat, lon) con el ángulo indicado
        g = geod.Direct(lat, lon, angle, radius)
        lat2 = float(g["lat2"])
        lon2 = float(g["lon2"])
        points.append((lat2, lon2))
    return points
'''



############################ Funciones para seleccionar multi escenario ##########################################
def selectBtnClick ():
    global scenarios, current, polys
    scenarios = []
    # limpio el mapa
    cleanDesign()
    # elimino los otros frames
    createFrame.grid_forget()
    superviseFrame.grid_forget()
    # muestro el frame de selección
    selectFrame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    selectBtn['text'] = 'Seleccionando...'
    selectBtn['fg'] = 'white'
    selectBtn['bg'] = 'green'

    createBtn['text'] = 'Crear'
    createBtn['fg'] = 'black'
    createBtn['bg'] = 'dark orange'

    superviseBtn['text'] = 'Supervisar'
    superviseBtn['fg'] = 'black'
    superviseBtn['bg'] = 'dark orange'

    startSelectingCircuit()

# una vez elegido el numero de jugadores mostramos los multi escenarios que hay para ese número de jugadores
def startSelectingCircuit ():
    global circuits, current

    # cargamos en una lista las imágenes de todos los multi escenarios disponibles
    # para el número de jugadores indicado
    circuits = []
    for file in glob.glob("circuits/*.png"):
        circuit = Image.open(file)
        circuit = circuit.resize((300, 200))
        circuitPic = ImageTk.PhotoImage(circuit)
        # en la lista guardamos el nombre que se le dió al escenario y la imagen
        circuits.append({'name': file.split('.')[0], 'pic': circuitPic})

    if len(circuits) > 0:
        # mostramos ya en el canvas la imagen del primer multi escenario
        circuitCanvas.create_image(0, 0, image=circuits[0]['pic'], anchor=tk.NW)
        current = 0
        # no podemos seleccionar el anterior porque no hay anterior
        prevBtn['state'] = tk.DISABLED
        # y si solo hay 1 multi escenario tampoco hay siguiente
        if len(circuits) == 1:
            nextBtn['state'] = tk.DISABLED
        else:
            nextBtn['state'] = tk.NORMAL

        sendBtn['state'] = tk.DISABLED
    else:
        messagebox.showinfo("showinfo",
                            "No hay circuitos para elegir")

# mostrar anterior
def showPrev ():
    global current
    current = current -1
    # mostramos el multi escenario anterior
    circuitCanvas.create_image(0, 0, image=circuits[current]['pic'], anchor=tk.NW)
    # deshabilitamos botones si no hay anterior o siguiente
    if current == 0:
        prevBtn['state'] = tk.DISABLED
    else:
        prevBtn['state'] = tk.NORMAL
    if current == len(circuits) - 1:
        nextBtn['state'] = tk.DISABLED
    else:
        nextBtn['state'] = tk.NORMAL

# mostrar siguiente
def showNext ():
    global current
    current = current +1
    # muestro el siguiente
    circuitCanvas.create_image(0, 0, image=circuits[current]['pic'], anchor=tk.NW)
    # deshabilitamos botones si no hay anterior o siguiente
    if current == 0:
        prevBtn['state'] = tk.DISABLED
    else:
        prevBtn['state'] = tk.NORMAL
    if current == len(circuits) - 1:
        nextBtn['state'] = tk.DISABLED
    else:
        nextBtn['state'] = tk.NORMAL

def selectCircuit ():
    global polys, selectedCircuit
    # limpio el mapa
    for poly in polys:
        poly.delete()
    # cargamos el fichero json con el multi escenario seleccionado (el que está en la posición current de la lista9
    f = open(circuits[current]['name'] + '.json')
    selectedCircuitPoints = json.load(f)
    # dibujo el escenario
    drawCircuit(selectedCircuitPoints)
    # habilito el botón para enviar el circuito al enjambre
    sendBtn['state'] = tk.NORMAL

# Limpiamos el mapa
def clear ():
    global paths, fence, polys
    name.set ("")
    for path in paths:
        path.delete()
    for poly in polys:
        poly.delete()

    paths = []
    polys = []

# borramos el escenario que esta a la vista
def deleteCircuit ():
    global current
    msg_box = messagebox.askquestion(
        "Atención",
        "¿Seguro que quieres eliminar este circuito?",
        icon="warning",
    )
    if msg_box == "yes":
        # borro los dos ficheros que representan el multi escenario seleccionado
        os.remove(circuits[current]['name'] + '.png')
        os.remove(circuits[current]['name'] + '.json')
        circuits.remove (circuits[current])
        # muestro el multi escenario anterior (o el siguiente si no hay anterior o ninguno si tampoco hay siguiente)
        if len (circuits) != 0:
            if len (circuits) == 1:
                # solo queda un escenario
                current = 0
                circuitCanvas.create_image(0, 0, image=circuits[current]['pic'], anchor=tk.NW)
                prevBtn['state'] = tk.DISABLED
                nextBtn['state'] = tk.DISABLED
            else:
                # quedan más multi escenarios
                if current == 0:
                    # hemos borrado el primer multi escenario de la lista. Mostramos el nuevo primero
                    circuitCanvas.create_image(0, 0, image=circuits[current]['pic'], anchor=tk.NW)
                    prevBtn['state'] = tk.DISABLED
                    if len (circuits) > 1:
                        nextBtn['state'] = tk.NORMAL
                else:
                    # mostramos
                    circuitCanvas.create_image(0, 0, image=circuits[current]['pic'], anchor=tk.NW)
                    prevBtn['state'] = tk.NORMAL
                    if current == len (circuits) -1:
                        nextBtn['state'] = tk.DISABLED
                    else:
                        nextBtn['state'] = tk.NORMAL
            cleanDesign()

# dibujamos en el mapa el multi escenario
def drawCircuit (selectedCircuitPoints):
    global polys, zones, scenario

    # borro los elementos que haya en el mapa
    for poly in polys:
        poly.delete()
    zones = []
    i=0
    while i < len(selectedCircuitPoints) -2:
        zone = []
        for point in selectedCircuitPoints[i:i + 4]:
            zone.append ((point[0], point[1]))
        print ('zone ', zone)
        zones.append(zone)
        polys.append(map_widget.set_polygon(zone, outline_color='black', border_width=1))
        i = i+2

    pos = len(selectedCircuitPoints)
    if pos % 4 == 0:
        zone = [(selectedCircuitPoints[pos - 2][0], selectedCircuitPoints[pos - 2][1]),
                (selectedCircuitPoints[pos - 1][0], selectedCircuitPoints[pos - 1][1]),
                (selectedCircuitPoints[0][0], selectedCircuitPoints[0][1]),
                (selectedCircuitPoints[1][0], selectedCircuitPoints[1][1])]


        #zone = [selectedCircuitPoints[pos - 2], selectedCircuitPoints[pos - 1], selectedCircuitPoints[0], selectedCircuitPoints[1]]
        zones.append(zone)
        polys.append(
            map_widget.set_polygon(zone, outline_color='black',
                                   border_width=1))
    else:

        zone = [(selectedCircuitPoints[pos - 2][0],selectedCircuitPoints[pos - 2][1]) ,
                (selectedCircuitPoints[pos - 1][0],selectedCircuitPoints[pos - 1][1]),
                (selectedCircuitPoints[1][0],selectedCircuitPoints[1][1]),
                (selectedCircuitPoints[0][0], selectedCircuitPoints[0][1])]

        zones.append(zone)
        polys.append(
            map_widget.set_polygon(zone, outline_color='black',
                                   border_width=1))

    i = 0
    external = []
    internal = []

    if len(zones) % 2 == 0:
        while i < len(selectedCircuitPoints):
            external.append(selectedCircuitPoints[i])
            external.append(selectedCircuitPoints[i + 3])
            internal.append(selectedCircuitPoints[i + 1])
            internal.append(selectedCircuitPoints[i + 2])
            i = i + 4
    else:
        while i < len(selectedCircuitPoints) - 2:
            external.append(selectedCircuitPoints[i])
            external.append(selectedCircuitPoints[i + 3])
            internal.append(selectedCircuitPoints[i + 1])
            internal.append(selectedCircuitPoints[i + 2])
            i = i + 4
        external.append(selectedCircuitPoints[len(selectedCircuitPoints) - 2])
        internal.append(selectedCircuitPoints[len(selectedCircuitPoints) - 1])

    polys.append(map_widget.set_polygon(external, outline_color='red',
                                        border_width=3))

    polys.append(map_widget.set_polygon(internal, outline_color='blue',
                                        border_width=3))

    scenario = []
    fence = {
        'type': 'polygon',
        'waypoints': []
    }
    for point in external:
        fence['waypoints'].append ({'lat': point[0], 'lon': point[1]})
    scenario.append (fence)
    fence = {
        'type': 'polygon',
        'waypoints': []
    }
    for point in internal:
        fence['waypoints'].append ({'lat': point[0], 'lon': point[1]})
    scenario.append (fence)


# envia los datos del  escenario seleccionado al enjambre
def sendCircuit ():
    # enviamos a cada dron del enjambre el escenario que le toca
    global swarm
    global connected, dron, dronIcons
    global altitudes, scenario

    for i in range (0,len(swarm)):
        swarm[i].setScenario(scenario)

    sendBtn['bg'] = 'green'



# me contecto a los drones del enjambre
def connect ():
    global swarm
    global connected, dron, dronIcons
    global altitudes, colors

    if not connected:

        if connectOption.get () == 'Simulation':
            # nos conectaremos a los simuladores de los drones
            connectionStrings = []
            base = 5763
            for i in range(0, numPlayers):
                port = base + i * 10
                connectionStrings.append('tcp:127.0.0.1:' + str(port))
            baud = 115200
        else:
            # nos conectaremos a los drones reales a través de las radios de telemetría
            # los puertos ya los hemos indicado y estan en comPorts, separados por comas
            connectionStrings = comPorts.split(',')
            baud = 57600


        colors = ['red', 'blue', 'green', 'yellow']
        altitudes = []

        # creamos el enjambre
        swarm = []
        dronIcons = [None, None, None, None]

        for i in range(0, numPlayers):
            # identificamos el dron
            dron = Dron(i)
            swarm.append(dron)
            # nos conectamos
            dron.connect(connectionStrings[i], baud)
            # colocamos los botones para aterrizar, cada uno con el color que toca
            tk.Button(superviseFrame, bg=colors[i],
                          command=lambda d=swarm[i]: d.Land(blocking=False)) \
                .grid(row=2, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            # colocamos las labels para mostrar las alturas de los drones
            altitudes.append(tk.Label(superviseFrame, text='', borderwidth=1, relief="solid"))
            altitudes[-1].grid(row=4, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            # solicitamos datos de telemetria del dron
            dron.send_telemetry_info(processTelemetryInfo)

        connected = True
        connectBtn['bg'] = 'green'




################### Funciones para supervisar el multi escenario #########################

def superviseBtnClick ():

    # quitamos los otros dos frames
    selectFrame.grid_forget()
    createFrame.grid_forget()
    # visualizamos el frame de creación
    superviseFrame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    createBtn['text'] = 'Crear'
    createBtn['fg'] = 'black'
    createBtn['bg'] = 'dark orange'

    selectBtn['text'] = 'Seleccionar'
    selectBtn['fg'] = 'black'
    selectBtn['bg'] = 'dark orange'

    superviseBtn['text'] = 'Supervisando...'
    superviseBtn['fg'] = 'white'
    superviseBtn['bg'] = 'green'

# creamos la ventana para gestionar los parámetros de los drones del enjambre
def adjustParameters ():
    global swarm
    # voy a mostrar la ventana de gestión de los parámetros
    parameterManagementWindow = tk.Tk()
    parameterManagementWindow.title("Gestión de parámetros")
    parameterManagementWindow.rowconfigure(0, weight=1)
    parameterManagementWindow.rowconfigure(1, weight=1)
    # voy a crear un manager para cada dron
    managers = []
    for i in range(0, len(swarm)):
        parameterManagementWindow.columnconfigure(i, weight=1)
        dronManager = ParameterManager(parameterManagementWindow, swarm, i)
        managers.append(dronManager)
        # coloco el frame correspondiente a este manager en la ventana de gestión de parámetros
        dronFrame = dronManager.buildFrame()
        dronFrame.grid(row=0, column=i, padx=50, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)
    managers[0].setManagers(managers)
    tk.Button(parameterManagementWindow, text='Cerrar', bg="dark orange",
              command=lambda: parameterManagementWindow.destroy()) \
        .grid(row=1, column=0, columnspan=len(swarm), padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

    parameterManagementWindow.mainloop()

############# Funciones para crear el circuito  ###########################################333
def startDesign ():
    global markers, points, zones, closed, polys
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo señala los puntos que definen las zonas\n"
                        "Con el boton derecho indica el fin del diseño\n"
                        "Empieza marcando un punto del exterior del circuito")
    points = []
    markers = []
    zones = []
    polys = []
    closed = False

def getFenceWaypoint (coords):
    global markers,zones, closed, points
    # acabo de clicar con el botón izquierdo
    if not closed:
        points.append(coords)
        marker = map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center")
        markers.append (marker)
        if len (points) == 4:
            polys.append(map_widget.set_polygon(points, outline_color='black',border_width=1))
            for marker in markers:
                marker.delete()
            markers = []
            zone = [ point for point in points]
            zones.append (zone)
        elif len (points) > 4 and len(points)% 2 == 0:
            pos = len(points)
            polys.append( map_widget.set_polygon(points[pos-4: pos], outline_color='black', border_width=1))
            for marker in markers:
                marker.delete()
            markers = []
            zone = [point for point in points[pos-4: pos]]
            zones.append(zone)
    else:
        point = Point(coords[0], coords[1])

        for i in range (0,len(zones)):
            print ('aaaa', zones[i])
            polygon = Polygon(zones[i])
            if polygon.contains(point):
                print (' Esta en la zona ', i)


def closeCircuit(coords):
    global closed

    pos = len (points)
    if pos%4 == 0:
        polys.append(map_widget.set_polygon([points [pos-2], points [pos-1], points [0], points[1]], outline_color='black', border_width=1))
        zones.append ([points [pos-2], points [pos-1], points [0], points[1]])
    else:
        polys.append(map_widget.set_polygon([points[pos - 2], points[pos - 1], points[1], points[0]], outline_color='black',
                               border_width=1))
        zones.append ([points [pos-2], points [pos-1], points [1], points[0]])

    i = 0
    external = []
    internal = []
    if len(zones)%2 == 0:
        while i < len(points):
            external.append(points[i])
            external.append(points[i + 3])
            internal.append(points[i + 1])
            internal.append(points[i + 2])
            i = i + 4
    else:
        while i < len(points)-2:
            external.append(points[i])
            external.append(points[i + 3])
            internal.append(points[i + 1])
            internal.append(points[i + 2])
            i = i + 4
        external.append(points[len(points)-2])
        internal.append(points[len(points)-1])

    polys.append(map_widget.set_polygon(external, outline_color='red',
                           border_width=3))

    polys.append(map_widget.set_polygon(internal, outline_color='blue',
                           border_width=3))
    closed = True
# La siguiente función crea una imagen capturando el contenido de una ventana

def cleanDesign ():
    global polys, points, markers, zones, closed
    for poly in polys:
        poly.delete()
    points = []
    markers = []
    zones = []
    polys = []
    closed = False

def screenshot(window_title=None):
    # capturo una imagen del multi escenario para guardarla más tarde
    if window_title:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            x, y, x1, y1 = win32gui.GetClientRect(hwnd)
            x, y = win32gui.ClientToScreen(hwnd, (x, y))
            x1, y1 = win32gui.ClientToScreen(hwnd, (x1 - x, y1 - y))
            # aquí le indico la zona de la ventana que me interesa, que es básicamente la zona del dronLab
            im = pyautogui.screenshot(region=(x+800, y+250, 750, 580))
            return im
        else:
            print('Window not found!')
    else:
        im = pyautogui.screenshot()
        return im

# guardamos los datos del escenario (imagen y fichero json)
def registerCircuit ():

    # voy a guardar el multi escenario en el fichero con el nombre indicado en el momento de la creación
    jsonFilename = 'circuits/' + name.get() + ".json"

    with open(jsonFilename, 'w') as f:
        json.dump(points, f)
    # aqui capturo el contenido de la ventana que muestra el Camp Nou (zona del cesped, que es dónde está el escenario)
    im = screenshot('Gestión de circuitos')
    imageFilename = 'circuits/'+name.get()+".png"
    im.save(imageFilename)

    cleanDesign()
def setNumPlayers (n):
    global numPlayers
    numPlayers = n


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK Returned code=", rc)
    else:
        print("Bad connection Returned code=", rc)

def publish_event (id, event):
    # al ser drones idenificados dronLink nos pasa siempre en primer lugar el identificador
    # del dron que ha hecho la operación
    # lo necesito para identificar qué jugador debe hacer caso a la respuesta
    global client
    client.publish('multiPlayerDash/mobileApp/'+event+'/'+str(id))

# aqui recibimos las publicaciones que hacen las web apps desde las que están jugando
def on_message(client, userdata, message):
    # el formato del topic siempre será:
    # multiPlayerDash/mobileApp/COMANDO/NUMERO
    # el número normalmente será el número del jugador (entre el 0 y el 3)
    # excepto en el caso de la petición de conexión
    global playersCount
    parts = message.topic.split ('/')
    command = parts[2]
    if command == 'connect':
        # el cuarto trozo del topic es un número aleatorio que debo incluir en la respuesta
        # para que ésta sea tenida en cuenta solo por el jugador que ha hecho la petición
        randomId = parts[3]
        if playersCount == numPlayers:
            # ya no hay sitio para más jugadores
            client.publish('multiPlayerDash/mobileApp/notAccepted/'+randomId)
        else:
            # aceptamos y le asignamos el identificador del siguiente jugador
            client.publish('multiPlayerDash/mobileApp/accepted/'+randomId, playersCount)
            playersCount = playersCount+1

    if command == 'arm_takeOff':
        # en este comando y en los siguientes, el último trozo del topic identifica al jugador que hace la petición
        id = int (parts[3])
        dron = swarm[id]
        if dron.state == 'connected':
            dron.arm()
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.takeOff(5, blocking=False, callback=publish_event, params='flying')

    if command == 'go':
        id = int (parts[3])
        dron = swarm[id]
        if dron.state == 'flying':
            direction = message.payload.decode("utf-8")
            dron.go(direction)

    if command == 'Land':
        id = int (parts[3])
        dron = swarm[id]
        if dron.state == 'flying':
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.Land(blocking=False, callback=publish_event, params='landed')

    if command == 'RTL':
        id = int (parts[3])
        dron = swarm[id]
        if dron.state == 'flying':
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.RTL(blocking=False, callback=publish_event, params='atHome')





def crear_ventana():

    global map_widget
    global createBtn,selectBtn, superviseBtn, createFrame, name, selectFrame, scene, scenePic,scenarios, current
    global superviseFrame
    global prevBtn, nextBtn, sendBtn, connectBtn
    global circuitCanvas
    global i_wp, e_wp
    global paths, fence, polys
    global connected
    global selectPlayersFrame
    global red, blue, green, yellow, black, dronPictures
    global connectOption
    global numPlayers, playersCount
    global myZone, myZoneWidget
    global client

    myZone = [None]*4
    myZoneWidget = [None]*4

    connected = False
    playersCount = 0

    # para guardar datos y luego poder borrarlos
    paths = []
    fence = []
    polys = []


    ventana = tk.Tk()
    ventana.title("Gestión de circuitos")
    ventana.geometry ('1900x1000')

    # El panel principal tiene una fila y dos columnas
    ventana.rowconfigure(0, weight=1)
    ventana.columnconfigure(0, weight=1)
    ventana.columnconfigure(1, weight=1)

    controlFrame = tk.LabelFrame(ventana, text = 'Control')
    controlFrame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # El frame de control aparece en la primera columna
    controlFrame.rowconfigure(0, weight=1)
    controlFrame.rowconfigure(1, weight=1)
    controlFrame.columnconfigure(0, weight=1)
    controlFrame.columnconfigure(1, weight=1)
    controlFrame.columnconfigure(2, weight=1)


    # botones para crear/seleccionar/supervisar
    createBtn = tk.Button(controlFrame, text="Crear", bg="dark orange", command = createBtnClick)
    createBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    selectBtn = tk.Button(controlFrame, text="Seleccionar", bg="dark orange", command = selectBtnClick)
    selectBtn.grid(row=0, column=1,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    superviseBtn = tk.Button(controlFrame, text="Supervisar", bg="dark orange", command=superviseBtnClick)
    superviseBtn.grid(row=0, column=2,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    ################################# frame para crear circuito  ###################################################
    createFrame = tk.LabelFrame(controlFrame, text='Crear circuito')
    # la visualización del frame se hace cuando se clica el botón de crear
    #createFrame.grid(row=1, column=0,  columnspan=3, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    createFrame.rowconfigure(0, weight=1)
    createFrame.rowconfigure(1, weight=1)
    createFrame.rowconfigure(2, weight=1)
    createFrame.rowconfigure(3, weight=1)
    createFrame.rowconfigure(4, weight=1)
    createFrame.rowconfigure(5, weight=1)
    createFrame.rowconfigure(6, weight=1)
    createFrame.rowconfigure(7, weight=1)
    createFrame.rowconfigure(8, weight=1)
    createFrame.rowconfigure(9, weight=1)
    createFrame.columnconfigure(0, weight=1)
    createFrame.columnconfigure(1, weight=1)

    tk.Label (createFrame, text='Escribe el nombre aquí')\
        .grid(row=0, column=0, columnspan = 2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # el nombre se usará para poner nombre al fichero con la imagen y al fichero json con el circuito
    name = tk.StringVar()
    tk.Entry(createFrame, textvariable=name)\
        .grid(row=1, column=0, columnspan = 2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    startDesignBtn = tk.Button(createFrame, text="Inicia el diseño", bg="dark orange",
                                      command= startDesign)
    startDesignBtn.grid(row=2, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    cleanDesignBtn = tk.Button(createFrame, text="Borra diseño", bg="dark orange",
                                      command= cleanDesign)
    cleanDesignBtn.grid(row=2, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    registerCircuitBtn = tk.Button(createFrame, text="Guardar circuito", bg="dark orange", command = registerCircuit)
    registerCircuitBtn.grid(row=3, column=0, columnspan = 2, padx=5, pady=5, sticky=tk.N +tk.E + tk.W)


    ################################ frame para seleccionar circuito ############################################
    selectFrame = tk.LabelFrame(controlFrame, text='Selecciona el circuito')
    # la visualización del frame se hace cuando se clica el botón de seleccionar
    #selectFrame.grid(row=1, column=0,  columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    selectFrame.rowconfigure(0, weight=1)
    selectFrame.rowconfigure(1, weight=1)
    selectFrame.rowconfigure(2, weight=1)
    selectFrame.rowconfigure(3, weight=1)
    selectFrame.rowconfigure(4, weight=1)
    selectFrame.rowconfigure(5, weight=1)
    selectFrame.rowconfigure(6, weight=1)
    selectFrame.rowconfigure(7, weight=1)
    selectFrame.columnconfigure(0, weight=1)
    selectFrame.columnconfigure(1, weight=1)
    selectFrame.columnconfigure(2, weight=1)
    selectFrame.columnconfigure(3, weight=1)


    tk.Label (selectFrame, text = 'Selecciona el número de jugadores').\
        grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="1", bg="dark orange", command = lambda: setNumPlayers (1))\
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="2", bg="dark orange", command=lambda:  setNumPlayers (2))\
        .grid(row=1, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="3", bg="dark orange", command=lambda: setNumPlayers (3))\
        .grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="4", bg="dark orange", command=lambda:  setNumPlayers (4))\
        .grid(row=1, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    # en este canvas se mostrarán las imágenes de los escenarios disponibles
    circuitCanvas = tk.Canvas(selectFrame, width=300, height=200, bg='grey')
    circuitCanvas.grid(row = 2, column=0, columnspan=4, padx=5, pady=5)

    prevBtn = tk.Button(selectFrame, text="<<", bg="dark orange", command = showPrev)
    prevBtn.grid(row=3, column=0, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)
    selectScenarioBtn = tk.Button(selectFrame, text="Seleccionar", bg="dark orange", command = selectCircuit)
    selectScenarioBtn.grid(row=3, column=1, columnspan = 2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    nextBtn = tk.Button(selectFrame, text=">>", bg="dark orange", command = showNext)
    nextBtn.grid(row=3, column=3, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)


    # pequeño frame para configurar la conexión
    connectFrame = tk.Frame(selectFrame)
    connectFrame.grid(row=5, column=0, columnspan=4, padx=5, pady=3, sticky=tk.N  + tk.E + tk.W)
    connectFrame.rowconfigure(0, weight=1)
    connectFrame.rowconfigure(1, weight=1)
    connectFrame.rowconfigure(2, weight=1)
    connectFrame.columnconfigure(0, weight=1)
    connectFrame.columnconfigure(1, weight=1)

    connectBtn = tk.Button(connectFrame, text="Conectar", bg="dark orange", command = connect)
    connectBtn.grid(row=0, column=0, rowspan=2, padx=5, pady=3, sticky=tk.N + tk.S + tk.E + tk.W)

    # se puede elegir entre conectarse al simulador o conectarse al dron real
    # en el segundo caso hay que especificar en qué puertos están conectadas las radios de telemetría
    connectOption = tk.StringVar()
    connectOption.set('Simulation')  # por defecto se trabaja en simulación
    option1 = tk.Radiobutton(connectFrame, text="Simulación", variable=connectOption, value="Simulation")
    option1.grid(row=0, column=1, padx=5, pady=3, sticky=tk.N + tk.S + tk.W)

    # se activa cuando elegimos la conexión en modo producción. Aquí especificamos los puertos en los que están
    # conectadas las radios de telemetría
    def ask_Ports():
        global comPorts
        comPorts = askstring('Puertos', "Indica los puertos COM separados por comas (por ejemplo: 'COM3,COM21,COM7')")

    option2 = tk.Radiobutton(connectFrame, text="Producción", variable=connectOption, value="Production",
                             command=ask_Ports)
    option2.grid(row=1, column=1, padx=5, pady=3, sticky=tk.N + tk.S + tk.W)


    sendBtn = tk.Button(selectFrame, text="Enviar circuito", bg="dark orange", command=sendCircuit)
    sendBtn.grid(row=6, column=0,columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    deleteBtn = tk.Button(selectFrame, text="Eliminar escenario", bg="red", fg = 'white', command = deleteCircuit)
    deleteBtn.grid(row=7, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)

    ########################## frame para supervisar ####################################################
    superviseFrame = tk.LabelFrame(controlFrame, text='Supervisar vuelos')
    # la visualización del frame se hace cuando se clica el botón de supervisar
    # superviseFrame.grid(row=1, column=0,  columnspan=3, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    superviseFrame.rowconfigure(0, weight=1)
    selectFrame.rowconfigure(1, weight=1)
    selectFrame.rowconfigure(2, weight=1)
    selectFrame.rowconfigure(3, weight=1)
    selectFrame.rowconfigure(4, weight=1)
    selectFrame.rowconfigure(5, weight=1)
    selectFrame.rowconfigure(6, weight=1)
    superviseFrame.columnconfigure(0, weight=1)
    superviseFrame.columnconfigure(1, weight=1)
    superviseFrame.columnconfigure(2, weight=1)
    superviseFrame.columnconfigure(3, weight=1)

    parametersBtn = tk.Button(superviseFrame, text="Ajustar parámetros", bg="dark orange", command=adjustParameters)
    parametersBtn.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # debajo de este label colocaremos botones para aterrizar los drones.
    # los colocaremos cuando sepamos cuántos drones tenemos en el enjambre
    tk.Label(superviseFrame, text='Aterrizar') \
        .grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # debajo de este label colocaremos las alturas en las que están los drones
    # las colocaremos cuando sepamos cuántos drones tenemos en el enjambre
    tk.Label(superviseFrame, text='Altitudes') \
        .grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    #################### Frame para el mapa, en la columna de la derecha #####################
    mapaFrame = tk.LabelFrame(ventana, text='Mapa')
    mapaFrame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    mapaFrame.rowconfigure(0, weight=1)
    mapaFrame.rowconfigure(1, weight=1)
    mapaFrame.columnconfigure(0, weight=1)

    # creamos el widget para el mapa
    map_widget = tkintermapview.TkinterMapView(mapaFrame, width=1400, height=1000, corner_radius=0)
    map_widget.grid(row=1, column=0, padx=5, pady=5)
    map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga",
                                    max_zoom=22)
    map_widget.set_position( 41.2764478, 1.9886568)  # Coordenadas del dronLab
    map_widget.set_zoom(20)


    # indicamos que capture los eventos de click sobre el mouse
    map_widget.add_right_click_menu_command(label="Cierra el fence", command=closeCircuit, pass_coords=True)
    map_widget.add_left_click_map_command(getFenceWaypoint)

    # ahora cargamos las imagenes de los iconos que vamos a usar

    # icono para marcadores
    im = Image.open("images/red.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    red = ImageTk.PhotoImage(im_resized)
    im = Image.open("images/blue.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    blue = ImageTk.PhotoImage(im_resized)
    im = Image.open("images/green.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    green = ImageTk.PhotoImage(im_resized)

    im = Image.open("images/yellow.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    yellow = ImageTk.PhotoImage(im_resized)

    im = Image.open("images/black.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    black = ImageTk.PhotoImage(im_resized)

    dronPictures = [red, blue, green, yellow]

    # nos conectamos al broker para recibir las ordenes de los que vuelan con la web app
    client = mqtt.Client("multiPlayerDash", transport="websockets")

    broker_address = "dronseetac.upc.edu"
    broker_port = 8000

    client.username_pw_set(
        'dronsEETAC', 'mimara1456.'
    )
    print('me voy a conectar')
    client.connect(broker_address, broker_port)
    print('Connected to dronseetac.upc.edu:8000')

    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(broker_address, broker_port)

    # me subscribo a cualquier mensaje  que venga del autopilot service
    client.subscribe('mobileApp/multiPlayerDash/#')
    client.loop_start()

    return ventana


if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.mainloop()
