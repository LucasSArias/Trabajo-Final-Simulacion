import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Importamos las funciones de tus FDP desde la carpeta fdp/
from fdp.determinar_franjas_horarias_consumo import generar_consumo
from fdp.determinar_franjas_horarias_generacion import generar_generacion
 
# =====================================================================
# 1. CONDICIONES INICIALES (CI)
# =====================================================================
TF = 1440.0                # Tiempo final de simulación (en horas) -> "TF = ver"
T = 0.0                     # Reloj de simulación
DELTA_T = 1.0                # t = t + 1 (Avanza de a 1 hora)
 
# --- Variables de control (según diagrama, hoja "C.I.") ---
capacidad_bateria = 10.0     # Capacidad nominal original (kWh)
eficiencia_cable = 0.95      # Rendimiento físico de la instalación (0 a 1)
gestor_inteligente = True    # Controla tarifas y destino del excedente
potencia_panel = 5.0         # Potencia pico instalada (kWp)
costo_instalacion_cable = 800.0  # NUEVO: variable de control (faltaba)
 
# --- Variables dependientes de las variables de control ---
# El diagrama indica que "dependen de las opciones elegidas en las
# variables de control" pero no da la fórmula exacta -> se dejan
# como función de potencia_panel / capacidad_bateria a modo de
# placeholder. AJUSTAR según la tabla de precios real del proyecto.
def calcular_precio_panel(potencia_panel):
    return potencia_panel * 600.0  # ej: $600 por kWp
 
def calcular_precio_bateria(capacidad_bateria):
    return capacidad_bateria * 400.0  # ej: $400 por kWh
 
precio_panel = calcular_precio_panel(potencia_panel)      # NUEVO (faltaba)
precio_bateria = calcular_precio_bateria(capacidad_bateria)  # NUEVO (faltaba)
precio_consumo = 0.0  # depende de gestor_inteligente (0.15) o no (0.25)
 
# --- Variables de Estado Dinámicas ---
carga_bateria = 0.0
capacidad_actual_bateria = capacidad_bateria
 
# --- Variables auxiliares / de resultado acumuladas (según diagrama) ---
consumo_total = 0.0
generacion_total = 0.0
energia_bateria_ciclada = 0.0
energia_ciclada_historica = 0.0   # NUEVO (faltaba) - se reinicia solo al cambiar batería
cant_veces_bateria_agotada = 0
costo_acumulado = 0.0
energia_consumida = 0.0
cant_operaciones_independientes = 0
energia_desperdiciada = 0.0
energia_inyectada_red = 0.0
lucro_cesante = 0.0
 
# --- Variables de resultado final (calculadas al terminar la simulación) ---
porcentaje_autosuficiencia_anual = 0.0
promedio_anual_energia_desperdiciada = 0.0
promedio_mensual_deficit_energetico = 0.0
ciclos_desgaste_anual = 0.0
promedio_mensual_lucro_cesante = 0.0
promedio_ahorro_economico_anual = 0.0
porcentaje_tiempo_bateria_agotada = 0.0
porcentaje_aprovechamiento_solar = 0.0
promedio_mensual_ingresos_inyeccion = 0.0
 
 
# =====================================================================
# LÓGICA PRINCIPAL DE LA SIMULACIÓN
# =====================================================================
def ejecutar_simulacion():
    global T, carga_bateria, capacidad_actual_bateria, precio_consumo
    global consumo_total, generacion_total, energia_bateria_ciclada
    global energia_ciclada_historica
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
 
        # -----------------------------------------------------------
        # NUEVO: Reemplazo de batería si perdió el 50% de su
        # capacidad original (bloque que faltaba en el código)
        # -----------------------------------------------------------
        if capacidad_actual_bateria < capacidad_bateria * 0.5:
            capacidad_actual_bateria = capacidad_bateria
            costo_acumulado += precio_bateria
            # Se reinicia el contador de ciclos de la batería nueva,
            # guardando el histórico de la batería reemplazada
            energia_ciclada_historica += energia_bateria_ciclada
            energia_bateria_ciclada = 0.0
            # Las baterías se compran llenas
            carga_bateria = capacidad_bateria
 
        T += 1.0
 
        # 3. Cálculo de degradación de la batería por ciclos
        ciclos_actuales = energia_bateria_ciclada / (capacidad_bateria * 2.0)
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
            excedente = (generacion - consumo) * eficiencia_cable
 
            if excedente >= (capacidad_actual_bateria - carga_bateria):
                # Sub-rama Verde (Derecha): Batería se llena al tope y sobra energía
                excedente_restante = excedente - (capacidad_actual_bateria - carga_bateria)
                energia_bateria_ciclada += (capacidad_actual_bateria - carga_bateria)
                carga_bateria = capacidad_actual_bateria
 
                # Decisión del excedente según gestor_inteligente
                if gestor_inteligente:
                    # Se reintegra a la red eléctrica
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
            faltante = (consumo - generacion) / eficiencia_cable
 
            if faltante <= carga_bateria:
                # Sub-rama Verde (Derecha): La batería tiene suficiente energía
                energia_bateria_ciclada += faltante
                carga_bateria -= faltante
                cant_operaciones_independientes += 1
            else:
                # Sub-rama Roja (Izquierda): No alcanza la batería, se consume de la red
                energia_bateria_ciclada += carga_bateria
                cant_veces_bateria_agotada += 1
                costo_acumulado += (faltante - carga_bateria) * precio_consumo
                energia_consumida += (faltante - carga_bateria)
                carga_bateria = 0.0
 
    # Fin del bucle (T >= TF) -> Presentación de resultados
    calculo_resultados()
 
 
