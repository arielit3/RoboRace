#!/usr/bin/env python3
"""Pruebas basicas de servos, sensor ultrasonico e IMU por I2C."""

from __future__ import annotations

import argparse
import math
import statistics
import time
from dataclasses import dataclass, replace
from typing import Any, Protocol


@dataclass(frozen=True)
class TestConfig:
    # Usa numeracion BCM, no los numeros fisicos del conector.
    servo_pins: tuple[int, ...] = (18,)
    servo_min_degrees: float = 0.0
    servo_max_degrees: float = 180.0
    servo_positions_degrees: tuple[float, ...] = (15.0, 45.0, 90.0, 135.0, 165.0)
    servo_pause_seconds: float = 0.8
    # Ajusta estos pulsos segun el datasheet para no forzar los topes mecanicos.
    servo_min_pulse_seconds: float = 0.001
    servo_max_pulse_seconds: float = 0.002

    ultrasonic_trigger_pin: int = 23
    ultrasonic_echo_pin: int = 24
    ultrasonic_reference_cm: float = 30.0
    ultrasonic_tolerance_cm: float = 2.0
    ultrasonic_samples: int = 5
    ultrasonic_echo_timeout_seconds: float = 0.04

    i2c_bus: int = 1
    imu_address: int = 0x68
    # MPU6050 devuelve 0x68. Cambia este valor solo tras verificar el datasheet.
    imu_who_am_i_values: tuple[int, ...] = (0x68,)
    imu_samples: int = 5
    imu_sample_pause_seconds: float = 0.1
    imu_min_acceleration_g: float = 0.5
    imu_max_acceleration_g: float = 1.5


CONFIG = TestConfig()


class TriggerPin(Protocol):
    def on(self) -> None: ...

    def off(self) -> None: ...


class EchoPin(Protocol):
    @property
    def is_active(self) -> bool: ...


def measure_distance_cm(
    trigger: TriggerPin,
    echo: EchoPin,
    timeout_seconds: float,
) -> float | None:
    """Mide el tiempo del eco y devuelve distancia en centimetros."""
    deadline = time.monotonic() + timeout_seconds
    while echo.is_active:
        if time.monotonic() >= deadline:
            return None

    trigger.on()
    time.sleep(0.00001)
    trigger.off()

    deadline = time.monotonic() + timeout_seconds
    while not echo.is_active:
        if time.monotonic() >= deadline:
            return None
    pulse_start = time.monotonic()

    deadline = pulse_start + timeout_seconds
    while echo.is_active:
        if time.monotonic() >= deadline:
            return None
    pulse_end = time.monotonic()

    # El sonido recorre la distancia de ida y vuelta.
    return (pulse_end - pulse_start) * 34300.0 / 2.0


def run_servo_test(config: TestConfig, interactive: bool) -> bool:
    from gpiozero import Servo

    if not config.servo_pins:
        raise ValueError("No hay pines de servo configurados.")
    if not config.servo_positions_degrees:
        raise ValueError("No hay posiciones de prueba configuradas.")
    if config.servo_min_degrees >= config.servo_max_degrees:
        raise ValueError("El limite minimo del servo debe ser menor al maximo.")
    if config.servo_min_pulse_seconds >= config.servo_max_pulse_seconds:
        raise ValueError("El pulso minimo debe ser menor al pulso maximo.")
    if config.servo_pause_seconds < 0:
        raise ValueError("La pausa del servo no puede ser negativa.")

    success = True
    for pin in config.servo_pins:
        print(f"\nServo en GPIO BCM {pin}:")
        servo: Any = Servo(
            pin,
            min_pulse_width=config.servo_min_pulse_seconds,
            max_pulse_width=config.servo_max_pulse_seconds,
        )
        try:
            for degrees in config.servo_positions_degrees:
                if not config.servo_min_degrees <= degrees <= config.servo_max_degrees:
                    raise ValueError(f"Angulo fuera de rango: {degrees} grados.")
                value = (
                    2.0
                    * (degrees - config.servo_min_degrees)
                    / (config.servo_max_degrees - config.servo_min_degrees)
                    - 1.0
                )
                servo.value = value
                print(f"  Orden enviada: {degrees:g} grados.")
                time.sleep(config.servo_pause_seconds)

                if interactive:
                    answer = input("  El servo llego a la posicion esperada? [s/N] ")
                    if answer.strip().lower() not in ("s", "si", "y", "yes"):
                        print("  Posicion no confirmada por el operador.")
                        success = False
        finally:
            servo.value = None
            servo.close()

    if not interactive:
        print("  Senal enviada; confirma visualmente que cada servo se movio.")
    return success


