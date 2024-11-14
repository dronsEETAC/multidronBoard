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
import random
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from datetime import datetime
from ParameterManager import ParameterManager
from AutopilotControllerClass import AutopilotController
'''
Ejemplo de estructura de datos que representa un escenario para carreras de tipo check.
Los escenarios base son: 1, 2H, 2V, 3H, 3V, 4H, 4V, 4M
Hay tantas zonas como número de jugadores y cada zona es un rectangulo
Los datos son (en los casos 2H, 2V, 3H, 3V, 4H, 4V), la orientación de las zonas y la distancia entre ellas
En el caso 1 no hay datos
En el caso 4M tenemos orientación y distancia tanto en horizontal como en vertical
Los obstáculos hacen referencia a la primera zona. Pueden ser poligonos o círculos,
en cuyo caso tenemos el centro y el radio,

{
  "numPlayers": 4,
  "base": "4V",
  "zones": [
    [
      [
        41.276451327606054,
        1.9883679228705375
      ],
      [
        41.276256805364255,
        1.9884322955769536
      ],
      [
        41.276287041461444,
        1.9885838400063216
      ],
      [
        41.27648156370221,
        1.9885194677498126
      ]
    ],
    [
      [
        41.276287041461444,
        1.9885838400063216
      ],
      [
        41.27648156370221,
        1.9885194677498126
      ],
      [
        41.27651179959873,
        1.9886710127689562
      ],
      [
        41.27631727735899,
        1.9887353845755484
      ]
    ],
    [
      [
        41.27651179959873,
        1.9886710127689562
      ],
      [
        41.27631727735899,
        1.9887353845755484
      ],
      [
        41.276347513056905,
        1.9888869292846427
      ],
      [
        41.276542035295606,
        1.9888225579279724
      ]
    ],
    [
      [
        41.276347513056905,
        1.9888869292846427
      ],
      [
        41.276542035295606,
        1.9888225579279724
      ],
      [
        41.27657227398454,
        1.9889741021079033
      ],
      [
        41.27637775178283,
        1.9890384751242607
      ]
    ]
  ],
  "data": [
    75.18581618130582,
    13.133379771916
  ],
  "obstacles": [
    [
      [
        41.27637674389427,
        1.9884457069319694
      ],
      [
        41.27642109097641,
        1.988453753559014
      ],
      [
        41.2763837991139,
        1.9884993511122673
      ]
    ],
    [
      [
        41.276356586119704,
        1.988675575463077
      ],
      9.440723493220057
    ]
  ]
}
'''


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

# procesado de los datos de telemetría
def processTelemetryInfo (id, telemetry_info):
    global dronIcons, colors, traces, lock
    global positions

    # recupero la posición en la que está el dron
    lat = telemetry_info['lat']
    lon = telemetry_info['lon']
    alt = telemetry_info['alt']
    modo = telemetry_info['flightMode']
    positions[id] = [lat, lon]

    # si es el primer paquete de este dron entonces ponemos en el mapa el icono de ese dron
    if not dronIcons[id]:
        dronIcons[id] = map_widget.set_marker(lat, lon,
                        icon=dronPictures[id],icon_anchor="center")
    # si no es el primer paquete entonces muevo el icono a la nueva posición
    else:
        dronIcons[id].set_position(lat,lon)
    # actualizo la altitud
    altitudes[id]['text'] = str (round(alt,2))
    # actualizo modo de vuelo
    modos[id]['text'] = modo


########## Funciones para la creación del escenario  #################################
def selectLimits ():
    global state, limitPoints, limits, graphics
    state = 'definingLimits'
    limitPoints = 0
    limits = []
    graphics = []
    # informo del tema de los botones del mouse para que el usuario no se despiste
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo del ratón señala 3 puntos que definen el paralelogramo")

