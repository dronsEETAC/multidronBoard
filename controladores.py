import json
import math
import random
import threading
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

import paho.mqtt.client as mqtt

from dronLink.Dron import Dron
import geopy.distance
from geographiclib.geodesic import Geodesic
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
'''
Ejemplo de estructura de datos que representa un escenario para el juego de controladores.
El campo 'limits' marca el geofence de inclusión.
El campo 'areas' es un vector en el que cada elemento define el polígono asociado a uno de los 
jugadores. Si hay n jugadores solo se definen n-1 areas porque el area para el ultimo jugador
es la zona que queda libre en el geofence de inclusión.
El campo 'obstacles' es un vector en el que cada elemento representa un obstaculo que puede ser
un poligono o un circulo.

{
  "numPlayers": 3,
  "limits": [
    [
      41.27643116985451,
      1.9882303287666048
    ],
    [
      41.27661561304896,
      1.9890162160079683
    ],
    [
      41.2764029489919,
      1.989096682278415
    ],
    [
      41.27619230002484,
      1.9883698036353792
    ]
  ],
  "areas": [
    [
      [
        41.27643116985451,
        1.9882893373649324
      ],
      [
        41.276482572108634,
        1.9885186662357057
      ],
      [
        41.27634140259836,
        1.9885348028586236
      ],
      [
        41.276271858212134,
        1.9883604592726556
      ]
    ],
    [
      [
        41.27648452269629,
        1.9885374850676385
      ],
      [
        41.276587327080016,
        1.989010894958767
      ],
      [
        41.27645831763141,
        1.9890658802435723
      ],
      [
        41.27634845782181,
        1.9885401672766534
      ]
    ]
  ],
  "obstacles": [
    {
      "type": "polygon",
      "waypoints": [
        [
          41.276364584043975,
          1.9884033746168939
        ],
        [
          41.276439167769645,
          1.9884422666476098
        ],
        [
          41.27640590747008,
          1.9885844237253991
        ],
        [
          41.27631620536554,
          1.988538826172146
        ]
      ]
    },
    {
      "type": "circle",
      "lat": 41.27645227030725,
      "lon": 1.9887453562662927,
      "radius": 4.889039228138402
    },
    {
      "type": "circle",
      "lat": 41.27638373392762,
      "lon": 1.9888526446268884,
      "radius": 5.8681900677013585
    }
  ]
}


'''


# clase para gestionar los parámetros del dron
class ParameterManager:
    # con esta clase gestionamos los parámetros de un dron
    def __init__(self, window, dron):
        self.window = window
        self.dron = dron
        self.on_off = 0 # indica si el geofence está habilitado (1) o no (0)
        # preparo el color correspondiente al dron (identificado del 0 en adelante)
        color = 'red'


        self.managementFrame = tk.LabelFrame (window, text = 'Dron 1', fg=color)
        self.managementFrame.rowconfigure(0, weight=1)
        self.managementFrame.rowconfigure(1, weight=1)
        self.managementFrame.rowconfigure(2, weight=1)
        self.managementFrame.rowconfigure(3, weight=1)
        self.managementFrame.rowconfigure(4, weight=1)
        self.managementFrame.rowconfigure(5, weight=1)
        self.managementFrame.rowconfigure(6, weight=1)
        self.managementFrame.rowconfigure(7, weight=1)
        self.managementFrame.rowconfigure(8, weight=1)



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
        result = self.dron.getParams(parameters)
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
        self.NAV_SPEED_Sldr.set (self.dron.navSpeed)
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
        self.dron.setParams(parameters)
        self.dron.navSpeed = float(self.NAV_SPEED_Sldr.get())
        messagebox.showinfo( "showinfo", "Parámetros enviados", parent=self.window)


# esta función da la distancia en metros entre dos posiciones
def haversine(lat1, lon1, lat2, lon2):
    # Radio de la Tierra en metros
    R = 6371000

    # Convertir grados a radianes
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Fórmula del Haversine
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distancia en metros
    distance = R * c

    return distance



def whichArea (lat, lon, areas):
    # identifico en cuál de las areas está la posición que se recibe como parámetro
    point = Point(lat, lon)
    for i in range (0,len(areas)):
        polygon = Polygon(areas[i])
        if polygon.contains(point):
            return i
    # si no está en ninguna de la lista es que esta en la última área, que es la que ha quedado
    # sin cubrir con las areas anteriores
    return len(areas)

# procesado de los datos de telemetría
def processTelemetryInfo (id, telemetry_info):
    global  inArea, black, dronIcon
    global modoLab, altitudLab
    # recupero la posición en la que está el dron
    lat = telemetry_info['lat']
    lon = telemetry_info['lon']
    alt = telemetry_info['alt']
    modo = telemetry_info['flightMode']

    # averiguo en qué área esta el dron en este momento
    # otras funciones necesitan esa información
    inArea = whichArea (lat,lon, selectedScenario['areas'])


    # si es el primer paquete de telemetría ponemos en el mapa el icono de ese dron
    if not dronIcon:
        dronIcon = map_widget.set_marker(lat, lon,
                        icon=black,icon_anchor="center")
    # si no es el primer paquete entonces muevo el icono a la nueva posición
    else:
        dronIcon.set_position(lat,lon)

    # actrualizo la altitud
    if altitudLab:
        altitudLab['text'] = str (round(alt,2))
    # y el modo de vuelo
    if modoLab:
        modoLab['text'] = modo