def run_ultrasonic_test(config: TestConfig) -> bool:
    from gpiozero import DigitalInputDevice, OutputDevice

    if config.ultrasonic_samples < 1:
        raise ValueError("ultrasonic_samples debe ser al menos 1.")
    if config.ultrasonic_reference_cm <= 0 or config.ultrasonic_tolerance_cm < 0:
        raise ValueError("La distancia de referencia debe ser positiva y la tolerancia no negativa.")
    if config.ultrasonic_echo_timeout_seconds <= 0:
        raise ValueError("El tiempo maximo de espera del eco debe ser positivo.")
    if config.ultrasonic_trigger_pin == config.ultrasonic_echo_pin:
        raise ValueError("Trigger y Echo deben usar pines distintos.")

    trigger = OutputDevice(
        config.ultrasonic_trigger_pin,
        active_high=True,
        initial_value=False,
    )
    echo = DigitalInputDevice(config.ultrasonic_echo_pin, pull_up=False)
    readings: list[float] = []
    try:
        for sample_number in range(1, config.ultrasonic_samples + 1):
            distance = measure_distance_cm(
                trigger,
                echo,
                config.ultrasonic_echo_timeout_seconds,
            )
            if distance is None:
                print(f"  Muestra {sample_number}: sin eco o tiempo agotado.")
            else:
                readings.append(distance)
                print(f"  Muestra {sample_number}: {distance:.1f} cm.")
            time.sleep(0.06)
    finally:
        trigger.close()
        echo.close()

    if len(readings) != config.ultrasonic_samples:
        print("  FALLO: no se recibio eco en todas las muestras.")
        return False

    measured = statistics.median(readings)
    error = abs(measured - config.ultrasonic_reference_cm)
    print(
        f"  Mediana: {measured:.1f} cm; referencia: "
        f"{config.ultrasonic_reference_cm:.1f} cm; error: {error:.1f} cm."
    )
    if error > config.ultrasonic_tolerance_cm:
        print(
            "  FALLO: el error supera la tolerancia de "
            f"{config.ultrasonic_tolerance_cm:.1f} cm."
        )
        return False

    print("  OK: la distancia esta dentro de la tolerancia.")
    return True


def signed_word(high_byte: int, low_byte: int) -> int:
    value = (high_byte << 8) | low_byte
    return value - 65536 if value >= 32768 else value