def generarZonas(caso):
    '''A partir de los límites y el tipo de escenario base calculamos los límites de las zonas
    Retornamos una lista de zonas y datos sobre orientación y distancia entre zonas'''

    global distanciaHorizontal, distanciaVertical, orientacionHorizontal, orientacionVertical
    global casoEscena, limits

    casoEscena = caso

    # ordeno los puntos porque me vienen asi: NW, NE, SE y SW
    # y los necesito asi; NW, NE, SW, SE
    tmp = limits[2]
    limits[2] = limits[3]
    limits[3] = tmp
    geod = Geodesic.WGS84
    # calculamos ancho (distancia entre NW y NE y orientación horizontal
    g = geod.Inverse(
        limits[0][0],
        limits[0][1],
        limits[1][0],
        limits[1][1])

    anchura = float(g["s12"])
    orientacionHorizontal = float(g["azi2"])

    # calculamos largo (distancia entre NW y SW) y orientación vertical
    g = geod.Inverse(
        limits[0][0],
        limits[0][1],
        limits[2][0],
        limits[2][1])

    largo = float(g["s12"])
    orientacionVertical = float(g["azi2"])

    # calculamos las coordenadas SE
    g = geod.Direct(
        limits[2][0],
        limits[2][1],
        orientacionHorizontal,
        anchura
    )
    lat = float(g["lat2"])
    lon = float(g["lon2"])
    limits.append([lat, lon])
    print('limites: ', limits)
    if caso == '1':
        # solo retorno límites. No necesito distancia ni orientación
        return [[limits[0], limits[1], limits[3], limits[2]]], None
    elif caso == '2V':
        # caso 2 zonas verticales
        distanciaHorizontal = anchura / 2
        distanciaVertical = largo
        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[2][0],
            limits[2][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto3 = [float(g["lat2"]), float(g["lon2"])]
        # retorno la lista con las dos areas, y la orientación y distancia
        return [[limits[0], limits[2], punto3, punto4],
                [punto3, punto4, limits[1], limits[3]]], \
                [orientacionHorizontal, distanciaHorizontal]
    elif caso == '2H':
        # caso 2 zonas horizontales
        distanciaVertical = largo / 2
        distanciaHorizontal = anchura

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionVertical,
            distanciaVertical)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[1][0],
            limits[1][1],
            orientacionVertical,
            distanciaVertical)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        return [[limits[0], limits[1], punto3, punto4],
                [punto3, punto4, limits[2], limits[3]]],\
                [orientacionVertical, distanciaVertical]

    elif caso == '3V':
        # caso 3 zonas verticales
        distanciaHorizontal = anchura / 3
        distanciaVertical = largo
        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionHorizontal,
            distanciaHorizontal * 2)
        punto5 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[2][0],
            limits[2][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[2][0],
            limits[2][1],
            orientacionHorizontal,
            distanciaHorizontal * 2)
        punto6 = [float(g["lat2"]), float(g["lon2"])]

        return [[limits[0], limits[2], punto3, punto4],
                [punto3, punto4, punto5, punto6],
                [punto5, punto6, limits[3], limits[1]]],\
                [orientacionHorizontal, distanciaHorizontal]

    elif caso == '3H':
        # caso 3 zonas horizontales
        distanciaVertical = largo / 3
        distanciaHorizontal = anchura
        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionVertical,
            distanciaVertical)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionVertical,
            distanciaVertical * 2)
        punto5 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[1][0],
            limits[1][1],
            orientacionVertical,
            distanciaVertical)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[1][0],
            limits[1][1],
            orientacionVertical,
            distanciaVertical * 2)
        punto6 = [float(g["lat2"]), float(g["lon2"])]

        return [[limits[0], limits[1], punto3, punto4],
                [punto3, punto4, punto5, punto6],
                [punto5, punto6, limits[3], limits[2]]],\
                [orientacionVertical, distanciaVertical]


    elif caso == '4V':
        # caso 4 zonas verticales
        distanciaHorizontal = anchura / 4
        distanciaVertical = largo
        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionHorizontal,
            distanciaHorizontal * 2)
        punto5 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionHorizontal,
            distanciaHorizontal * 3)
        punto8 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[2][0],
            limits[2][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[2][0],
            limits[2][1],
            orientacionHorizontal,
            distanciaHorizontal * 2)
        punto6 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[2][0],
            limits[2][1],
            orientacionHorizontal,
            distanciaHorizontal * 3)
        punto7 = [float(g["lat2"]), float(g["lon2"])]

        return [[limits[0], limits[2], punto3, punto4],
                [punto3, punto4, punto5, punto6],
                [punto5, punto6, punto7, punto8],
                [punto7, punto8, limits[1], limits[3]]],\
                [orientacionHorizontal, distanciaHorizontal]

    elif caso == '4H':
        # caso 3 zonas horizontales
        distanciaVertical = largo / 4
        distanciaHorizontal = anchura

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionVertical,
            distanciaVertical)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionVertical,
            distanciaVertical * 2)
        punto5 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionVertical,
            distanciaVertical * 3)
        punto8 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[1][0],
            limits[1][1],
            orientacionVertical,
            distanciaVertical)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[1][0],
            limits[1][1],
            orientacionVertical,
            distanciaVertical * 2)
        punto6 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[1][0],
            limits[1][1],
            orientacionVertical,
            distanciaVertical * 3)
        punto7 = [float(g["lat2"]), float(g["lon2"])]

        return [[limits[0], limits[1], punto3, punto4],
                [punto3, punto4, punto5, punto6],
                [punto5, punto6, punto7, punto8],
                [punto7, punto8, limits[2], limits[3]]],\
                [orientacionVertical, distanciaVertical]


    elif caso == '4M':
        # caso 4 zonas en malla
        distanciaVertical = largo / 2
        distanciaHorizontal = anchura /2

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionVertical,
            distanciaVertical)
        punto6 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[0][0],
            limits[0][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[1][0],
            limits[1][1],
            orientacionVertical,
            distanciaVertical)
        punto7= [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limits[2][0],
            limits[2][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto5 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            punto6[0],
            punto6[1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto8 = [float(g["lat2"]), float(g["lon2"])]
        # en este caso se retorna la lista con las 4 zonas y también las dos orientaciones y las dos distancias
        return [[limits[0], punto4, punto8, punto6],
                [punto8, punto4, limits[1], punto7],
                [limits[2], punto6, punto8, punto5],
                [punto7, punto8, punto5, limits[3]]],\
                [orientacionHorizontal, distanciaHorizontal, orientacionVertical, distanciaVertical]


def getFenceWaypoint (coords):
    global centerFixed, state, scenario, limitPoints, obstaclePoints
    global limits, casoEscena, obstacles, graphics, graphicsObstacles, selectLimitsBtn
    geod = Geodesic.WGS84

    # acabo de clicar con el botón izquierdo
    if state == "definingLimits":
        # estoy definiendo el espacio de vuelo
        limitPoints = limitPoints+1
        graphics.append(map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center"))
        if limitPoints == 1:
            limits.append(coords)
        elif limitPoints == 2:
            graphics.append(map_widget.set_path([limits[0], coords], color='gray', width=3))
            limits.append(coords)
        elif limitPoints == 3:
            graphics.append(map_widget.set_path([limits[1], coords], color='gray', width=3))
            limits.append(coords)
            # voy a clacular el cuarto punto que cierra el paralelogramo
            g = geod.Inverse(
                limits[1][0],
                limits[1][1],
                limits[2][0],
                limits[2][1])

            distancia = float(g["s12"])
            orientacion = float(g["azi2"])

            g = geod.Direct (
                limits[0][0],
                limits[0][1],
                orientacion,
                distancia
            )
            limits.append( [float(g["lat2"]), float(g["lon2"])])

            for element in graphics:
                element.delete()
            graphics = []
            graphics.append(map_widget.set_polygon(limits,
                                                outline_color='black',
                                                fill_color='black',
                                                border_width=3))
            # quedo a la espera de definir obstáculos
            graphicsObstacles = []
            selectLimitsBtn['text'] = "Listo"
            state = 'waitingObstacle'
    elif state == "waitingObstacle":
        # antes de clicar debería haber elegido el tipo de obstaculo
        messagebox.showinfo("showinfo",
                        "Selecciona primero si quieres un obstaculo tipo poligono o tipo círculo")


    elif state == "definingObstaclePoly":
        # estoy recogiendo los puntos que delimitan el obstáculo poligonal
        # dependiendo del tipo de escenario tengo que replicar el punto en cada una de las zonas
        obstaclePoints = obstaclePoints + 1
        graphicsObstacles.append(map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center"))
        if casoEscena == '1':
            obstacles[0].append(coords)
        elif casoEscena == '2V':
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionHorizontal,
                distanciaHorizontal)
            punto = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
            obstacles[0].append(coords)
            obstacles[1].append(punto)
        elif casoEscena == '2H':
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionVertical,
                distanciaVertical)
            punto = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
            obstacles[0].append(coords)
            obstacles[1].append(punto)
        elif casoEscena == '3V':
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionHorizontal,
                distanciaHorizontal)
            punto = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionHorizontal,
                distanciaHorizontal*2)
            punto2 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
            obstacles[0].append(coords)
            obstacles[1].append(punto)
            obstacles[2].append(punto2)
        elif casoEscena == '3H':
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionVertical,
                distanciaVertical)
            punto = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionVertical,
                distanciaVertical*2)
            punto2 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
            obstacles[0].append(coords)
            obstacles[1].append(punto)
            obstacles[2].append(punto2)
        elif casoEscena == '4V':
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionHorizontal,
                distanciaHorizontal)
            punto = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionHorizontal,
                distanciaHorizontal * 2)
            punto2 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionHorizontal,
                distanciaHorizontal * 3)
            punto3 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto3[0], punto3[1], icon=black, icon_anchor="center"))
            obstacles[0].append(coords)
            obstacles[1].append(punto)
            obstacles[2].append(punto2)
            obstacles[3].append(punto3)
        elif casoEscena == '4H':
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionVertical,
                distanciaVertical)
            punto = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionVertical,
                distanciaVertical * 2)
            punto2 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionVertical,
                distanciaVertical * 3)
            punto3 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto3[0], punto3[1], icon=black, icon_anchor="center"))
            obstacles[0].append(coords)
            obstacles[1].append(punto)
            obstacles[2].append(punto2)
            obstacles[3].append(punto3)
        elif casoEscena == '4M':
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionVertical,
                distanciaVertical)
            punto = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                coords[0],
                coords[1],
                orientacionHorizontal,
                distanciaHorizontal)
            punto2 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
            g = geod.Direct(
                punto2[0],
                punto2[1],
                orientacionVertical,
                distanciaVertical)
            punto3 = [float(g["lat2"]), float(g["lon2"])]
            graphicsObstacles.append(map_widget.set_marker(punto3[0], punto3[1], icon=black, icon_anchor="center"))
            obstacles[0].append(coords)
            obstacles[1].append(punto)
            obstacles[2].append(punto2)
            obstacles[3].append(punto3)

        if obstaclePoints > 1:
            graphicsObstacles.append(map_widget.set_path([obstacles[0][-1], coords], color='black', width=3))


    elif state == "definingObstacleCircle":
        # estoy definiendo un obstáculo circular

        if centerFixed:
            # ya he marcado el centro del círculo. Tendría que haber pulsado el boton derecho del mouse para cerrar el circulo
            messagebox.showinfo("Error",
                                "Marca el límite con el botón derecho del mouse")
        else:
            # acabo de señalar el centro del circulo
            # dependiendo del escenario base tengo que replicar el círculo en todas las zonas
            obstacles[0].append(coords)
            centerFixed = True
            graphicsObstacles.append(map_widget.set_marker(coords[0], coords[1], icon=black, icon_anchor="center"))
            if casoEscena == '2V':
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionHorizontal,
                    distanciaHorizontal)
                punto = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
                obstacles[1].append(punto)
            elif casoEscena == '2H':
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionVertical,
                    distanciaVertical)
                punto = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
                obstacles[1].append(punto)
            elif casoEscena == '3V':
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionHorizontal,
                    distanciaHorizontal)
                punto = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionHorizontal,
                    distanciaHorizontal * 2)
                punto2 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
                obstacles[1].append(punto)
                obstacles[2].append(punto2)
            elif casoEscena == '3H':
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionVertical,
                    distanciaVertical)
                punto = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionVertical,
                    distanciaVertical * 2)
                punto2 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
                obstacles[1].append(punto)
                obstacles[2].append(punto2)
            elif casoEscena == '4V':
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionHorizontal,
                    distanciaHorizontal)
                punto = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionHorizontal,
                    distanciaHorizontal * 2)
                punto2 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionHorizontal,
                    distanciaHorizontal * 3)
                punto3 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto3[0], punto3[1], icon=black, icon_anchor="center"))
                obstacles[1].append(punto)
                obstacles[2].append(punto2)
                obstacles[3].append(punto3)
            elif casoEscena == '4H':
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionVertical,
                    distanciaVertical)
                punto = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionVertical,
                    distanciaVertical * 2)
                punto2 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionVertical,
                    distanciaVertical * 3)
                punto3 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto3[0], punto3[1], icon=black, icon_anchor="center"))
                obstacles[1].append(punto)
                obstacles[2].append(punto2)
                obstacles[3].append(punto3)
            elif casoEscena == '4M':
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionVertical,
                    distanciaVertical)
                punto = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto[0], punto[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    coords[0],
                    coords[1],
                    orientacionHorizontal,
                    distanciaHorizontal)
                punto2 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto2[0], punto2[1], icon=black, icon_anchor="center"))
                g = geod.Direct(
                    punto2[0],
                    punto2[1],
                    orientacionVertical,
                    distanciaVertical)
                punto3 = [float(g["lat2"]), float(g["lon2"])]
                graphicsObstacles.append(map_widget.set_marker(punto3[0], punto3[1], icon=black, icon_anchor="center"))
                obstacles[1].append(punto)
                obstacles[2].append(punto2)
                obstacles[3].append(punto3)


