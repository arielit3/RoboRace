# Pruebas de componentes para Raspberry Pi 4

Este directorio contiene `Components_Test.py`, un programa de prueba para servomotores, un sensor ultrasonico y un IMU conectado por I2C.

## Que comprueba el algoritmo

1. **Servomotores:** envia ordenes a varias posiciones y espera entre movimientos. Con `--interactive`, pregunta si cada posicion se alcanzo. Un servo sin sensor de posicion no permite confirmar electricamente su angulo; la confirmacion es visual.
2. **Ultrasonico:** envia pulsos Trigger, mide la duracion del pulso Echo y la convierte a centimetros usando la velocidad aproximada del sonido. Toma varias lecturas, calcula la mediana y la compara con una distancia real y una tolerancia configurables.
3. **IMU:** consulta el registro `WHO_AM_I` por I2C, despierta el MPU6050 y lee acelerometro y giroscopio. Con el sensor quieto comprueba que la magnitud de aceleracion sea plausible, aproximadamente 1 g.

El programa muestra cada lectura y un resumen, y termina con codigo 0 si las pruebas seleccionadas pasan o 1 si alguna falla. No reemplaza una inspeccion electrica ni puede medir la posicion real de un servo sin realimentacion.

## Importante: identificar el IMU

El nombre `MPU6080` no identifica por si solo un mapa de registros verificable. El codigo usa los registros y escalas del **MPU6050** y espera `WHO_AM_I = 0x68`. Antes de ejecutar la prueba, confirma el modelo exacto y el mapa de registros en la hoja de datos del modulo. Si el modulo es compatible pero devuelve otro identificador, actualiza `imu_who_am_i_values` en `CONFIG`. Si usa otro mapa de registros o escalas, hay que adaptar esa parte del codigo; no basta con cambiar el identificador.

## Conexiones de ejemplo

Los pines del programa se numeran en modo **BCM**, no por su posicion fisica en el conector.

| Componente | GPIO BCM por defecto | Conexion adicional |
|---|---:|---|
| Servo 1, senal | 18 | Alimentar el servo con una fuente externa adecuada |
| Ultrasonico Trigger | 23 | GND compartida |
| Ultrasonico Echo | 24 | Reducir 5 V a 3.3 V antes de conectar al GPIO |
| IMU SDA | 2 | Pin fisico 3 |
| IMU SCL | 3 | Pin fisico 5 |

Conecta las tierras de la Raspberry Pi, la fuente externa del servo y los sensores. **No alimentes el servo desde el pin de 5 V o 3.3 V de la Raspberry Pi.** Muchos modulos HC-SR04 entregan 5 V en Echo; usa un divisor resistivo o un conversor de nivel, porque la entrada GPIO de la Pi no es tolerante a 5 V. Comprueba el pinout del modulo antes de conectar la alimentacion.

## Instalar dependencias en Raspberry Pi OS

En una terminal de la Pi:

```bash
sudo apt update
sudo apt install -y python3 python3-gpiozero python3-lgpio python3-smbus2 i2c-tools
sudo raspi-config nonint do_i2c 0
sudo reboot
```

Despues del reinicio, comprueba el bus I2C:

```bash
i2cdetect -y 1
```

El IMU suele aparecer como `68` o `69`, segun el pin AD0. Si no aparece, revisa el cableado, que I2C este habilitado, la alimentacion y la direccion configurada. El script usa `0x68` por defecto.

## Copiar el codigo a la Raspberry Pi

Puedes usar cualquiera de estos metodos:

1. **VS Code Remote - SSH:** conecta VS Code a la Raspberry Pi y copia la carpeta `Algoritmo_Pruebas` al equipo remoto.
2. **SCP desde PowerShell en Windows:** cambia el usuario y la direccion IP por los de tu Pi:

   ```powershell
   scp .\Algoritmo_Pruebas\Components_Test.py usuario@192.168.1.50:/home/usuario/
   ```

3. **Copia manual:** crea `Components_Test.py` en la Pi con un editor de texto y pega el contenido del archivo de este proyecto.

Si usas SCP, conectate por SSH a la Pi y ejecuta los comandos de prueba desde `/home/usuario`.

## Configurar y ejecutar

Edita la seccion `CONFIG = TestConfig(...)` al inicio de `Components_Test.py` para cambiar los pines BCM, la lista de servos, los angulos, la direccion I2C, los limites de aceleracion y los tiempos. Los pulsos del servo estan limitados inicialmente a 1-2 ms para reducir el riesgo de forzar los topes; revisa el datasheet del servo antes de ampliar ese rango. Los argumentos de linea de comandos permiten ajustar la prueba ultrasonica sin editar el archivo:

```bash
python3 Components_Test.py --help
python3 Components_Test.py --only all --reference-cm 30 --tolerance-cm 2 --samples 5 --interactive
```

Mide la distancia desde la cara del sensor hasta un objeto plano y coloca ese valor en `--reference-cm`. No ejecutes una prueba de 30 cm si el objeto no esta realmente a esa distancia. Para probar un componente individual:

```bash
python3 Components_Test.py --only servo --interactive
python3 Components_Test.py --only ultrasonic --reference-cm 30 --tolerance-cm 2
python3 Components_Test.py --only imu
```

Mantiene el IMU quieto durante su prueba. Si cambias la cantidad de muestras con `--samples`, ese valor aplica a la prueba ultrasonica.

## Compatibilidad de Python

Raspberry Pi 4 puede ejecutar Raspberry Pi OS con Python 3. El script requiere Python 3.9 o posterior y usa bibliotecas estandar de Python, `gpiozero`, `lgpio` y `smbus2`. Los comandos de instalacion anteriores instalan las dependencias del sistema y evitan requerir `pip` para este caso.
