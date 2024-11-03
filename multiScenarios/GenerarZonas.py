from geographiclib.geodesic import Geodesic

def generarZonas (caso):

    # las coordenadas estan es este orden: NW, NE, SW
    # la coordenada SE la deducimos para que sea un paralelogramo perfecto
    limitesDronLab = [
        [41.2764297, 1.9882223],
        [41.2766152, 1.9890162],
        [41.2761697, 1.9883189]
    ]

    geod = Geodesic.WGS84
    # calculamos ancho (distancia entre NW y NE y orientación horizontal
    g = geod.Inverse(
        limitesDronLab[0][0],
        limitesDronLab[0][1],
        limitesDronLab[1][0],
        limitesDronLab[1][1])

    anchura = float(g["s12"])
    orientacionHorizontal = float(g["azi2"])
    print ('anchura: ', anchura, ' orientaciónHorizontal: ', orientacionHorizontal)

    # calculamos largo (distancia entre NW y SW) y orientación vertical
    g = geod.Inverse(
        limitesDronLab[0][0],
        limitesDronLab[0][1],
        limitesDronLab[2][0],
        limitesDronLab[2][1])

    largo = float(g["s12"])
    orientacionVertical = float(g["azi2"])
    print ('largo: ', largo, ' orientaciónVertical: ', orientacionVertical)

    # calculamos las coordenadas SE
    g = geod.Direct(
        limitesDronLab[2][0],
        limitesDronLab[2][1],
        orientacionHorizontal,
        anchura
    )
    lat = float(g["lat2"])
    lon = float(g["lon2"])
    limitesDronLab.append ([lat, lon])
    print ('limites: ', limitesDronLab)

    if caso == '2V':
        # caso 2 zonas verticales
        distanciaHorizontal = anchura/2
        g = geod.Direct(
            limitesDronLab[0][0],
            limitesDronLab[0][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limitesDronLab[2][0],
            limitesDronLab[2][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        return [[limitesDronLab[0], limitesDronLab[2], punto3, punto4],
                    [punto3, punto4, limitesDronLab[1], limitesDronLab[3]]]
    elif caso == '2H':
        # caso 2 zonas horizontales
        distanciaVertical = largo/2

        g = geod.Direct(
            limitesDronLab[0][0],
            limitesDronLab[0][1],
            orientacionVertical,
            distanciaVertical)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limitesDronLab[1][0],
            limitesDronLab[1][1],
            orientacionVertical,
            distanciaVertical)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        return [[limitesDronLab[0], limitesDronLab[1], punto3, punto4],
                    [punto3, punto4, limitesDronLab[2], limitesDronLab[3]]]


    elif caso == '3V':
        # caso 3 zonas verticales
        distanciaHorizontal = anchura / 3
        g = geod.Direct(
            limitesDronLab[0][0],
            limitesDronLab[0][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limitesDronLab[0][0],
            limitesDronLab[0][1],
            orientacionHorizontal,
            distanciaHorizontal*2)
        punto5 = [float(g["lat2"]), float(g["lon2"])]


        g = geod.Direct(
            limitesDronLab[2][0],
            limitesDronLab[2][1],
            orientacionHorizontal,
            distanciaHorizontal)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limitesDronLab[2][0],
            limitesDronLab[2][1],
            orientacionHorizontal,
            distanciaHorizontal * 2)
        punto6 = [float(g["lat2"]), float(g["lon2"])]

        return [[limitesDronLab[0], limitesDronLab[2], punto3, punto4],
                [punto3, punto4, punto5, punto6],
                [punto5, punto6, limitesDronLab[3], limitesDronLab[1]]]

    elif caso == '3H':
        # caso 3 zonas horizontales
        distanciaVertical = largo / 3

        g = geod.Direct(
            limitesDronLab[0][0],
            limitesDronLab[0][1],
            orientacionVertical,
            distanciaVertical)
        punto4 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limitesDronLab[0][0],
            limitesDronLab[0][1],
            orientacionVertical,
            distanciaVertical*2)
        punto5 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limitesDronLab[2][0],
            limitesDronLab[2][1],
            orientacionVertical,
            distanciaVertical)
        punto3 = [float(g["lat2"]), float(g["lon2"])]

        g = geod.Direct(
            limitesDronLab[2][0],
            limitesDronLab[2][1],
            orientacionVertical,
            distanciaVertical * 2)
        punto6 = [float(g["lat2"]), float(g["lon2"])]

        return [[limitesDronLab[0], limitesDronLab[1], punto3, punto4],
                [punto3, punto4, punto5, punto6],
                [punto5, punto6, limitesDronLab[3], limitesDronLab[2]]]