def closeObstacle(coords):
    # he pulsado el botón derecho del mouse para cerrar el obstáculo
    global scenario, limits, state
    global  obstacles
    global graphicsObstacles

    geod = Geodesic.WGS84
    # estamos creando un area y acabamos de darle al boton derecho del mouse para cerrar


    if state == "definingObstaclePoly":
        # acabamos de cerrar un obstaculo poligonal

        for element in graphicsObstacles:
            element.delete()
        graphicsObstacles = []
        # dibujamos el obstáculo en cada una de las zonas
        for obstacle in obstacles:
            graphics.append(map_widget.set_polygon(obstacle,
                                                outline_color='black',
                                                fill_color='black',
                                                border_width=3))
        # añadimos al escenario las coordenadas del obstaculo de la zona 0 (con eso es suficiente)
        scenario['obstacles'].append( obstacles[0])
        state = 'waitingObstacle'
        print (state)

    elif state == "definingObstacleCircle":
        # acabamos de cerrar un obstaculo circular
        print (obstacles[0])
        center = (obstacles[0][0][0], obstacles[0][0][1])
        limit = (coords[0], coords[1])
        radius = geopy.distance.geodesic(center, limit).m
        # el radio del círculo es la distancia entre el centro y el punto clicado
        obstacles[0].append (radius)
        # ya tengo completa la definición del fence

        # como no se puede dibujar un circulo con la librería tkintermapview, creo un poligono que aproxime al círculo
        points = getCircle(obstacles[0][0][0], obstacles[0][0][1], radius)
        graphics.append(map_widget.set_polygon(points,
                                            fill_color='black',
                                            outline_color="black",
                                            border_width=3))
        # para cada uno de los casos calculo dónde debo dibujar el circulo de cada una de las zonas
        if casoEscena == '2V':
            g = geod.Direct(
                center[0],
                center[1],
                orientacionHorizontal,
                distanciaHorizontal)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))

        elif casoEscena == '2H':
            g = geod.Direct(
                center[0],
                center[1],
                orientacionVertical,
                distanciaVertical)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
        elif casoEscena == '3V':
            g = geod.Direct(
                center[0],
                center[1],
                orientacionHorizontal,
                distanciaHorizontal)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                center[0],
                center[1],
                orientacionHorizontal,
                distanciaHorizontal * 2)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
        elif casoEscena == '3H':
            g = geod.Direct(
                center[0],
                center[1],
                orientacionVertical,
                distanciaVertical)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                center[0],
                center[1],
                orientacionVertical,
                distanciaVertical * 2)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
        elif casoEscena == '4V':
            g = geod.Direct(
                center[0],
                center[1],
                orientacionHorizontal,
                distanciaHorizontal)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                center[0],
                center[1],
                orientacionHorizontal,
                distanciaHorizontal * 2)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                center[0],
                center[1],
                orientacionHorizontal,
                distanciaHorizontal * 3)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
        elif casoEscena == '4H':
            g = geod.Direct(
                center[0],
                center[1],
                orientacionVertical,
                distanciaVertical)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                center[0],
                center[1],
                orientacionVertical,
                distanciaVertical * 2)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                center[0],
                center[1],
                orientacionVertical,
                distanciaVertical * 3)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
        elif casoEscena == '4M':
            g = geod.Direct(
                center[0],
                center[1],
                orientacionVertical,
                distanciaVertical)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                center[0],
                center[1],
                orientacionHorizontal,
                distanciaHorizontal)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))
            g = geod.Direct(
                point[0],
                point[1],
                orientacionVertical,
                distanciaVertical)
            point = [float(g["lat2"]), float(g["lon2"])]
            points = getCircle(point[0], point[1], radius)
            graphics.append(map_widget.set_polygon(points,
                                                   fill_color='black',
                                                   outline_color="black",
                                                   border_width=3))

        for element in graphicsObstacles:
            element.delete()
        graphicsObstacles = []
        scenario['obstacles'].append(obstacles[0])
        state = 'waitingObstacle'


