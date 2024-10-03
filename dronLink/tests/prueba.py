from pymavlink import mavutil

# Conectar al vehículo (puerto serial o UDP)
connection = mavutil.mavlink_connection('com21',57600)

# Esperar a recibir el mensaje HEARTBEAT para confirmar la conexión
connection.wait_heartbeat()
print("Conexión establecida con el vehículo.")

# Lista de parámetros que deseas leer
parametros_a_leer = [ 'BATTERY_CAPACITY', 'RTL_ALT']


# Función para solicitar un parámetro específico
def solicitar_parametro(param_name):
    connection.mav.param_request_read_send(
        connection.target_system,  # Target system (ID del sistema)
        connection.target_component,  # Target component (ID del componente)
        param_name.encode('utf-8'),  # Nombre del parámetro
        -1  # Parámetro index (-1 para ignorar el index)
    )


# Leer y mostrar los valores de los parámetros especificados
for param in parametros_a_leer:
    solicitar_parametro(param)

    # Esperar la respuesta con el valor del parámetro solicitado
    message = connection.recv_match(type='PARAM_VALUE', blocking=True)

    if message:
        param_name = message.param_id
        param_value = message.param_value
        print(f"Parámetro {param_name}: {param_value}")

print("Lectura de parámetros completada.")
