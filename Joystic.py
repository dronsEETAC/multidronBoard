import threading
import pygame
import time


class Joystic:
    def __init__(self, num, dron, idCallback):

        self.dron = dron
        # este será el identificador de joystic
        self.id = num
        # guardo la funcion que hay que ejecutar cuando pulse el boton 4 (identificación)
        self.idCallBack = idCallback

        threading.Thread(target=self.control_loop).start()

    def changeHeading (self, id):
        self.dron.changeHeading(0)


    def control_loop (self):
        # Inicializar pygame y el módulo de joystick
        pygame.init()
        pygame.joystick.init()
        # Obtener el primer joystick
        self.joystick = pygame.joystick.Joystick(self.id)
        self.joystick.init()
        if self.joystick.get_name() == 'USB Gamepad':
            self.pitch = 2
        elif self.joystick.get_name() == 'Generic USB Joystick':
            self.pitch = 4

        while True:
            pygame.event.pump()
            # Leer estado de botones  y ejes
            roll = self.map_axis(self.joystick.get_axis(3))  # RC1: Roll
            pitch = self.map_axis(self.joystick.get_axis(self.pitch))  # RC2: Pitch
            throttle = self.map_axis(-self.joystick.get_axis(1))  # RC3: Throttle
            yaw = self.map_axis(self.joystick.get_axis(0))  # RC4: Yaw
            self.dron.send_rc( roll, pitch, throttle, yaw)


            if self.joystick.get_button(8) == 1:
                self.dron.arm()
                print("Armado")
            if self.joystick.get_button(9) == 1:
                self.dron.takeOff(5, blocking = False, callback=self.changeHeading)
                print("En el aire")

            if self.joystick.get_button(0) == 1:
                self.dron.RTL(blocking = False)
                print("Retornado")
            if self.joystick.get_button(1) == 1:
                self.dron.setFlightMode('GUIDED')
                print("Modo Guided")
            if self.joystick.get_button(2) == 1:
                self.dron.Land(blocking = False)
                print("Aterrizado")
            if self.joystick.get_button(3) == 1:
                self.dron.setFlightMode('LOITER')
                print("Modo Loiter")
            if self.joystick.get_button(4) == 1:
                self.idCallBack (self.id)

            time.sleep(0.1)

    def map_axis(self, value):
        """Convierte valor del eje (-1 a 1) a rango RC (1000 a 2000)"""
        return int(1500 + value * 500)

    def map_axis_yaw(self, value):
        """Convierte valor del eje (-1 a 1) a rango RC (1000 a 2000)"""
        return int(1500 + value *value*value*value* 500)