def selectBase (case):
    global scenario, graphics, obstacles, numPlayers
    if state == 'waitingLimits':
        messagebox.showinfo("showinfo",
                            "Primero selecciona los límites del área de vuelo")

    else:
        # calculo las zonas
        zonas, datos = generarZonas(case)
        numPlayers = len (zonas)

        # preparo la estructura de datos que representa el escenario
        scenario = {
            'numPlayers': numPlayers,
            'base': case,
            'zones': zonas,
            'data': datos,
            'obstacles': []
        }
        colors = ['red', 'blue', 'green', 'yellow']
        # pinto las zonas
        for i in range (len(zonas)):
            graphics.append(map_widget.set_polygon(zonas[i],
                                                outline_color=colors[i],
                                                fill_color=colors[i],
                                                border_width=3))


def definePoly():
    # van a definir un obstáculo de tipo polígono
    global  state, obstaclePoints, limits, obstacles, casoEscena
    if casoEscena == '1':
        obstacles = [[]]
    elif casoEscena == '2V' or casoEscena == '2H':
        obstacles = [[], []]
    elif casoEscena == '3V' or casoEscena == '3H':
        obstacles = [[], [], []]
    else:
        obstacles = [[], [], [], []]

    state = 'definingObstaclePoly'
    obstaclePoints = 0

    # informo del tema de los botones del mouse para que el usuario no se despiste
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo del ratón señala los waypoints\nCon el boton derecho cierra el polígono")



def defineCircle():
    # van a definir un obstáculo de tipo círculo

    global centerFixed, state, casoEscena, obstacles
    if casoEscena == '1':
        obstacles = [[]]
    elif casoEscena == '2V' or casoEscena == '2H':
        obstacles = [[], []]
    elif casoEscena == '3V' or casoEscena == '3H':
        obstacles = [[], [], []]
    else:
        obstacles = [[], [], [], []]

    centerFixed = False
    state = 'definingObstacleCircle'
    # informo del tema de los botones del mouse para que el usuario no se despiste
    messagebox.showinfo("showinfo",
                        "Con el boton izquierdo señala el centro\nCon el boton derecho marca el límite del círculo")



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
    global scenario

    # voy a guardar el multi escenario en el fichero con el nombre indicado en el momento de la creación
    jsonFilename = 'escenariosCheck/' + name.get() + "_"+str(numPlayers)+".json"

    with open(jsonFilename, 'w') as f:
        json.dump(scenario, f)
    # aqui capturo el contenido de la ventana que muestra el Camp Nou (zona del cesped, que es dónde está el escenario)
    im = screenshot('Gestión de escenarios')
    imageFilename = 'escenariosCheck/'+name.get()+ "_"+str(numPlayers)+".png"
    im.save(imageFilename)
    scenario = []
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



############################ Funciones para seleccionar multi escenario ##########################################
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

