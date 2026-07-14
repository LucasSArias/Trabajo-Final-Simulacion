import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importamos las funciones de tus FDP desde la carpeta fdp/
from fdp.determinar_franjas_horarias_consumo import generar_consumo
from fdp.determinar_franjas_horarias_generacion import generar_generacion

# =====================================================================
# 1. CONDICIONES INICIALES (CI)
# =====================================================================
TF = 1440.0                # Tiempo final de simulación (en horas)
T = 0.0                    # Reloj de simulación
DELTA_T = 1.0              # t = t + 1 (Avanza de a 1 hora)

# Parámetros configurables del sistema
capacidad_bateria = 10.0   # Capacidad nominal original (kWh)
eficiencia_cable = 0.95    # Rendimiento físico de la instalación (0.95)
gestor_inteligente = True  # Controla tarifas y destino del excedente
potencia_panel = 5.0       # Potencia pico instalada (kWp)

# Variables de Estado Dinámicas (Inicializadas según el diagrama)
carga_bateria = 0.0
# Se inicializa con la capacidad nominal de la batería
capacidad_actual_bateria = capacidad_bateria 

# Variables de Resultado / Estadísticas acumuladas
precio_consumo = 0.0
consumo_total = 0.0
generacion_total = 0.0
energia_bateria_ciclada = 0.0
cant_veces_bateria_agotada = 0
costo_acumulado = 0.0
energia_consumida = 0.0
cant_operaciones_independientes = 0
energia_desperdiciada = 0.0
energia_inyectada_red = 0.0
lucro_cesante = 0.0

# =====================================================================
# LÓGICA PRINCIPAL DE LA SIMULACIÓN
# =====================================================================
def ejecutar_simulacion():
    # Declaramos globales todas las variables dinámicas y estadísticas
    global T, carga_bateria, capacidad_actual_bateria, precio_consumo
    global consumo_total, generacion_total, energia_bateria_ciclada
    global cant_veces_bateria_agotada, costo_acumulado, energia_consumida
    global cant_operaciones_independientes, energia_desperdiciada
    global energia_inyectada_red, lucro_cesante

    # 1. Bloque de decisión: gestor_inteligente determina tarifa
    if gestor_inteligente:
        precio_consumo = 0.15
    else:
        precio_consumo = 0.25

    # 2. Asignación inicial de capacidad actual
    capacidad_actual_bateria = capacidad_bateria

    # Bucle Principal de Simulación (Punto de retorno 'A')
    while T < TF:
        
        T += 1.0
        
        # 3. Cálculo de degradación de la batería por ciclos
        # ciclos_actuales = energia_bateria_ciclada / (capacidad_bateria * 2)
        ciclos_actuales = energia_bateria_ciclada / (capacidad_bateria * 2.0)
        
        # capacidad_actual_bateria = capacidad_bateria - (capacidad_bateria * 0.0002 * ciclos_actuales)
        capacidad_actual_bateria = capacidad_bateria - (capacidad_bateria * 0.0002 * ciclos_actuales)
        
        # 4. Generación de variables aleatorias mediante FDP
        consumo = generar_consumo(T)
        generacion = generar_generacion(T)
        
        # 5. Acumuladores e impacto de eficiencia de cables en generación
        consumo_total += consumo
        generacion = generacion * eficiencia_cable
        generacion_total += generacion
        
        # =================================================================
        # 6. DECISIÓN: balance de energía (generacion >= consumo)
        # =================================================================
        if generacion >= consumo:
            # -------------------------------------------------------------
            # RAMA VERDE (DERECHA): GENERACIÓN >= CONSUMO (SUPERÁVIT)
            # -------------------------------------------------------------
            cant_operaciones_independientes += 1
            
            # excedente = (generacion - consumo) * eficiencia_cable
            excedente = (generacion - consumo) * eficiencia_cable
            
            # Decisión: ¿El excedente cabe en la batería actual?
            # excedente >= capacidad_actual_bateria - carga_bateria
            if excedente >= (capacidad_actual_bateria - carga_bateria):
                # Sub-rama Verde (Derecha): Batería se llena al tope y sobra energía
                
                # excedente = excedente - (capacidad_actual_bateria - carga_bateria)
                excedente_restante = excedente - (capacidad_actual_bateria - carga_bateria)
                
                # energia_bateria_ciclada += capacidad_actual_bateria - carga_bateria
                energia_bateria_ciclada += (capacidad_actual_bateria - carga_bateria)
                
                # carga_bateria = capacidad_actual_bateria
                carga_bateria = capacidad_actual_bateria
                
                # Decisión del excedente según gestor_inteligente
                if gestor_inteligente:
                    # Se inyecta a la red eléctrica
                    energia_inyectada_red += excedente_restante
                    costo_acumulado -= (excedente_restante * 0.05)
                else:
                    # Se desperdicia la energía
                    energia_desperdiciada += excedente_restante
                    lucro_cesante += (excedente_restante * 0.05)
                    
            else:
                # Sub-rama Roja (Izquierda): Todo el excedente se guarda en la batería
                carga_bateria += excedente
                energia_bateria_ciclada += excedente
                
        else:
            # -------------------------------------------------------------
            # RAMA ROJA (IZQUIERDA): GENERACIÓN < CONSUMO (DÉFICIT)
            # -------------------------------------------------------------
            
            # faltante = (consumo - generacion) / eficiencia_cable
            faltante = (consumo - generacion) / eficiencia_cable
            
            # Decisión: ¿La batería cubre el faltante? (faltante <= carga_bateria)
            if faltante <= carga_bateria:
                # Sub-rama Verde (Derecha): La batería tiene suficiente energía
                energia_bateria_ciclada += faltante
                carga_bateria -= faltante
                cant_operaciones_independientes += 1
            else:
                # Sub-rama Roja (Izquierda): No alcanza la batería, se consume de la red
                energia_bateria_ciclada += carga_bateria
                cant_veces_bateria_agotada += 1
                
                # costo_acumulado += (faltante - carga_bateria) * precio_consumo
                costo_acumulado += (faltante - carga_bateria) * precio_consumo
                
                # energia_consumida += (faltante - carga_bateria)
                energia_consumida += (faltante - carga_bateria)
                
                carga_bateria = 0.0

    # Fin del bucle (T >= TF) -> Presentación de resultados
    resultados()

def resultados():
    print("\n=======================================================")
    print(" RESULTADOS ")
    print("=======================================================")
    print(f"Tiempo simulado final (T):             {T:.1f} horas")
    print(f"Consumo total de carga:                {consumo_total:.2f} kWh")
    print(f"Generación total neta (con cables):    {generacion_total:.2f} kWh")
    print(f"Energía total de batería ciclada:      {energia_bateria_ciclada:.2f} kWh")
    print(f"Capacidad final real de la batería:    {capacidad_actual_bateria:.4f} kWh")
    print(f"Cantidad de veces batería agotada:     {cant_veces_bateria_agotada}")
    print(f"Operaciones independientes realizadas:  {cant_operaciones_independientes}")
    print(f"Energía total consumida de la red:     {energia_consumida:.2f} kWh")
    print(f"Energía inyectada a la red eléctrica:  {energia_inyectada_red:.2f} kWh")
    print(f"Energía desperdiciada (sin gestor):    {energia_desperdiciada:.2f} kWh")
    print(f"Lucro cesante acumulado:               ${lucro_cesante:.2f}")
    print(f"Costo / Beneficio neto acumulado:      ${costo_acumulado:.2f}")
    print("=======================================================\n")

if __name__ == "__main__":
    ejecutar_simulacion()