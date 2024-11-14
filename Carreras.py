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
from ParameterManager import ParameterManager
from AutopilotControllerClass import AutopilotController

'''
El formato en que se guarda un circuito es simplemente una lista de puntos que definen las zonas
del circuito. Los 4 primeros puntos definen la primera zona. A partir de ahí, los dos siguientes
puntos, junto con los dos anteriores, definen la zona siguiente.
'''

##################### Procesado de los datos de telemetría
def runAgain (id, params):
    # cuando el dron atrapado haya aterrizado vengo aquí
    i = params[0] # dron que a pillado al atrapado
    flightMode = params[1] # modo de vuelo que tenía el dron que ha pillado (y que ahora está en BRAKE)
    swarm[i].setFlightMode(flightMode) # recupero el modo que tenía
    j = params[2] # dron que ha sido atrapado
    dronIcons[j].delete() # elimino el icono del dron atrapado
    # coloco el icono del dron atrapado (una circunferencia del color adecuado en vez de un circulo)
    # ATENCION: no importa dónde coloque el icono porque pronto tendremos un paquete de telemetría del dron j
    # que movera el icono al sitio en el que está realmente el dron
    dronIcons[j] = map_widget.set_marker(0, 0,
                                         icon=dronPictures_lines[j], icon_anchor="center")

def processTelemetryInfo (id, telemetry_info):
    global dronIcons, myZone, myZoneWidget
    # recupero la posición en la que está el dron
    lat = telemetry_info['lat']
    lon = telemetry_info['lon']
    alt = telemetry_info['alt']
    modo = telemetry_info['flightMode']


    # si es el primer paquete de este dron entonces ponemos en el mapa el icono de ese dron
    if not dronIcons[id]:
        dronIcons[id] = map_widget.set_marker(lat, lon,
                        icon=dronPictures[id],icon_anchor="center")
    # si no es el primer paquete entonces muevo el icono a la nueva posición
    else:
        dronIcons[id].set_position(lat,lon)
    # actrualizo la altitud y el modo de vuelo
    altitudes[id]['text'] = str(round(alt, 2))
    modos[id]['text'] = modo

    # si estamos ya en carrera y este dron no ha sido pillado aún...
    if running and myZone[id] != -1:
        # miro en qué zona está
        point = Point(lat,lon)
        for i in range(0, len(zones)):
            polygon = Polygon([zones[i][0],zones[i][1],zones[i][2],zones[i][3]])
            if polygon.contains(point):
                # está en la zona i
                if myZone[id] != i:
                    # ha cambiado de zona
                    myZone[id] = i
                    # elimino el rectangulo que colorea la zona que abandona
                    if myZoneWidget[id]:
                        myZoneWidget[id].delete()
                    # coloreo la zona en la que entra
                    myZoneWidget[id] = map_widget.set_polygon([zones[i][0],zones[i][1],zones[i][2],zones[i][3]],
                                                              outline_color=colors[id], fill_color = colors[id] ,
                                                              border_width=1)

        # veamos si el dron  ha atrapado a alguien
        if myZone [id]:
            for j in range(0, len(swarm)):
                if id!= j and myZone[j] and  myZone[j] != -1:
                    # veamos si el dron id ha atrapado al dron j
                    if (myZone[id] + 1) % len(zones) == myZone[j]:
                        # si que lo ha atrapado
                        # me guardo el modo de vuelo para recuperarlo luego
                        # (será GUIDED si volamos con el movil o LOITER si volamos con la emisora)
                        flightMode =  swarm[id].flightMode
                        # detengo el dron
                        swarm[id].setFlightMode ('BRAKE')
                        # marco el dron que ha sido alcanzado
                        myZone [j] = -1
                        # y lo hago arerrizar
                        swarm[j].Land(blocking=False, callback = runAgain, params = [id,flightMode,j])
                        # elimino la zona coloreada del dron atrapado
                        myZoneWidget[j].delete()


############# Funciones para crear el circuito  ###########################################

def createBtnClick ():

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


def startDesign():
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


def fixError():
    # a veces pasa algo raro al clicar el mouse y se descontrola, quedando afectada la primera zona
    # aqui eliminamos los datos de la primera zona para eliminar ese mal funcionamiento
    global points, zones, polys

    zones = zones[1:]
    polys[0].delete()
    polys = polys[1:]
    points = points[2:]


