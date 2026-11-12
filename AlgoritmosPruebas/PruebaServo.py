import RPi.GPIO as GPIO
import time
# DEPENDENCIAS NECESARIAS - Instalar librerias:
# sudo apt update
# sudo apt upgrade -y
# sudo apt install python3 python3-pip -y
# pip3 install RPi.GPIO
#
# ==========================================================
# CONEXIONES
# Los colores de los cables pueden variar dependiendo
# del fabricante del servomotor.
# Identificar 
# GND      -> Tierra
# VCC      -> Alimentacion
# SIGNAL   -> Senal PWM

# RESUMEN
#
# Servo GND      -> Raspberry Pin 6
# Servo VCC      -> Raspberry Pin 2
# Servo SIGNAL   -> Raspberry Pin 12
#
#
# EJEMPLOS DE COLORES COMUNES
#
# SG90:
# Marron  -> GND
# Rojo    -> VCC
# Naranja -> SIGNAL
#
#
# Otros modelos:
# Negro   -> GND
# Rojo    -> VCC
# Blanco  -> SIGNAL
#
#
# Otros modelos:
# Negro    -> GND
# Rojo     -> VCC
# Amarillo -> SIGNAL
#
# ==========================================================

SERVO_GPIO = 18 # Numeracion de pin no fisico 

GPIO.setmode(GPIO.BCM)

GPIO.setup(SERVO_GPIO, GPIO.OUT)

# Frecuencia PWM de 50 Hz

pwm = GPIO.PWM(SERVO_GPIO, 50)

pwm.start(0)


def angle_to_duty(angle):

    """
    Convierte un angulo entre 0 y 180
    a un duty cycle para PWM.
    """

    return 2 + (angle / 18)


def move_servo(angle):

    """
    Mueve el servo al angulo indicado.

    Parametros:
        angle -> valor entre 0 y 180
    """

    duty = angle_to_duty(angle)

    pwm.ChangeDutyCycle(duty)

    time.sleep(0.5)

    pwm.ChangeDutyCycle(0)


try:

    print("====================================")
    print("PRUEBA DE SERVOMOTOR")
    print("====================================")

    print("\nMoviendo a 0 grados")
    move_servo(0)
    time.sleep(2)

    print("Moviendo a 45 grados")
    move_servo(45)
    time.sleep(2)

    print("Moviendo a 90 grados")
    move_servo(90)
    time.sleep(2)

    print("Moviendo a 135 grados")
    move_servo(135)
    time.sleep(2)

    print("Moviendo a 180 grados")
    move_servo(180)
    time.sleep(2)

    print("\nIniciando barrido completo")

    for angle in range(0, 181, 10):

        print(f"Angulo objetivo: {angle}")

        move_servo(angle)

    for angle in range(180, -1, -10):

        print(f"Angulo objetivo: {angle}")

        move_servo(angle)

    print("\nPrueba finalizada correctamente")

except KeyboardInterrupt:

    print("\nPrueba cancelada por usuario")

finally:

    pwm.stop()

    GPIO.cleanup()

    print("\nGPIO liberados")