# una vez elegido el numero de jugadores mostramos los multi escenarios que hay para ese número de jugadores
def selectScenarios (num):
    global scenarios, current, polys
    global numPlayers
    global client, swarm
    numPlayers = num
    # cargamos en una lista las imágenes de todos los multi escenarios disponibles
    # para el número de jugadores indicado
    scenarios = []
    for file in glob.glob("escenariosCheck/*_"+str(num)+".png"):
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


    additionalEvents = [
        {'event': 'drop', 'method':check_drop},
    ]
    autopilotService = AutopilotController (numPlayers, numPlayers, additionalEvents)
    client, swarm = autopilotService.start()

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
def clear ():
    global graphics, graphicsObstacles, state
    state = 'waitingLimits'

    for element in graphics:
        element.delete()
    for element in graphicsObstacles:
        element.delete()



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
    global graphics, obstacles
    geod = Geodesic.WGS84
    graphics = []
    colors = ['red', 'blue', 'green', 'yellow']
    for i in range (len(scenario ['zones'])):
        graphics.append(map_widget.set_polygon(scenario ['zones'][i],
                                               outline_color=colors[i],
                                               fill_color=colors[i],
                                               border_width=3))
    obstacles = [[],[],[],[]]
    casoEscena = scenario ['base']
    for obstacle in scenario['obstacles']:
        obstacles [0].append (obstacle)
        if len (obstacle) > 2:
            # es un polígono
            graphics.append(map_widget.set_polygon(obstacle,
                                                   outline_color='black',
                                                   fill_color='black',
                                                   border_width=3))
            if casoEscena == '2V' or casoEscena == '2H':
                obstacle2 = []
                for point in obstacle:
                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][0],
                        scenario['data'][1])
                    obstacle2.append([float(g["lat2"]), float(g["lon2"])])
                obstacles[1].append(obstacle2)
                graphics.append(map_widget.set_polygon(obstacle2,
                                                       outline_color='black',
                                                       fill_color='black',
                                                       border_width=3))
            if casoEscena == '3V' or casoEscena == '3H':
                obstacle2 = []
                obstacle3 = []
                for point in obstacle:
                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][0],
                        scenario['data'][1])
                    obstacle2.append([float(g["lat2"]), float(g["lon2"])])

                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][0],
                        scenario['data'][1]*2)
                    obstacle3.append([float(g["lat2"]), float(g["lon2"])])


                obstacles[1].append(obstacle2)
                graphics.append(map_widget.set_polygon(obstacle2,
                                                       outline_color='black',
                                                       fill_color='black',
                                                       border_width=3))
                obstacles[2].append(obstacle2)
                graphics.append(map_widget.set_polygon(obstacle3,
                                                       outline_color='black',
                                                       fill_color='black',
                                                       border_width=3))
            if casoEscena == '4V' or casoEscena == '4H':
                obstacle2 = []
                obstacle3 = []
                obstacle4 = []
                for point in obstacle:
                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][0],
                        scenario['data'][1])
                    obstacle2.append([float(g["lat2"]), float(g["lon2"])])

                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][0],
                        scenario['data'][1]*2)
                    obstacle3.append([float(g["lat2"]), float(g["lon2"])])

                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][0],
                        scenario['data'][1] * 3)
                    obstacle4.append([float(g["lat2"]), float(g["lon2"])])


                obstacles[1].append(obstacle2)
                graphics.append(map_widget.set_polygon(obstacle2,
                                                       outline_color='black',
                                                       fill_color='black',
                                                       border_width=3))
                obstacles[2].append(obstacle3)
                graphics.append(map_widget.set_polygon(obstacle3,
                                                       outline_color='black',
                                                       fill_color='black',
                                                       border_width=3))
                obstacles[3].append(obstacle4)
                graphics.append(map_widget.set_polygon(obstacle4,
                                                       outline_color='black',
                                                       fill_color='black',
                                                       border_width=3))
            if casoEscena == '4M':
                obstacle2 = []
                obstacle3 = []
                obstacle4 = []
                for point in obstacle:
                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][0],
                        scenario['data'][1])
                    obstacle2.append([float(g["lat2"]), float(g["lon2"])])

                    g = geod.Direct(
                        point[0],
                        point[1],
                        scenario['data'][2],
                        scenario['data'][3])
                    obstacle3.append([float(g["lat2"]), float(g["lon2"])])

                    g = geod.Direct(
                        obstacle2[-1][0],
                        obstacle2[-1][1],
                        scenario['data'][2],
                        scenario['data'][3])
                    obstacle4.append([float(g["lat2"]), float(g["lon2"])])

                obstacles[1].append(obstacle2)
                graphics.append(map_widget.set_polygon(obstacle2,
                                                        outline_color='black',
                                                        fill_color='black',
                                                        border_width=3))
                obstacles[2].append(obstacle3)
                graphics.append(map_widget.set_polygon(obstacle3,
                                                        outline_color='black',
                                                        fill_color='black',
                                                        border_width=3))
                obstacles[3].append(obstacle4)
                graphics.append(map_widget.set_polygon(obstacle4,
                                                           outline_color='black',
                                                           fill_color='black',
                                                           border_width=3))

        else:
            # es un círculo
            points = getCircle(obstacle[0][0], obstacle[0][1], obstacle[1])
            graphics.append(map_widget.set_polygon(points,
                                                   outline_color='black',
                                                   fill_color='black',
                                                   border_width=3))

            if casoEscena == '2V' or casoEscena == '2H':
                g = geod.Direct(
                    obstacle[0][0],
                    obstacle[0][1],
                    scenario['data'][0],
                    scenario['data'][1])
                point = [float(g["lat2"]), float(g["lon2"])]
                points = getCircle(point[0], point[1], obstacle[1])
                graphics.append(map_widget.set_polygon(points,
                                                       fill_color='black',
                                                       outline_color="black",
                                                       border_width=3))
                obstacles[1].append( [point,obstacle[1]])

            if casoEscena == '3V' or casoEscena == '3H':
                    g = geod.Direct(
                        obstacle[0][0],
                        obstacle[0][1],
                        scenario['data'][0],
                        scenario['data'][1])
                    point = [float(g["lat2"]), float(g["lon2"])]
                    points = getCircle(point[0], point[1], obstacle[1])
                    graphics.append(map_widget.set_polygon(points,
                                                           fill_color='black',
                                                           outline_color="black",
                                                           border_width=3))
                    obstacles[1].append( [point,obstacle[1]])

                    g = geod.Direct(
                        obstacle[0][0],
                        obstacle[0][1],
                        scenario['data'][0],
                        scenario['data'][1]*2)
                    point = [float(g["lat2"]), float(g["lon2"])]
                    points = getCircle(point[0], point[1], obstacle[1])
                    graphics.append(map_widget.set_polygon(points,
                                                           fill_color='black',
                                                           outline_color="black",
                                                           border_width=3))
                    obstacles[2].append([point, obstacle[1]])

            if casoEscena == '4V' or casoEscena == '4H':
                g = geod.Direct(
                    obstacle[0][0],
                    obstacle[0][1],
                    scenario['data'][0],
                    scenario['data'][1])
                point = [float(g["lat2"]), float(g["lon2"])]
                points = getCircle(point[0], point[1], obstacle[1])
                graphics.append(map_widget.set_polygon(points,
                                                       fill_color='black',
                                                       outline_color="black",
                                                       border_width=3))
                obstacles[1].append([point, obstacle[1]])

                g = geod.Direct(
                    obstacle[0][0],
                    obstacle[0][1],
                    scenario['data'][0],
                    scenario['data'][1] * 2)
                point = [float(g["lat2"]), float(g["lon2"])]
                points = getCircle(point[0], point[1], obstacle[1])
                graphics.append(map_widget.set_polygon(points,
                                                       fill_color='black',
                                                       outline_color="black",
                                                       border_width=3))
                obstacles[2].append([point, obstacle[1]])

                g = geod.Direct(
                    obstacle[0][0],
                    obstacle[0][1],
                    scenario['data'][0],
                    scenario['data'][1] * 3)
                point = [float(g["lat2"]), float(g["lon2"])]
                points = getCircle(point[0], point[1], obstacle[1])
                graphics.append(map_widget.set_polygon(points,
                                                       fill_color='black',
                                                       outline_color="black",
                                                       border_width=3))
                obstacles[3].append([point, obstacle[1]])


            if casoEscena == '4M':
                g = geod.Direct(
                    obstacle[0][0],
                    obstacle[0][1],
                    scenario['data'][0],
                    scenario['data'][1])
                point = [float(g["lat2"]), float(g["lon2"])]
                points = getCircle(point[0], point[1], obstacle[1])
                graphics.append(map_widget.set_polygon(points,
                                                       fill_color='black',
                                                       outline_color="black",
                                                       border_width=3))
                obstacles[1].append([point, obstacle[1]])

                g = geod.Direct(
                    obstacle[0][0],
                    obstacle[0][1],
                    scenario['data'][2],
                    scenario['data'][3])
                point = [float(g["lat2"]), float(g["lon2"])]
                points = getCircle(point[0], point[1], obstacle[1])
                graphics.append(map_widget.set_polygon(points,
                                                       fill_color='black',
                                                       outline_color="black",
                                                       border_width=3))
                obstacles[2].append([point, obstacle[1]])
                a =   obstacles[2][-1][0][0]
                b =    obstacles[2][-1][0][1]

                g = geod.Direct(
                    obstacles[1][-1][0][0],
                    obstacles[1][-1][0][1],
                    scenario['data'][2],

                    scenario['data'][3])
                point = [float(g["lat2"]), float(g["lon2"])]
                points = getCircle(point[0], point[1], obstacle[1])
                graphics.append(map_widget.set_polygon(points,
                                                       fill_color='black',
                                                       outline_color="black",
                                                       border_width=3))
                obstacles[3].append([point, obstacle[1]])