def deleteLast():
    # elimino el resultado del ultimo click
    global points, zones, polys, markers

    if len(points) > 4 and len(points) % 2 == 0:
        points.pop()
        points.pop()
        zones.pop()
        item = polys.pop()
        item.delete()
    else:
        points.pop()
        item = markers.pop()
        item.delete()


def getFenceWaypoint(coords):
    # los 4 primeros puntos que marque definen la primera zona del cicuito
    # a partir de ahí cada dos nuevos puntos defienen la siguiente zona
    global markers, zones, closed, points, polys
    # acabo de clicar con el botón izquierdo
    if not closed:
        points.append(coords)
        marker = map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center")
        markers.append(marker)
        if len(points) == 4:
            # acabo de definir la primera zona
            polys.append(map_widget.set_polygon(points, outline_color='black', border_width=1))
            for marker in markers:
                marker.delete()
            markers = []
            zone = [point for point in points]
            zones.append(zone)
        elif len(points) > 4 and len(points) % 2 == 0:
            # acabo de definir el segundo punto que define la siguiente zona
            pos = len(points)
            # los 4 ultimos puntos marcados definen la siguiente zona
            polys.append(map_widget.set_polygon(points[pos - 4: pos], outline_color='black', border_width=1))
            for marker in markers:
                marker.delete()
            markers = []
            zone = [point for point in points[pos - 4: pos]]
            zones.append(zone)
    else:
        # esto me sirve de control
        # si una vez cerrado el circuito clico en una zona me pone en consola el numero de zona
        point = Point(coords[0], coords[1])
        for i in range(0, len(zones)):
            polygon = Polygon(zones[i])
            if polygon.contains(point):
                print(' Esta en la zona ', i)


def closeCircuit(coords):
    # al clicar el boton derecho indico que quiero cerrar el circuito
    # para eso debo definir la siguiente zona, que está delimitada por los dos ultimos puntos que he marcado y los
    # dos primeros puntos que marqué
    global closed
    pos = len(points)
    # La ordenación de los puntos para delimitar la ultima zona depende de la paridad del número de zonas
    if pos % 4 == 0:
        polys.append(
            map_widget.set_polygon([points[pos - 2], points[pos - 1], points[0], points[1]], outline_color='black',
                                   border_width=1))
        zones.append([points[pos - 2], points[pos - 1], points[0], points[1]])
    else:
        polys.append(
            map_widget.set_polygon([points[pos - 2], points[pos - 1], points[1], points[0]], outline_color='black',
                                   border_width=1))
        zones.append([points[pos - 2], points[pos - 1], points[1], points[0]])

    # una vez definidas las zonas ya puedo determinar los bordes del circuito.
    # El borde exterior se convertirá en su momento en un geofence de inclusión
    # y el borde interior en un geofence de exclusión

    i = 0
    external = []
    internal = []
    if len(zones) % 2 == 0:
        while i < len(points):
            external.append(points[i])
            external.append(points[i + 3])
            internal.append(points[i + 1])
            internal.append(points[i + 2])
            i = i + 4
    else:
        while i < len(points) - 2:
            external.append(points[i])
            external.append(points[i + 3])
            internal.append(points[i + 1])
            internal.append(points[i + 2])
            i = i + 4
        external.append(points[len(points) - 2])
        internal.append(points[len(points) - 1])

    # pinto en rojo el borde exterior
    polys.append(map_widget.set_polygon(external, outline_color='red',
                                        border_width=3))
    # pinto en azul el borde interior
    polys.append(map_widget.set_polygon(internal, outline_color='blue',
                                        border_width=3))
    closed = True


def cleanDesign():
    global polys, points, markers, zones, closed
    for poly in polys:
        poly.delete()
    points = []
    markers = []
    zones = []
    polys = []
    closed = False


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
            im = pyautogui.screenshot(region=(x + 800, y + 250, 750, 580))
            return im
        else:
            print('Window not found!')
    else:
        im = pyautogui.screenshot()
        return im


# guardamos los datos del escenario (imagen y fichero json)
def registerCircuit():
    # voy a guardar el multi escenario en el fichero con el nombre indicado en el momento de la creación
    jsonFilename = 'circuits/' + name.get() + ".json"

    with open(jsonFilename, 'w') as f:
        json.dump(points, f)
    # aqui capturo el contenido de la ventana que muestra el Camp Nou (zona del cesped, que es dónde está el escenario)
    im = screenshot('Gestión de circuitos')
    imageFilename = 'circuits/' + name.get() + ".png"
    im.save(imageFilename)

    cleanDesign()