def calculo_resultados():
    """
    NUEVO: esta función faltaba casi por completo. El diagrama
    "calculo resultados" (hoja 2) define un bloque de costos finales
    más 9 métricas de resultado que no estaban implementadas.
    """
    global costo_acumulado
    global porcentaje_autosuficiencia_anual, promedio_anual_energia_desperdiciada
    global promedio_mensual_deficit_energetico, ciclos_desgaste_anual
    global promedio_mensual_lucro_cesante, promedio_ahorro_economico_anual
    global porcentaje_tiempo_bateria_agotada, porcentaje_aprovechamiento_solar
    global promedio_mensual_ingresos_inyeccion
 
    # Bloque de costos finales de instalación
    if gestor_inteligente:
        costo_acumulado += 5000
    costo_acumulado += costo_instalacion_cable + precio_panel + precio_bateria
 
    # Métricas de resultado (fórmulas tomadas literalmente del diagrama)
    porcentaje_autosuficiencia_anual = (cant_operaciones_independientes / T) * 100
    promedio_anual_energia_desperdiciada = energia_desperdiciada * (24 * 365 / T)
    promedio_mensual_deficit_energetico = energia_consumida * (24 * 30 / T)
    ciclos_desgaste_anual = (energia_ciclada_historica + energia_bateria_ciclada) / (capacidad_bateria * 2) * (24 * 365 / T)
    promedio_mensual_lucro_cesante = lucro_cesante * (24 * 30 / T)
    promedio_ahorro_economico_anual = (consumo_total * 0.25 - costo_acumulado) * (24 * 365 / T)
    porcentaje_tiempo_bateria_agotada = (cant_veces_bateria_agotada / T) * 100
    porcentaje_aprovechamiento_solar = (1 - (energia_desperdiciada / generacion_total)) * 100
    promedio_mensual_ingresos_inyeccion = energia_inyectada_red * 0.05 * (24 * 30 / T)
 
    resultados()
 
 
def resultados():
    print("\n=======================================================")
    print(" RESULTADOS ")
    print("=======================================================")
    print(f"Tiempo simulado final (T):             {T:.1f} horas")
    print(f"Consumo total de carga:                {consumo_total:.2f} kWh")
    print(f"Generación total neta (con cables):    {generacion_total:.2f} kWh")
    print(f"Energía total de batería ciclada:      {energia_bateria_ciclada:.2f} kWh")
    print(f"Energía ciclada histórica (baterías reemplazadas): {energia_ciclada_historica:.2f} kWh")
    print(f"Capacidad final real de la batería:    {capacidad_actual_bateria:.4f} kWh")
    print(f"Cantidad de veces batería agotada:     {cant_veces_bateria_agotada}")
    print(f"Operaciones independientes realizadas: {cant_operaciones_independientes}")
    print(f"Energía total consumida de la red:     {energia_consumida:.2f} kWh")
    print(f"Energía inyectada a la red eléctrica:  {energia_inyectada_red:.2f} kWh")
    print(f"Energía desperdiciada (sin gestor):    {energia_desperdiciada:.2f} kWh")
    print(f"Lucro cesante acumulado:               ${lucro_cesante:.2f}")
    print(f"Costo / Beneficio neto acumulado:      ${costo_acumulado:.2f}")
    print("-------------------------------------------------------")
    print(" MÉTRICAS FINALES (calculo_resultados)")
    print("-------------------------------------------------------")
    print(f"% Autosuficiencia anual:               {porcentaje_autosuficiencia_anual:.2f} %")
    print(f"Promedio anual energía desperdiciada:  {promedio_anual_energia_desperdiciada:.2f} kWh")
    print(f"Promedio mensual déficit energético:   {promedio_mensual_deficit_energetico:.2f} kWh")
    print(f"Ciclos de desgaste anual:               {ciclos_desgaste_anual:.4f}")
    print(f"Promedio mensual lucro cesante:        ${promedio_mensual_lucro_cesante:.2f}")
    print(f"Promedio ahorro económico anual:       ${promedio_ahorro_economico_anual:.2f}")
    print(f"% Tiempo batería agotada:              {porcentaje_tiempo_bateria_agotada:.2f} %")
    print(f"% Aprovechamiento solar:               {porcentaje_aprovechamiento_solar:.2f} %")
    print(f"Promedio mensual ingresos por inyección: ${promedio_mensual_ingresos_inyeccion:.2f}")
    print("=======================================================\n")
 
 
if __name__ == "__main__":
    ejecutar_simulacion()