# seleccionar el multi escenario que está a la vista
def selectScenario():
    global  selectedScenario, numPlayers
    # limpio el mapa
    clear()
    # cargamos el fichero json con el multi escenario seleccionado (el que está en la posición current de la lista9
    f = open(scenarios[current]['name'] +'.json')
    selectedScenario = json.load (f)
    # dibujo el escenario
    drawScenario(selectedScenario)
    # habilito el botón para enviar el escenario al enjambre
    sendBtn['state'] = tk.NORMAL

# envia los datos del multi escenario seleccionado al enjambre
def sendScenario ():
    # enviamos a cada dron el escenario que le toca
    global swarm
    global connected, dron, dronIcons
    global altitudes, modos

    # tengo que prepara el escenario de cada dron en el formato establecido
    for i in range (0,len(swarm)):
        tmp = [] # aqui creo el escenario
        waypoints = [{'lat': wp[0], 'lon':wp[1]} for wp in selectedScenario['zones'][i]]
        # lo primero el fence de inclusión que es la zona correspondente
        tmp.append ({
            'type':'polygon',
            'waypoints': waypoints
        })
        # y ahora cada uno de los obstaculos que tengo en la lista obstacles
        for obstacle in obstacles[i]:
            if len(obstacle) > 2:
                waypoints = [{'lat': wp[0], 'lon': wp[1]} for wp in obstacle]
                tmp.append({
                    'type': 'polygon',
                    'waypoints': waypoints
                })
            else:
                tmp.append({
                    'type': 'circle',
                    'radius': obstacle[1],
                    'lat': obstacle[0][0],
                    'lon': obstacle[0][1]
                })

        swarm[i].setScenario(tmp)

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

#
def defineLimits ():
    global zone, defineLimitsBtn, scenario, state, limitPoints, limits
    if 'Define' in defineLimitsBtn['text']:
        state = 'definingLimits'
        limitPoints = 0
        limits = []
        defineLimitsBtn['text'] = "Clica aquí cuando hayas acabado de definir los límites"
        scenario['limits'] = []
        messagebox.showinfo("showinfo",
                            "Con el boton izquierdo del ratón señala los waypoints\nCon el boton derecho cierra el polígono")

    else:
        print ('Final')

def landAll ():
    for dron in swarm:
        dron.Land(blocking=False)

# me contecto a los drones del enjambre
def connect ():
    global swarm
    global connected, dron, dronIcons
    global altitudes, modos, points

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
        points = []

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
            tk.Button(controlesFrame, bg=colors[i], fg= textColor, text = 'Aterrizar',
                          command=lambda d=swarm[i]: d.Land(blocking=False)) \
                .grid(row=0, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            tk.Button(controlesFrame, bg=colors[i],fg= textColor, text='Modo guiado',
                      command=lambda d=swarm[i]: d.setFlightMode('GUIDED')) \
                .grid(row=1, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            tk.Button(controlesFrame, bg=colors[i],fg= textColor, text='Modo break',
                      command=lambda d=swarm[i]: d.setFlightMode('BRAKE')) \
                .grid(row=2, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            # colocamos las labels para mostrar las alturas de los drones
            altitudes.append(tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid"))
            altitudes[-1].grid(row=0, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)
            modos.append(tk.Label(telemetriaFrame, text='', borderwidth=1, relief="solid"))
            modos[-1].grid(row=1, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

            # preparamos el frame de puntuación
            points.append(tk.Label(pointsFrame, text='0', fg = colors[i],  font=("Arial", 25), borderwidth=1, relief="solid"))
            points[-1].grid(row=0, column=i, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

            # solicitamos datos de telemetria del dron
            dron.send_telemetry_info(processTelemetryInfo)

        # añado el boton para aterrizar todos los drones
        tk.Button(controlesFrame, bg='dark orange', fg='white', text='Aterrizar todos',command=landAll) \
            .grid(row=3, column=0, columnspan=4, padx=2, pady=2, sticky=tk.N + tk.E + tk.W)

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

def genetateTargets ():
    global targets
    geod = Geodesic.WGS84
    targets = [[], [], [], []]

    zone = selectedScenario['zones'][0]
    casoEscena = selectedScenario['base']

    # los puntos que se generen aleatoriamente deben estar dentro
    # de la zona del dron 0

    polygon = Polygon([(zone[0][0], zone[0][1]),
                       (zone[1][0], zone[1][1]),
                       (zone[2][0], zone[2][1]),
                       (zone[3][0], zone[3][1])])

    lats = [zone[0][0], zone[1][0], zone[2][0], zone[3][0]]
    lons = [zone[0][1], zone[1][1], zone[2][1], zone[3][1]]
    # generaremos puntos aleatorios dentro de estos rangos
    minLat = min(lats)
    maxLat = max(lats)
    minLon = min(lons)
    maxLon = max(lons)
    random.seed(datetime.now().timestamp())
    for i in range (10):
        # generamos un punto aleatorio que este dentro de la zona y fuera de los obstaculos
        valid = False
        while not valid:

            targetLat = random.uniform(minLat, maxLat)
            targetLon = random.uniform(minLon, maxLon)
            point = Point(targetLat, targetLon)
            valid = True

            if not polygon.contains(point):
                valid = False
            else:
                j = 0
                while j < len (obstacles[0]) and valid:
                    if len(obstacles[0][j]) > 2:
                        polygon2 = Polygon(obstacles[0][j])
                        if polygon2.contains(point):
                            valid = False
                    else:
                        if haversine(targetLat, targetLon, obstacles[0][j][0][0], obstacles[0][j][0][1]) <= obstacles[0][j][1]:
                            valid = False
                    j = j+1
        print ('ya tengo otro ',targetLat, targetLon )
        targets[0].append((targetLat, targetLon))

        print('ya tengo otro ', targets[0])
        if casoEscena == '2V' or casoEscena == '2H':
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][0],
                selectedScenario['data'][1])
            targets[1].append([float(g["lat2"]), float(g["lon2"])])

        if casoEscena == '3V' or casoEscena == '3H':
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][0],
                selectedScenario['data'][1])
            targets[1].append([float(g["lat2"]), float(g["lon2"])])
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][0],
                selectedScenario['data'][1]*2)
            targets[2].append([float(g["lat2"]), float(g["lon2"])])

        if casoEscena == '4V' or casoEscena == '4H':
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][0],
                selectedScenario['data'][1])
            targets[1].append([float(g["lat2"]), float(g["lon2"])])
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][0],
                selectedScenario['data'][1] * 2)
            targets[2].append([float(g["lat2"]), float(g["lon2"])])
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][0],
                selectedScenario['data'][1] * 3)
            targets[3].append([float(g["lat2"]), float(g["lon2"])])
        if casoEscena == '4M':
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][0],
                selectedScenario['data'][1])
            targets[1].append([float(g["lat2"]), float(g["lon2"])])
            g = geod.Direct(
                targetLat,
                targetLon,
                selectedScenario['data'][2],
                selectedScenario['data'][3])
            targets[2].append([float(g["lat2"]), float(g["lon2"])])
            g = geod.Direct(
                targets[1][-1][0],
                targets[1][-1][1],
                selectedScenario['data'][2],
                selectedScenario['data'][3])
            targets[3].append([float(g["lat2"]), float(g["lon2"])])