def publish_landed(id):
    client.publish('multiPlayerDash/mobileApp/landed/' + str(id))


def RTL4Land(id):
    # esto es lo que quiero que haga el autopilot service (ordenar un Land)
    # en caso de que se clique Return to Launch en un movil
    dron = swarm[id]
    if dron.state == 'flying':
        # operación no bloqueante. Cuando acabe publicará el evento correspondiente
        dron.Land(blocking=False, callback=publish_landed)


def setNumPlayers(n):
    global numPlayers, client, swarm
    numPlayers = n
    # voy a cambiar la funcionalidad del boton de Return to Launch de la web app
    # un RTL es peligroso porque puede provocar un choque de drones
    # el boton hará un land
    additionalEvents = [
        {'event': 'RTL', 'method': RTL4Land}
    ]
    autopilotService = AutopilotController(numPlayers, numPlayers, additionalEvents)
    client, swarm = autopilotService.start()



############################ Funciones para seleccionar el circuito ##########################################
def selectBtnClick ():
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
    # reconstruyo las zonas
    # la primera está formada por los 4 primeros puntos
    # las siguientes quedan definidas por los dos ultimos puntos de la zona
    # anterior y los dos puntos siguientes de la lista
    zones = []
    i=0
    while i < len(selectedCircuitPoints) -2:
        zone = []
        for point in selectedCircuitPoints[i:i + 4]:
            zone.append ((point[0], point[1]))
        zones.append(zone)
        polys.append(map_widget.set_polygon(zone, outline_color='black', border_width=1))
        i = i+2

    # la ultima zona se define dependiendo de la paridad del número de puntos
    pos = len(selectedCircuitPoints)
    if pos % 4 == 0:
        zone = [(selectedCircuitPoints[pos - 2][0], selectedCircuitPoints[pos - 2][1]),
                (selectedCircuitPoints[pos - 1][0], selectedCircuitPoints[pos - 1][1]),
                (selectedCircuitPoints[0][0], selectedCircuitPoints[0][1]),
                (selectedCircuitPoints[1][0], selectedCircuitPoints[1][1])]
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

    # ahora recuperamos el borde externo y el borde interno
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
    for i in range (len (external)-1):
        polys.append(map_widget.set_path ([external[i], external[i+1]], color ='red',width=3))
    polys.append(map_widget.set_path([external[-1], external[0]], color='red', width = 3))

    for i in range(len(internal) - 1):
        polys.append(map_widget.set_path([internal[i], internal[i + 1]], color='blue', width=3))
    polys.append(map_widget.set_path([internal[-1], internal[0]], color='blue', width=3))

    # ahora preparamos el escenario que habrá que enviar a los drones
    # el esceario es el mismo para todos. Tiene un geofence de inclusión (el borde externo)
    # y uno de exclusión (el borde interno)

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


def sendCircuit ():
    # enviamos el esenario a todos los drones
    global swarm
    global connected, dron, dronIcons
    global altitudes, scenario

    for i in range (0,len(swarm)):
        swarm[i].setScenario(scenario)

    sendBtn['bg'] = 'green'