def run_imu_test(config: TestConfig) -> bool:
    from smbus2 import SMBus

    if config.imu_samples < 1:
        raise ValueError("imu_samples debe ser al menos 1.")
    if config.imu_min_acceleration_g >= config.imu_max_acceleration_g:
        raise ValueError("El rango minimo de aceleracion debe ser menor al maximo.")
    if config.imu_sample_pause_seconds < 0:
        raise ValueError("La pausa entre lecturas del IMU no puede ser negativa.")

    bus: Any = SMBus(config.i2c_bus)
    try:
        identity = bus.read_byte_data(config.imu_address, 0x75)
        print(f"  WHO_AM_I: 0x{identity:02X}.")
        if identity not in config.imu_who_am_i_values:
            expected = ", ".join(f"0x{value:02X}" for value in config.imu_who_am_i_values)
            print(f"  FALLO: se esperaba uno de estos identificadores: {expected}.")
            return False

        # Despierta el MPU6050, que normalmente inicia en modo de suspension.
        bus.write_byte_data(config.imu_address, 0x6B, 0x00)
        # Fija escalas conocidas para que las conversiones de abajo sean validas.
        bus.write_byte_data(config.imu_address, 0x1C, 0x00)
        bus.write_byte_data(config.imu_address, 0x1B, 0x00)
        time.sleep(0.1)

        magnitudes: list[float] = []
        for sample_number in range(1, config.imu_samples + 1):
            data = bus.read_i2c_block_data(config.imu_address, 0x3B, 14)
            if len(data) != 14:
                raise OSError(f"Lectura I2C incompleta: se recibieron {len(data)} bytes.")

            accel = [
                signed_word(data[0], data[1]),
                signed_word(data[2], data[3]),
                signed_word(data[4], data[5]),
            ]
            gyro = [
                signed_word(data[8], data[9]),
                signed_word(data[10], data[11]),
                signed_word(data[12], data[13]),
            ]

            # La escala por defecto del MPU6050 es +/-2 g y +/-250 grados/s.
            accel_g = [axis / 16384.0 for axis in accel]
            gyro_dps = [axis / 131.0 for axis in gyro]
            magnitude = math.sqrt(sum(axis * axis for axis in accel_g))
            magnitudes.append(magnitude)
            print(
                f"  Muestra {sample_number}: aceleracion "
                f"({accel_g[0]:+.2f}, {accel_g[1]:+.2f}, {accel_g[2]:+.2f}) g; "
                f"giroscopio ({gyro_dps[0]:+.1f}, {gyro_dps[1]:+.1f}, "
                f"{gyro_dps[2]:+.1f}) grados/s."
            )
            time.sleep(config.imu_sample_pause_seconds)
    finally:
        bus.close()

    average_magnitude = statistics.mean(magnitudes)
    print(f"  Magnitud media de aceleracion: {average_magnitude:.2f} g.")
    if not config.imu_min_acceleration_g <= average_magnitude <= config.imu_max_acceleration_g:
        print(
            "  FALLO: la magnitud no esta en el rango esperado con el sensor quieto "
            f"({config.imu_min_acceleration_g:.2f} a "
            f"{config.imu_max_acceleration_g:.2f} g)."
        )
        return False

    print("  OK: I2C responde y la aceleracion es plausible.")
    return True


def run_component(name: str, test: Any, *args: Any) -> bool:
    print(f"\n=== Prueba: {name} ===")
    try:
        return bool(test(*args))
    except Exception as error:
        print(f"  FALLO: {type(error).__name__}: {error}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pruebas de hardware para Raspberry Pi 4."
    )
    parser.add_argument(
        "--only",
        choices=("all", "servo", "ultrasonic", "imu"),
        default="all",
        help="Ejecuta todas las pruebas o solo un componente.",
    )
    parser.add_argument(
        "--reference-cm",
        type=float,
        default=CONFIG.ultrasonic_reference_cm,
        help="Distancia real medida desde el sensor hasta el objetivo, en cm.",
    )
    parser.add_argument(
        "--tolerance-cm",
        type=float,
        default=CONFIG.ultrasonic_tolerance_cm,
        help="Error maximo permitido para el ultrasonico, en cm.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=CONFIG.ultrasonic_samples,
        help="Numero de muestras del ultrasonico.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Pide confirmacion visual de cada posicion del servo.",
    )
    args = parser.parse_args()
    config = replace(
        CONFIG,
        ultrasonic_reference_cm=args.reference_cm,
        ultrasonic_tolerance_cm=args.tolerance_cm,
        ultrasonic_samples=args.samples,
    )

    selected = args.only
    results: list[tuple[str, bool]] = []
    if selected in ("all", "servo"):
        results.append(
            (
                "servo",
                run_component("servomotores", run_servo_test, config, args.interactive),
            )
        )
    if selected in ("all", "ultrasonic"):
        results.append(
            (
                "ultrasonic",
                run_component("sensor ultrasonico", run_ultrasonic_test, config),
            )
        )
    if selected in ("all", "imu"):
        results.append(
            (
                "imu",
                run_component("MPU6080 o IMU compatible", run_imu_test, config),
            )
        )

    print("\n=== Resumen ===")
    for name, success in results:
        print(f"{name}: {'OK' if success else 'FALLO'}")
    return 0 if all(success for _, success in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())