def startCompetition ():
    global targets, nextTarget, targetIcon
    genetateTargets ()
    nextTarget = [0,0,0,0]
    targetIcon = [None, None, None, None]
    for i in range (selectedScenario['numPlayers']):
        point = targets[i][0]
        targetIcon[i] = map_widget.set_marker(point[0], point[1], icon=diana, icon_anchor="center")


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


'''def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK Returned code=", rc)
    else:
        print("Bad connection Returned code=", rc)'''

'''def publish_event (id, event):
    # al ser drones idenificados dronLink_old nos pasa siempre en primer lugar el identificador
    # del dron que ha hecho la operación
    # lo necesito para identificar qué jugador debe hacer caso a la respuesta
    global client
    client.publish('multiPlayerDash/mobileApp/'+event+'/'+str(id))'''

def check_drop (id):
    global targetIcon, nextTarget, map_widget, diana, white, black
    global points


    distanceForSuccess = 1
    target = targets[id][nextTarget[id]]
    if haversine(positions[id][0], positions[id][1], target[0], target[1]) < distanceForSuccess:
         targetIcon[id].delete()

         targetIcon[id]=map_widget.set_marker(target[0], target[1], icon=white, icon_anchor="center")
         nextTarget[id] = nextTarget[id] + 1
         target = targets[id][nextTarget[id]]
         targetIcon[id]=map_widget.set_marker(target[0], target[1], icon=diana, icon_anchor="center")
         p = int (points[id]['text'])
         points[id]['text'] = str(p+1)

    else:
         targetIcon[id].delete()
         targetIcon[id] = map_widget.set_marker(target[0], target[1], icon=black, icon_anchor="center")
         nextTarget[id] = nextTarget[id] + 1
         targeta = targets[id][nextTarget[id]]
         targetIcon[id]=map_widget.set_marker(targeta[0], targeta[1], icon=diana, icon_anchor="center")