def connect ():
    global swarm
    global connected, dron, dronIcons
    global altitudes, modos, colors
    global telemetriaFrame, controlesFrame

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
        modos = []

        dronIcons = [None, None, None, None]

        textColor = 'white'

        for i in range(0, numPlayers):
            # identificamos el dron
            dron = swarm[i]
            dron.changeNavSpeed(1) # que vuele a 1 m/s
            # nos conectamos
            print ('voy a onectar ', i, connectionStrings[i], baud)
            dron.connect(connectionStrings[i], baud)
            print ('conectado')
            if i == 3:
                textColor = 'black'
            # colocamos los botones para aterrizar y cambiar de modo, cada uno con el color que toca
            tk.Button(controlesFrame, bg=colors[i], fg=textColor, text='Aterrizar',
                      command=lambda d=swarm[i]: d.Land(blocking=False)) \
                .grid(row=0, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            tk.Button(controlesFrame, bg=colors[i], fg=textColor, text='Modo guided',
                      command=lambda d=swarm[i]: d.setFlightMode('GUIDED')) \
                .grid(row=1, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            tk.Button(controlesFrame, bg=colors[i], fg=textColor, text='Modo brake',
                      command=lambda d=swarm[i]: d.setFlightMode('BRAKE')) \
                .grid(row=2, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            # colocamos las labels para mostrar las alturas de los drones
            altitudes.append(tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid"))
            altitudes[-1].grid(row=0, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            modos.append(tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid"))
            modos[-1].grid(row=1, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            # solicitamos datos de telemetria del dron
            dron.send_telemetry_info(processTelemetryInfo)

        connected = True
        connectBtn['bg'] = 'green'




################### Funciones para supervisar la carrera #########################

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

def start ():
    # esto hará que empiezen a colorearse las zonas en las que estan los drones y a comparar las posiciones
    # para ver si alguno a pillado a otro
    global running
    running = True



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
    global red, blue, green, yellow, black, dronPictures, dronPictures_lines
    global connectOption
    global numPlayers, playersCount
    global myZone, myZoneWidget
    global client
    global running
    global controlesFrame, telemetriaFrame

    running = False

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
    createFrame.columnconfigure(2, weight=1)
    createFrame.columnconfigure(2, weight=1)

    tk.Label (createFrame, text='Escribe el nombre aquí')\
        .grid(row=0, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # el nombre se usará para poner nombre al fichero con la imagen y al fichero json con el circuito
    name = tk.StringVar()
    tk.Entry(createFrame, textvariable=name)\
        .grid(row=1, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    startDesignBtn = tk.Button(createFrame, text="Inicia \nel diseño", bg="dark orange",
                                      command= startDesign)
    startDesignBtn.grid(row=2, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    cleanDesignBtn = tk.Button(createFrame, text="Borra \ndiseño", bg="dark orange",
                                      command= cleanDesign)
    cleanDesignBtn.grid(row=2, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    deleteLastBtn = tk.Button(createFrame, text="Borra \núltimo punto", bg="dark orange",
                               command=deleteLast)
    deleteLastBtn.grid(row=2, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    fixErrorBtn = tk.Button(createFrame, text="Corregir \nerror", bg="dark orange",
                               command=fixError)
    fixErrorBtn.grid(row=2, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    registerCircuitBtn = tk.Button(createFrame, text="Guardar circuito", bg="dark orange", command = registerCircuit)
    registerCircuitBtn.grid(row=3, column=0, columnspan = 4, padx=5, pady=5, sticky=tk.N +tk.E + tk.W)


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

    controlesFrame = tk.LabelFrame(superviseFrame, text='Controles')
    controlesFrame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # en este frame colocaremos los botones para aterrizar y cambiar modos de cada dron
    controlesFrame.rowconfigure(0, weight=1)
    controlesFrame.rowconfigure(1, weight=1)
    controlesFrame.rowconfigure(2, weight=1)
    controlesFrame.columnconfigure(0, weight=1)
    controlesFrame.columnconfigure(1, weight=1)
    controlesFrame.columnconfigure(2, weight=1)
    controlesFrame.columnconfigure(3, weight=1)


    telemetriaFrame = tk.LabelFrame(superviseFrame, text='Telemetría (altitud y modo de vuelo')
    telemetriaFrame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # en este frame colocaremos la altitud y el modo de vuelo de cada dron
    telemetriaFrame.rowconfigure(0, weight=1)
    telemetriaFrame.rowconfigure(1, weight=1)
    telemetriaFrame.columnconfigure(0, weight=1)
    telemetriaFrame.columnconfigure(1, weight=1)
    telemetriaFrame.columnconfigure(2, weight=1)
    telemetriaFrame.columnconfigure(3, weight=1)

    showQRBtn = tk.Button(superviseFrame, text="Mostrar código QR de mobile web APP", bg="dark orange", command=showQR)
    showQRBtn.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    startBtn = tk.Button(superviseFrame, text="Empezar la carrera", bg="dark orange", command=start)
    startBtn.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)



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

    # icono para representar los drones en el mapa
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

    # iconos para representar a los drones que han aterrizado porque los han pillado

    im = Image.open("images/red_line.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    red_line = ImageTk.PhotoImage(im_resized)
    im = Image.open("images/blue_line.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    blue_line = ImageTk.PhotoImage(im_resized)
    im = Image.open("images/green_line.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    green_line = ImageTk.PhotoImage(im_resized)

    im = Image.open("images/yellow_line.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    yellow_line = ImageTk.PhotoImage(im_resized)

    dronPictures_lines = [red_line, blue_line, green_line, yellow_line]



    return ventana


if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.mainloop()