########## Funciones para la creación del escenario  #################################

def createBtnClick ():
    global scenario
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

# iniciamos la creación de un obstáculo poligonal
def definePoly():
    global state, obstaclePoints, obstacle

    state = "definingObstaclePoly"
    obstaclePoints = 0
    obstacle = {
        'type': 'polygon',
        'waypoints': []
    }
    # informo del tema de los botones del mouse para que el usuario no se despiste
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo del ratón señala los waypoints\nCon el boton derecho cierra el polígono")

# iniciamos la creación de un obstáculo con forma de círculo
def defineCircle():
    global centerFixed, state, obstacle

    state = "definingObstacleCircle"
    obstacle = {
        'type': 'circle',
        "lat": None,
        "lon": None,
        "radius": None
    }
    centerFixed = False
    # informo del tema de los botones del mouse para que el usuario no se despiste
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo señala el centro\nCon el boton derecho marca el límite del círculo")

# capturamos el siguiente click del boton izquierdo del mouse
def getFenceWaypoint (coords):
    global centerFixed, state, limitPoints, areaPoints, obstaclePoints

    if state == "definingLimits":
        # estoy definiendo el polígono que delimita el espacio de vuelo,
        # que se convertira en un geofence de inclusión
        limitPoints = limitPoints+1
        # señalo el punto con un marcador negro, que guardo en una lista para poder eliminarlo más tarde
        limits.append(map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center"))

        if  limitPoints > 1:
            # ahora trazo la línea que une el nuevo punto con tel anterior
            limits.append(map_widget.set_path([escenarioControladores['limits'][-1], coords], color='gray', width=3))
        # añado el nuevo punto a la lista de puntos que delimitan el area de vuelo
        escenarioControladores['limits'].append(coords)

    elif state == "definingArea":
        # estoy definiendo el polígono que delimita una de las áreas de vuelo
        areaPoints = areaPoints + 1
        # añado un punto del color que corresponde al área que se está delimitando
        limits.append(map_widget.set_marker(coords[0], coords[1], icon=colorIcon, icon_anchor="center"))
        if areaPoints > 1:
            # ahora trazo la línea que une el nuevo punto con el punto anterior de ese área
            limits.append(map_widget.set_path([area[-1], coords], color=selectedColor, width=3))
        # añado el punto a la lista de puntos que delimitan el área que se está definiendo
        area.append(coords)

    elif state == "definingObstaclePoly":
        # estamos definiendo un obstáculo con forma poligonal
        obstaclePoints = obstaclePoints + 1
        # señalo el punto con el círculo negro
        limits.append(map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center"))
        if obstaclePoints > 1:
            # ahora trazo la línea que une el nuevo punto con el punto anterior del obstáculo
            limits.append(map_widget.set_path([obstacle['waypoints'][-1], coords], color='black', width=3))
        # añado el punto a la lista de puntos que delimitan el obstáculo se está definiendo
        obstacle['waypoints'].append(coords)

    elif state == "definingObstacleCircle":
        # estamos definiendo un obstáculo de tipo círculo
        if centerFixed:
            # ya habíamos señalado el centro del círculo. Ahora estamos esperando el click en el botón derecho
            # y no otro click en el izquierdo
            messagebox.showinfo("Error",
                                "Marca el límite con el botón derecho del mouse")
        else:
            # acabamos de señalar el centro del círculo
            # guardo los datos
            obstacle['lat'] = coords[0]
            obstacle['lon'] = coords[1]
            centerFixed = True
            # marco el centro con el icono negro
            limits.append(map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center"))

def closeFence(coords):
    # hemos clicado el boton derecho para cerrar un polígono o un círculo
    global polys, escenarioControladores, limits, state, limitsBtn, redPlayerBtn, bluePlayerBtn, greenPlayerBtn
    global areaPoints, area, obstacle


    if state == "definingLimits":
        # acabamos de cerrar los limites del area de vuelo.
        # Pintamos ese area del color del ultimo jugador, que es el que se quedará con los restos
        # no ocupados por las otras areas. Por ejemplo, si hay 3 jugadores, se definirán las areas del
        # jugador rojo y del azul. Para el jugador verde quedará el resto. En ese caso pintamos el espacio
        # de verde
        if numPlayers == 1:
            color = 'red'
        elif numPlayers == 2:
            color = 'blue'
        elif numPlayers == 3:
            color = 'green'
        else:
            color = 'yellow'
        polys.append(map_widget.set_polygon(escenarioControladores['limits'],
                                            outline_color=color,
                                            fill_color=color,
                                            border_width=3))
        # ya podemos eliminar los marcadores que hemos ido usando
        for element in limits:
            element.delete()
        limits = []
        limitsBtn ['text']="Listo"
        # ahora esperamos que el usuario empiece a definir las áreas de los diferentes jugadores
        state = "definigArea"


    elif state == "definingArea":
        # acabamos de cerrar el area de uno de los jugadores cuyo color esta en selectedColor
        polys.append(map_widget.set_polygon(area,
                                            outline_color=selectedColor,
                                            fill_color=selectedColor,
                                            border_width=3))
        # guardamos el area en el escenario
        escenarioControladores['areas'].append (area)
        # eliminamos los marcadores que hemos usado para definir este área
        for element in limits:
            element.delete()
        limits = []
        # nos preparamos para la siguiente área
        area = []
        areaPoints = 0

        if selectedColor == 'red':
            redPlayerBtn ["text"] ="Listo"
        elif selectedColor == 'blue':
            bluePlayerBtn["text"] = "Listo"
        elif selectedColor == 'green':
            greenPlayerBtn["text"] = "Listo"

    elif state == "definingObstaclePoly":
        # acabamos de cerrar un obstaculo poligonal
        polys.append(map_widget.set_polygon(obstacle['waypoints'],
                                            outline_color='black',
                                            fill_color='black',
                                            border_width=3))
        # añadimos el obstáculo al escenario
        escenarioControladores['obstacles'].append(obstacle)
        # eliminamos los marcadores que hemos usado para definir este obtáculo
        for element in limits:
            element.delete()
        limits = []

    elif state == "definingObstacleCircle":
        # acabamos de cerrar un obstaculo circular
        # calculamos el radio (distancia entre el centro y este punto en el que hemos clicado)
        center = (obstacle['lat'], obstacle['lon'])
        limit = (coords[0], coords[1])
        radius = geopy.distance.geodesic(center, limit).m
        obstacle['radius'] = radius
        # añado el obstáculo al escenario
        escenarioControladores['obstacles'].append(obstacle)
        # eliminamos los marcadores que hemos usado para definir este obtáculo
        for element in limits:
            element.delete()
        limits = []

        # como no se puede dibujar un circulo con la librería tkintermapview, creo un poligono que aproxime al círculo
        points = getCircle(obstacle['lat'], obstacle['lon'], radius)
        polys.append(map_widget.set_polygon(points,
                                            fill_color='black',
                                            outline_color="black",
                                            border_width=3))



# La siguiente función crea una imagen capturando el contenido de una ventana
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
            im = pyautogui.screenshot(region=(x+800, y+250, 730, 580))
            return im
        else:
            print('Window not found!')
    else:
        im = pyautogui.screenshot()
        return im

# guardamos los datos del escenario (imagen y fichero json)
def registerScenario ():
    global escenarioControladores

    # voy a guardar el escenario en el fichero con el nombre indicado en el momento de la creación
    jsonFilename = 'escenariosControladores/' + name.get() + "_"+str(numPlayers)+".json"

    with open(jsonFilename, 'w') as f:
        json.dump(escenarioControladores, f)
    # aqui capturo el contenido de la ventana que muestra el escenario que se acaba de definir
    im = screenshot('Gestión de escenarios')
    imageFilename = 'escenariosControladores/'+name.get()+ "_"+str(numPlayers)+".png"
    im.save(imageFilename)
    # limpio el mapa
    clear()

# genera el poligono que aproxima al círculo
def getCircle ( lat, lon, radius):
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

def createPlayer (color):
    # aqui vamos a crear el escenario para uno de los jugadores, el que tiene el color indicado como parámetro
    global colorIcon
    global selectedColor, scenario, state, area, areaPoints
    # nos preparamos para definir el área de este jugador
    state = "definingArea"
    selectedColor = color
    areaPoints = 0
    area = []
    if color == 'red':
        colorIcon = red
    elif color == 'blue':
        colorIcon = blue
    elif color == 'green':
        colorIcon = green

    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo del ratón señala los límites de area. \nCon el boton derecho cierra el polígono")

def defineLimits ():
    # vamos a empezar a definir los límites del área de vuelo
    global state, limitPoints
    state = 'definingLimits'
    limitPoints = 0
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo del ratón señala los límites de escenario. \nCon el boton derecho cierra el polígono")

# elijo el número de jugadores
def selectNumPlayers (num):
    global redPlayerBtn, bluePlayerBtn, greenPlayerBtn, yellowPlayerBtn
    global escenarioControladores
    global numPlayers
    global limitsBtn

    numPlayers = num

    # empezamos a preparar la estructura de datos del multi escenario
    escenarioControladores = {
        'numPlayers': num,  # numero de jugadores
        'limits': [],       # limites del escenario (geofence de inclusion)
        'areas': [],        # areas para num-1 jugadores (el area del ultimo es lo que quede sin cubrir)
        'obstacles': []     # geofences de exclusion
    }
    # colocamos los botones que permiten crear el escenario para cada uno de los jugadores
    limitsBtn = tk.Button(selectPlayersFrame, text="Marca los límites del escenario", bg="gray", fg='white',
                             command=defineLimits)
    limitsBtn.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    if num == 1:
        pass
    if num == 2:
        redPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rojo", bg="red", fg='white',
                                command = lambda: createPlayer('red'))
        redPlayerBtn.grid(row=3, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    if num == 3:
        redPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rojo", bg="red",
                                 fg='white',
                                 command=lambda: createPlayer('red'))
        redPlayerBtn.grid(row=3, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

        bluePlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador azul", bg="blue",
                                  fg='white',
                                  command=lambda: createPlayer('blue'))
        bluePlayerBtn.grid(row=4, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    if num == 4:
        redPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador rojo", bg="red",
                                 fg='white',
                                 command=lambda: createPlayer('red'))
        redPlayerBtn.grid(row=3, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

        bluePlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador azul", bg="blue",
                                  fg='white',
                                  command=lambda: createPlayer('blue'))
        bluePlayerBtn.grid(row=4, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
        greenPlayerBtn = tk.Button(selectPlayersFrame, text="Crea el escenario para el jugador verde", bg="green",
                                   fg='white',
                                   command=lambda: createPlayer('green'))
        greenPlayerBtn.grid(row=5, column=0,columnspan = 4,  padx=5, pady=5, sticky=tk.N + tk.E + tk.W)



############################ Funciones para seleccionar el escenario ##########################################
def selectBtnClick ():
    global scenarios, current, polys
    scenarios = []
    # limpio el mapa
    clear()
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

# una vez elegido el numero de jugadores mostramos los escenarios que hay para ese número de jugadores
def selectScenarios (num):
    global scenarios, current
    global numPlayers
    numPlayers = num

    # cargamos en una lista las imágenes de todos los escenarios disponibles
    # para el número de jugadores indicado
    scenarios = []
    for file in glob.glob("escenariosControladores/*_"+str(num)+".png"):
        scene = Image.open(file)
        scene = scene.resize((300, 200))
        scenePic = ImageTk.PhotoImage(scene)
        # en la lista guardamos el nombre que se le dió al escenario y la imagen
        scenarios.append({'name': file.split('.')[0], 'pic': scenePic})

    if len(scenarios) > 0:
        # mostramos ya en el canvas la imagen del primer multi escenario
        scenarioCanvas.create_image(0, 0, image=scenarios[0]['pic'], anchor=tk.NW)
        current = 0
        # no podemos seleccionar el anterior porque no hay anterior
        prevBtn['state'] = tk.DISABLED
        # y si solo hay 1 multi escenario tampoco hay siguiente
        if len(scenarios) == 1:
            nextBtn['state'] = tk.DISABLED
        else:
            nextBtn['state'] = tk.NORMAL

        sendBtn['state'] = tk.DISABLED
    else:
        messagebox.showinfo("showinfo",
                            "No hay escenarios para elegir")

# mostrar anterior
def showPrev ():
    global current
    current = current -1
    # mostramos el multi escenario anterior
    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
    # deshabilitamos botones si no hay anterior o siguiente
    if current == 0:
        prevBtn['state'] = tk.DISABLED
    else:
        prevBtn['state'] = tk.NORMAL
    if current == len(scenarios) - 1:
        nextBtn['state'] = tk.DISABLED
    else:
        nextBtn['state'] = tk.NORMAL

# mostrar siguiente
def showNext ():
    global current
    current = current +1
    # muestro el siguiente
    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
    # deshabilitamos botones si no hay anterior o siguiente
    if current == 0:
        prevBtn['state'] = tk.DISABLED
    else:
        prevBtn['state'] = tk.NORMAL
    if current == len(scenarios) - 1:
        nextBtn['state'] = tk.DISABLED
    else:
        nextBtn['state'] = tk.NORMAL

# Limpiamos el mapa
# Se trata de borrar todos los elementos de la lista polys que contiene los polígonos que hemos ido dibujando
def clear ():
    global polys
    # también tengo que borrar el texto de la caja para el nombre
    name.set ("")
    for poly in polys:
        poly.delete()
    polys = []

# borramos el escenario que esta a la vista
def deleteScenario ():
    global current
    msg_box = messagebox.askquestion(
        "Atención",
        "¿Seguro que quieres eliminar este escenario?",
        icon="warning",
    )
    if msg_box == "yes":
        # borro los dos ficheros que representan el multi escenario seleccionado
        os.remove(scenarios[current]['name'] + '.png')
        os.remove(scenarios[current]['name'] + '.json')
        scenarios.remove (scenarios[current])
        # muestro el multi escenario anterior (o el siguiente si no hay anterior o ninguno si tampoco hay siguiente)
        if len (scenarios) != 0:
            if len (scenarios) == 1:
                # solo queda un escenario
                current = 0
                scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
                prevBtn['state'] = tk.DISABLED
                nextBtn['state'] = tk.DISABLED
            else:
                # quedan más multi escenarios
                if current == 0:
                    # hemos borrado el primer multi escenario de la lista. Mostramos el nuevo primero
                    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
                    prevBtn['state'] = tk.DISABLED
                    if len (scenarios) > 1:
                        nextBtn['state'] = tk.NORMAL
                else:
                    # mostramos
                    scenarioCanvas.create_image(0, 0, image=scenarios[current]['pic'], anchor=tk.NW)
                    prevBtn['state'] = tk.NORMAL
                    if current == len (scenarios) -1:
                        nextBtn['state'] = tk.DISABLED
                    else:
                        nextBtn['state'] = tk.NORMAL
            clear()

# dibujamos en el mapa el multi escenario
def drawScenario (scenario):
    global polys
    # borro los elementos que haya en el mapa
    for poly in polys:
        poly.delete()

    numPlayers = scenario['numPlayers']
    if numPlayers == 1:
        polys.append(map_widget.set_polygon(scenario['limits'],
                                            outline_color='red',
                                            fill_color='red',
                                            border_width=3))

    elif numPlayers == 2:
        polys.append(map_widget.set_polygon(scenario['limits'],
                                            outline_color='blue',
                                            fill_color='blue',
                                            border_width=3))
        polys.append(map_widget.set_polygon(scenario['areas'][0],
                                            outline_color='red',
                                            fill_color='red',
                                            border_width=3))
    elif numPlayers == 3:
        polys.append(map_widget.set_polygon(scenario['limits'],
                                            outline_color='green',
                                            fill_color='green',
                                            border_width=3))
        polys.append(map_widget.set_polygon(scenario['areas'][0],
                                            outline_color='red',
                                            fill_color='red',
                                            border_width=3))
        polys.append(map_widget.set_polygon(scenario['areas'][1],
                                            outline_color='blue',
                                            fill_color='blue',
                                            border_width=3))
    elif numPlayers == 4:
        polys.append(map_widget.set_polygon(scenario['limits'],
                                            outline_color='yellow',
                                            fill_color='yellow',
                                            border_width=3))
        polys.append(map_widget.set_polygon(scenario['areas'][0],
                                            outline_color='red',
                                            fill_color='red',
                                            border_width=3))
        polys.append(map_widget.set_polygon(scenario['areas'][1],
                                            outline_color='blue',
                                            fill_color='blue',
                                            border_width=3))
        polys.append(map_widget.set_polygon(scenario['areas'][2],
                                            outline_color='green',
                                            fill_color='green',
                                            border_width=3))


    for obstacle in scenario['obstacles']:
        if obstacle['type'] == 'polygon':
            polys.append(map_widget.set_polygon(obstacle['waypoints'],
                                                    outline_color="black",
                                                    fill_color="black",
                                                    border_width=3))
        else:
            poly = getCircle(obstacle['lat'], obstacle['lon'], obstacle['radius'])
            polys.append(map_widget.set_polygon(poly,
                                                    outline_color="black",
                                                    fill_color="black",
                                                    border_width=3))

# seleccionar el escenario que está a la vista
def selectScenario():
    global polys, selectedScenario, numPlayers
    # limpio el mapa
    for poly in polys:
        poly.delete()
    # cargamos el fichero json con el multi escenario seleccionado (el que está en la posición current de la lista9
    f = open(scenarios[current]['name'] +'.json')
    selectedScenario = json.load (f)
    # dibujo el escenario
    drawScenario(selectedScenario)
    # habilito el botón para enviar el escenario al enjambre
    sendBtn['state'] = tk.NORMAL

# envia los datos del multi escenario seleccionado al enjambre
def sendScenario ():
    # enviamos el escenario al dron
    # tenemos que construir la estructura de datos necesaria

    global dron
    global selectedScenario
    scenario = []
    waypoints = []
    for waypoint in selectedScenario['limits']:
        waypoints.append ({
            'lat': waypoint[0],
            'lon': waypoint[1]
        })

    scenario.append (
        {
            'type':'polygon',
            'waypoints': waypoints
        }
    )
    for obstacle in selectedScenario ['obstacles']:
        if obstacle['type'] == 'circle':
            scenario.append (obstacle)
        else:
            scenario.append ( {
                'type':'polygon',
                'waypoints': [{'lat': lat, 'lon':lon} for (lat,lon) in obstacle['waypoints']]
            })

    dron.setScenario (scenario)
    sendBtn['bg'] = 'green'

# carga el multi escenario que hay ahora en el enjambre
# NO ESTA OPERATIVO
def loadScenario ():
    # ESTO NO ESTA OPERATIVO
    # voy a mostrar el escenario que hay cargado en el dron
    global connected, dron
    if not connected:
        dron = Dron()
        connection_string = 'tcp:127.0.0.1:5763'
        baud = 115200
        dron.connect(connection_string, baud)
        connected = True
    scenario = dron.getScenario()
    if scenario:
        drawScenario(scenario)
    else:
        messagebox.showinfo("showinfo",
                        "No hay ningún escenario cargado en el dron")

def toggleHeading ():
    # según esté el boton haré una cosa u otra
    global toggleHeadingBtn, dron
    if 'Fijar' in toggleHeadingBtn['text']:
        toggleHeadingBtn['text'] = 'Desbloquear heading'
        dron.fixHeading ()
    else:
        toggleHeadingBtn['text'] = 'Fijar heading'
        dron.unfixHeading ()

# me contecto al dron
def connect ():
    global connected, dron, dronIcon
    global altitud, numPlayers
    global controlesFrame, telemetriaFrame
    global altitudLab, modoLab
    global toggleHeadingBtn


    if not connected:
        dron = Dron(0)

        if connectOption.get () == 'Simulation':
            # nos al simulador
            connectionString = "tcp:127.0.0.1:5763"
            baud = 115200

        else:
            # nos conectaremos al dron real mediante la radio de telemetría
            # el puerto lo ha escrito el usuario y está en comPorts
            connectionString = comPorts
            baud = 57600

        dron.connect(connectionString, baud)
        dron.changeNavSpeed(1)
        dron.send_telemetry_info(processTelemetryInfo)
        dronIcon = None

        # colocamos los botones de control en el frame que toca
        tk.Button(controlesFrame, bg='red', fg='white', text='Aterrizar',
                  command=lambda : dron.Land(blocking=False)) \
            .grid(row=0, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        tk.Button(controlesFrame, bg='red', fg='white', text='Modo guiado',
                  command=lambda : dron.setFlightMode('GUIDED')) \
            .grid(row=1, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        tk.Button(controlesFrame, bg='red', fg='white', text='Modo break',
                  command=lambda: dron.setFlightMode('BRAKE')) \
            .grid(row=2, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        toggleHeadingBtn = tk.Button(controlesFrame, bg='red', fg='white', text='Fijar heading',
                  command= toggleHeading)
        toggleHeadingBtn.grid(row=3, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        # colocamos las labels para mostrar los datos de telemetría
        altitudLab = tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid")
        altitudLab.grid(row=0, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
        modoLab = tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid")
        modoLab.grid(row=1, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

        connected = True
        connectBtn['bg'] = 'green'



################### Funciones para supervisar el escenario #########################
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
    global dron
    # voy a mostrar la ventana de gestión de los parámetros
    parameterManagementWindow = tk.Tk()
    parameterManagementWindow.title("Gestión de parámetros")
    parameterManagementWindow.rowconfigure(0, weight=1)
    parameterManagementWindow.rowconfigure(1, weight=1)
    parameterManagementWindow.columnconfigure(0, weight=1)

    dronManager = ParameterManager(parameterManagementWindow, dron)
    dronFrame = dronManager.buildFrame()
    dronFrame.grid(row=0, column=0, padx=50, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    tk.Button(parameterManagementWindow, text='Cerrar', bg="dark orange",
              command=lambda: parameterManagementWindow.destroy()) \
        .grid(row=1, column=0, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

    parameterManagementWindow.mainloop()

def showQR():
    global QRimg
    QRWindow = tk.Toplevel()
    QRWindow.title("Código QR para mobile web app")
    QRWindow.rowconfigure(0, weight=1)
    QRWindow.rowconfigure(1, weight=1)
    QRWindow.columnconfigure(0, weight=1)

    QRimg = Image.open("images/QR.png")
    QRimg = ImageTk.PhotoImage(QRimg)
    label = tk.Label(QRWindow, image=QRimg)
    label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E +tk.S+ tk.W)

    closeBtn = tk.Button(QRWindow, text="Cerrar", bg="dark orange", command = lambda: QRWindow.destroy())
    closeBtn.grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E +tk.S+tk.W)

    QRWindow.mainloop()




def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK Returned code=", rc)
    else:
        print("Bad connection Returned code=", rc)

def publish_event (id, event):
    # al ser un dron identificado, la librería nos pasa siempre en primer lugar el identificador del dron
    global client
    # envio el evento (que puede ser 'flying', 'landed' o 'atHome' al dron que tiene el control
    # es decir, al dron cuyo id coincide con el area en el que está el dron
    client.publish('multiPlayerDash/mobileApp/'+event+'/'+str(inArea))
    if event == 'flying':
        # en este caso comunico a todos que el dron esté en el aire para que lo reflejen así en la interfez
        # de usuario del movil
        # ESTO SEGURAMENTE DEBERÍA HACERLO CON LOS OTROS EVENTOS PARA QUE TODOS LOS JUGADORES RECIBAN LA INFORMACIÓN
        # DE MOMENTO NO LO HAGO PORQUE HAY QUE TOCAR LA WEB APP
        client.publish('multiPlayerDash/mobileApp/flyingForAll')


# aqui recibimos las publicaciones que hacen las web apps desde las que están jugando
def on_message(client, userdata, message):
    # el formato del topic siempre será:
    # multiPlayerDash/mobileApp/COMANDO/NUMERO
    # el número normalmente será el número del jugador (entre el 0 y el 3)
    # excepto en el caso de la petición de conexión
    global playersCount, dron
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
            # devolvemos el número aleatorio recibido para que solo tenga en cuenta este mensaje el jugador que
            # se acaba de conectar
            client.publish('multiPlayerDash/mobileApp/accepted/'+randomId, playersCount)
            playersCount = playersCount+1

    if command == 'arm_takeOff':
        # en este comando y en los siguientes, el último trozo del topic identifica al jugador que hace la petición
        # solo atenderemos la petición si el identificador coincide con el área en el que está el dron
        id = int (parts[3])
        if id == inArea:
            if dron.state == 'connected':
                dron.arm()
                # operación no bloqueante. Cuando acabe publicará el evento correspondiente
                dron.takeOff(5, blocking=False, callback=publish_event, params='flying')

    if command == 'go':
        id = int (parts[3])
        if id == inArea:
            if dron.state == 'flying':
                direction = message.payload.decode("utf-8")
                dron.go(direction)

    if command == 'Land':
        id = int (parts[3])
        if id == inArea:
            if dron.state == 'flying':
                # operación no bloqueante. Cuando acabe publicará el evento correspondiente
                dron.Land(blocking=False, callback=publish_event, params='landed')

    if command == 'RTL':
        id = int (parts[3])
        if id == inArea:
            if dron.state == 'flying':
                # operación no bloqueante. Cuando acabe publicará el evento correspondiente
                dron.RTL(blocking=False, callback=publish_event, params='atHome')




def crear_ventana():

    global map_widget
    global createBtn,selectBtn, superviseBtn, createFrame, name, selectFrame, scene, scenePic,scenarios, current
    global superviseFrame
    global prevBtn, nextBtn, sendBtn, connectBtn
    global scenarioCanvas
    global i_wp, e_wp
    global polys, limits
    global connected
    global selectPlayersFrame
    global red, blue, green, yellow, black
    global connectOption
    global playersCount
    global client
    global QRimg
    global controlesFrame, telemetriaFrame
    global altitudLab, modoLab


    playersCount = 0
    connected = False


    # para guardar mrcadores del mapa y luego poder borrarlos
    polys = []
    limits = []


    ventana = tk.Tk()
    ventana.title("Gestión de escenarios")
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

    ################################# frame para crear escenario  ###################################################
    createFrame = tk.LabelFrame(controlFrame, text='Crear escenario')
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

    tk.Label (createFrame, text='Escribe el nombre aquí')\
        .grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # el nombre se usará para poner nombre al fichero con la imagen y al fichero json con el escenario
    name = tk.StringVar()
    tk.Entry(createFrame, textvariable=name)\
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    selectPlayersFrame = tk.LabelFrame(createFrame, text='Jugadores')
    selectPlayersFrame.grid(row=2, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    selectPlayersFrame.rowconfigure(0, weight=1)
    selectPlayersFrame.rowconfigure(1, weight=1)
    selectPlayersFrame.rowconfigure(2, weight=1)
    selectPlayersFrame.rowconfigure(3, weight=1)
    selectPlayersFrame.rowconfigure(4, weight=1)
    selectPlayersFrame.rowconfigure(5, weight=1)
    selectPlayersFrame.rowconfigure(6, weight=1)

    selectPlayersFrame.columnconfigure(0, weight=1)
    selectPlayersFrame.columnconfigure(1, weight=1)
    selectPlayersFrame.columnconfigure(2, weight=1)
    selectPlayersFrame.columnconfigure(3, weight=1)
    tk.Label (selectPlayersFrame, text = 'Selecciona el número de jugadores').\
        grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="1", bg="dark orange", command = lambda:  selectNumPlayers (1))\
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="2", bg="dark orange", command=lambda: selectNumPlayers(2)) \
        .grid(row=1, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="3", bg="dark orange", command=lambda: selectNumPlayers(3)) \
        .grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectPlayersFrame, text="4", bg="dark orange", command=lambda: selectNumPlayers(4)) \
        .grid(row=1, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    # los obstacilos son fences de exclusión y pueden ser también polígonos o círculos
    # el parámetro 2 en el command indica que son fences de exclusión
    obstacleFrame = tk.LabelFrame(createFrame, text='Definición de los obstaculos del escenario')
    obstacleFrame.grid(row=3, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    obstacleFrame.rowconfigure(0, weight=1)
    obstacleFrame.columnconfigure(0, weight=1)
    obstacleFrame.columnconfigure(1, weight=1)

    polyObstacleBtn = tk.Button(obstacleFrame, text="Polígono", bg="dark orange", command =  definePoly)
    polyObstacleBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    circleObstacleBtn = tk.Button(obstacleFrame, text="Círculo", bg="dark orange", command= defineCircle)
    circleObstacleBtn.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    registerBtn = tk.Button(createFrame, text="Registra escenario", bg="dark orange", command = registerScenario)
    registerBtn.grid(row=4, column=0, padx=5, pady=5, sticky=tk.N +tk.E + tk.W)

    clearBtn = tk.Button(createFrame, text="Limpiar", bg="dark orange", command=clear)
    clearBtn.grid(row=5, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    ################################ frame para seleccionar escenarios ############################################
    selectFrame = tk.LabelFrame(controlFrame, text='Selecciona escenario')
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
    tk.Button(selectFrame, text="1", bg="dark orange", command = lambda:  selectScenarios (1))\
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="2", bg="dark orange", command=lambda: selectScenarios(2)) \
        .grid(row=1, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="3", bg="dark orange", command=lambda: selectScenarios(3)) \
        .grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectFrame, text="4", bg="dark orange", command=lambda: selectScenarios(4)) \
        .grid(row=1, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    # en este canvas se mostrarán las imágenes de los escenarios disponibles
    scenarioCanvas = tk.Canvas(selectFrame, width=300, height=200, bg='grey')
    scenarioCanvas.grid(row = 2, column=0, columnspan=4, padx=5, pady=5)

    prevBtn = tk.Button(selectFrame, text="<<", bg="dark orange", command = showPrev)
    prevBtn.grid(row=3, column=0, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)
    selectScenarioBtn = tk.Button(selectFrame, text="Seleccionar", bg="dark orange", command = selectScenario)
    selectScenarioBtn.grid(row=3, column=1, columnspan = 2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    nextBtn = tk.Button(selectFrame, text=">>", bg="dark orange", command = showNext)
    nextBtn.grid(row=3, column=3, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)

    # La función de cargar el multi escenario que hay en ese momento en los drones no está operativa aún
    loadBtn = tk.Button(selectFrame, text="Cargar el escenario que hay en el dron", bg="dark orange", state = tk.DISABLED, command=loadScenario)
    loadBtn.grid(row=4, column=0,columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

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
        comPorts = askstring('Puerto', "Indica el puerto COM (por ejemplo COM21)")

    option2 = tk.Radiobutton(connectFrame, text="Producción", variable=connectOption, value="Production",
                             command=ask_Ports)
    option2.grid(row=1, column=1, padx=5, pady=3, sticky=tk.N + tk.S + tk.W)


    sendBtn = tk.Button(selectFrame, text="Enviar escenario", bg="dark orange", command=sendScenario)
    sendBtn.grid(row=6, column=0,columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    deleteBtn = tk.Button(selectFrame, text="Eliminar escenario", bg="red", fg = 'white', command = deleteScenario)
    deleteBtn.grid(row=7, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N +  tk.E + tk.W)

    ########################## frame para supervisar ####################################################
    superviseFrame = tk.LabelFrame(controlFrame, text='Supervisar vuelos')
    # la visualización del frame se hace cuando se clica el botón de supervisar
    # superviseFrame.grid(row=1, column=0,  columnspan=3, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    superviseFrame.rowconfigure(0, weight=1)
    superviseFrame.rowconfigure(1, weight=1)
    superviseFrame.rowconfigure(2, weight=1)
    superviseFrame.rowconfigure(3, weight=1)


    superviseFrame.columnconfigure(0, weight=1)
    superviseFrame.columnconfigure(1, weight=1)
    superviseFrame.columnconfigure(2, weight=1)
    superviseFrame.columnconfigure(3, weight=1)

    parametersBtn = tk.Button(superviseFrame, text="Ajustar parámetros", bg="dark orange", command=adjustParameters)
    parametersBtn.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    controlesFrame = tk.LabelFrame(superviseFrame, text='Controles')
    controlesFrame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    controlesFrame.rowconfigure(0, weight=1)
    controlesFrame.rowconfigure(1, weight=1)
    controlesFrame.rowconfigure(2, weight=1)
    controlesFrame.rowconfigure(3, weight=1)
    controlesFrame.columnconfigure(0, weight=1)


    # debajo de este label colocaremos las alturas en las que están los drones
    # las colocaremos cuando sepamos cuántos drones tenemos en el enjambre
    telemetriaFrame = tk.LabelFrame(superviseFrame, text='Telemetría (altitud y modo de vuelo')
    telemetriaFrame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    telemetriaFrame.rowconfigure(0, weight=1)
    telemetriaFrame.rowconfigure(1, weight=1)
    telemetriaFrame.columnconfigure(0, weight=1)
    # Aqui guardaremos los labels para mostrar los datos de telemetría
    altitudLab = None
    modoLab = None

    showQRBtn = tk.Button(superviseFrame, text="Mostrar código QR de mobile web APP", bg="dark orange", command=showQR)
    showQRBtn.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

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
    map_widget.add_right_click_menu_command(label="Cierra el fence", command=closeFence, pass_coords=True)
    map_widget.add_left_click_map_command(getFenceWaypoint)


    # iconos para marcar áreas, cada una con su color
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



    # nos conectamos al broker para recibir las ordenes de los que vuelan con la web app
    clientName = "multiPlayerDash" + str(random.randint(1000, 9000))
    client = mqtt.Client(clientName,transport="websockets")


    broker_address = "dronseetac.upc.edu"
    broker_port = 8000

    client.username_pw_set(
        'dronsEETAC', 'mimara1456.'
    )
    print('me voy a conectar')
    client.connect(broker_address, broker_port )
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