'''# aqui recibimos las publicaciones que hacen las web apps desde las que están jugando
def on_message(client, userdata, message):
    global targetIcon, nexttarget, map_widget
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
            print ('se ha conectado el ', playersCount)
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

    if command == 'drop':
        id = int(parts[3])
        check_drop(id)


'''
def crear_ventana():

    global map_widget
    global createBtn,selectBtn, superviseBtn, createFrame, name, selectFrame, scene, scenePic,scenarios, current
    global superviseFrame
    global prevBtn, nextBtn, sendBtn, connectBtn
    global scenarioCanvas
    global i_wp, e_wp
    global paths, fence, polys
    global connected
    global selectPlayersFrame
    global red, blue, green, yellow, black, white, dronPictures
    global connectOption
    global playersCount
    global client
    global drawingAction, traces, dronLittlePictures
    global QRimg
    global colors
    global lock
    global graphics, graphicsObstacles, limits
    global state
    global target, positions, diana
    global controlesFrame, telemetriaFrame, pointsFrame
    global selectLimitsBtn

    positions = [None, None, None, None]

    target = None
    state = 'waitingLimits'

    playersCount = 0

    connected = False
    # aqui indicare, para cada dron, si estamos pintando o no
    drawingAction = ['nothing']*4 # nothing, draw o remove
    # y aqui ire guardando los rastros
    traces = [[], [], [], []]

    # para guardar datos y luego poder borrarlos
    graphicsObstacles = []
    graphics = []
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
    selectLimitsBtn = tk.Button(createFrame, text="Selecciona los límites del escenario", bg="dark orange", command= selectLimits)
    selectLimitsBtn.grid(row = 2, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    selectBaseFrame = tk.LabelFrame(createFrame, text='Elije el escenario base')
    selectBaseFrame.grid(row=3, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    selectBaseFrame.rowconfigure(0, weight=1)
    selectBaseFrame.rowconfigure(1, weight=1)
    selectBaseFrame.columnconfigure(0, weight=1)
    selectBaseFrame.columnconfigure(1, weight=1)
    selectBaseFrame.columnconfigure(2, weight=1)
    selectBaseFrame.columnconfigure(3, weight=1)

    tk.Button(selectBaseFrame, text="1", bg="dark orange", command = lambda:  selectBase ("1"))\
        .grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectBaseFrame, text="2V", bg="dark orange", command=lambda: selectBase("2V")) \
        .grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectBaseFrame, text="2H", bg="dark orange", command=lambda: selectBase("2H")) \
        .grid(row=0, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectBaseFrame, text="3V", bg="dark orange", command=lambda: selectBase("3V")) \
        .grid(row=0, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectBaseFrame, text="3H", bg="dark orange", command=lambda: selectBase("3H")) \
        .grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectBaseFrame, text="4V", bg="dark orange", command=lambda: selectBase("4V")) \
        .grid(row=1, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectBaseFrame, text="4H", bg="dark orange", command=lambda: selectBase("4H")) \
        .grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    tk.Button(selectBaseFrame, text="4M", bg="dark orange", command=lambda: selectBase("4M")) \
        .grid(row=1, column=3, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    inclusionFenceFrame = tk.LabelFrame (createFrame, text ='Definición de los límites del escenario')
    inclusionFenceFrame.grid(row=4, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    inclusionFenceFrame.rowconfigure(0, weight=1)
    inclusionFenceFrame.columnconfigure(0, weight=1)
    inclusionFenceFrame.columnconfigure(1, weight=1)
    # el fence de inclusión puede ser un poligono o un círculo
    # el parámetro 1 en el command indica que es fence de inclusion
    polyInclusionFenceBtn = tk.Button(inclusionFenceFrame, text="Polígono", bg="dark orange", command = definePoly)
    polyInclusionFenceBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    circleInclusionFenceBtn = tk.Button(inclusionFenceFrame, text="Círculo", bg="dark orange", command = defineCircle)
    circleInclusionFenceBtn.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    # los obstacilos son fences de exclusión y pueden ser también polígonos o círculos
    # el parámetro 2 en el command indica que son fences de exclusión
    obstacleFrame = tk.LabelFrame(createFrame, text='Definición de los obstaculos del escenario')
    obstacleFrame.grid(row=4, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    obstacleFrame.rowconfigure(0, weight=1)
    obstacleFrame.columnconfigure(0, weight=1)
    obstacleFrame.columnconfigure(1, weight=1)

    polyObstacleBtn = tk.Button(obstacleFrame, text="Polígono", bg="dark orange", command = definePoly )
    polyObstacleBtn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    circleObstacleBtn = tk.Button(obstacleFrame, text="Círculo", bg="dark orange", command=defineCircle)
    circleObstacleBtn.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    registerBtn = tk.Button(createFrame, text="Registra escenario", bg="dark orange", command = registerScenario)
    registerBtn.grid(row=5, column=0, padx=5, pady=5, sticky=tk.N +tk.E + tk.W)

    clearBtn = tk.Button(createFrame, text="Limpiar", bg="dark orange", command=clear)
    clearBtn.grid(row=6, column=0, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

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
        comPorts = askstring('Puertos', "Indica los puertos COM separados por comas (por ejemplo: 'COM3,COM21,COM7')")

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
    superviseFrame.rowconfigure(4, weight=1)
    superviseFrame.rowconfigure(5, weight=1)


    superviseFrame.columnconfigure(0, weight=1)
    superviseFrame.columnconfigure(1, weight=1)
    superviseFrame.columnconfigure(2, weight=1)
    superviseFrame.columnconfigure(3, weight=1)

    parametersBtn = tk.Button(superviseFrame, text="Ajustar parámetros", bg="dark orange", command=adjustParameters)
    parametersBtn.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    # debajo de este label colocaremos botones para aterrizar los drones.
    # los colocaremos cuando sepamos cuántos drones tenemos en el enjambre
    controlesFrame = tk.LabelFrame(superviseFrame, text='Controles')
    controlesFrame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    controlesFrame.rowconfigure(0, weight=1)
    controlesFrame.rowconfigure(1, weight=1)
    controlesFrame.rowconfigure(3, weight=1)
    controlesFrame.rowconfigure(4, weight=1)
    controlesFrame.columnconfigure(0, weight=1)
    controlesFrame.columnconfigure(1, weight=1)
    controlesFrame.columnconfigure(2, weight=1)
    controlesFrame.columnconfigure(3, weight=1)

    # debajo de este label colocaremos las alturas en las que están los drones
    # las colocaremos cuando sepamos cuántos drones tenemos en el enjambre
    telemetriaFrame = tk.LabelFrame(superviseFrame, text='Telemetría (altitud y modo de vuelo')
    telemetriaFrame.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    telemetriaFrame.rowconfigure(0, weight=1)
    telemetriaFrame.rowconfigure(1, weight=1)
    telemetriaFrame.columnconfigure(0, weight=1)
    telemetriaFrame.columnconfigure(1, weight=1)
    telemetriaFrame.columnconfigure(2, weight=1)
    telemetriaFrame.columnconfigure(3, weight=1)

    showQRBtn = tk.Button(superviseFrame, text="Mostrar código QR de mobile web APP", bg="dark orange", command=showQR)
    showQRBtn.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    startCompetitionBtn = tk.Button(superviseFrame, text="Iniciar la carrera", bg="dark orange", command=startCompetition)
    startCompetitionBtn.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)

    pointsFrame = tk.LabelFrame(superviseFrame, text='Puntuación')
    pointsFrame.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky=tk.N + tk.E + tk.W)
    pointsFrame.rowconfigure(0, weight=1)
    pointsFrame.columnconfigure(0, weight=1)
    pointsFrame.columnconfigure(1, weight=1)
    pointsFrame.columnconfigure(2, weight=1)
    pointsFrame.columnconfigure(3, weight=1)



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
    map_widget.add_right_click_menu_command(label="Cierra el fence", command=closeObstacle, pass_coords=True)
    map_widget.add_left_click_map_command(getFenceWaypoint)

    # ahora cargamos las imagenes de los iconos que vamos a usar

    # iconos para representar cada dron (circulo de color) y para marcar su rastro (círculo más pequeño del mismo color)
    im = Image.open("images/red.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    red = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littleRed = ImageTk.PhotoImage(im_resized_plus)

    im = Image.open("images/blue.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    blue = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littleBlue = ImageTk.PhotoImage(im_resized_plus)

    im = Image.open("images/green.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    green = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littleGreen = ImageTk.PhotoImage(im_resized_plus)


    im = Image.open("images/yellow.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    yellow = ImageTk.PhotoImage(im_resized)
    im_resized_plus = im.resize((10, 10), Image.LANCZOS)
    littleYellow = ImageTk.PhotoImage(im_resized_plus)


    im = Image.open("images/black.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    black = ImageTk.PhotoImage(im_resized)

    im = Image.open("images/white.png")
    im_resized = im.resize((20, 20), Image.LANCZOS)
    white = ImageTk.PhotoImage(im_resized)

    im = Image.open("images/targetIcon.png")
    im_resized = im.resize((30, 30), Image.LANCZOS)
    diana = ImageTk.PhotoImage(im_resized)

    dronPictures = [red, blue, green, yellow]
    colors =['red', 'blue', 'green', 'yellow']
    # para dibujar los rastros
    dronLittlePictures = [littleRed, littleBlue, littleGreen, littleYellow]

    '''# nos conectamos al broker para recibir las ordenes de los que vuelan con la web app
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
    # para garantizar acceso excluyente a las estructuras para pintar el rastro
    lock = threading.Lock()'''

    return ventana


if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.mainloop()
