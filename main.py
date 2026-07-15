import json
import numpy as np
import scipy.stats as stats

# =============================================================================
# 1. CARGA DE LAS FUNCIONES DE DENSIDAD DE PROBABILIDAD (FDP)
# =============================================================================

path_consumo = "fdp/fdp_mejor_ajuste_consumo.json" 
path_generacion = "fdp/fdp_mejor_ajuste_generacion.json" 

def cargar_json(ruta):
    """Carga un archivo JSON en un diccionario."""
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Advertencia: No se encontró el archivo en {ruta}.")
        return {}

datos_consumo = cargar_json(path_consumo)
datos_generacion = cargar_json(path_generacion)

def obtener_muestra(datos_franja):
    """Genera una muestra aleatoria a partir de la distribución especificada en el JSON."""
    if not datos_franja:
        return 0.0
    
    dist_nombre = datos_franja.get("distribucion")
    params = datos_franja.get("parametros", {})
    
    # Mapeo y generación usando scipy.stats
    if dist_nombre == "norm":
        return stats.norm.rvs(loc=params.get("loc"), scale=params.get("scale"))
    elif dist_nombre == "lognorm":
        return stats.lognorm.rvs(s=params.get("s"), loc=params.get("loc"), scale=params.get("scale"))
    elif dist_nombre == "expon":
        return stats.expon.rvs(loc=params.get("loc"), scale=params.get("scale"))
    elif dist_nombre == "gamma":
        return stats.gamma.rvs(a=params.get("a"), loc=params.get("loc"), scale=params.get("scale"))
    elif dist_nombre == "uniform":
        return stats.uniform.rvs(loc=params.get("loc"), scale=params.get("scale"))
    else:
        return 0.0

# =============================================================================
# 2. INICIALIZACIÓN DE VARIABLES (Subrutina)
# =============================================================================

# TODO: Configurar las variables de control según la elección del usuario
capacidad_bateria = 10
eficiencia_cables = 0.99
potencia_paneles = 3
gestor_inteligente = True
costo_instalacion_cable = 1000.0
precio_panel = 3300.0
precio_bateria = 3000.0

# Variables temporales
T = 0
TF = 8760*10 # 50 años

# Variables Auxiliares
carga_bateria = 0
consumo_total = 0
generacion_total = 0
energia_desperdiciada = 0
energia_consumida = 0
energia_inyectada_red = 0
lucro_cesante = 0
cant_operaciones_independientes = 0
cant_veces_bateria_agotada = 0
energia_bateria_ciclada = 0
energia_ciclada_historica = 0
ciclos_actuales = 0
capacidad_actual_bateria = capacidad_bateria

# Costo inicial y precio de consumo dependiente del gestor
precio_consumo = 0.15 if gestor_inteligente else 0.3
costo_acumulado = costo_instalacion_cable + precio_panel + precio_bateria
if gestor_inteligente:
    costo_acumulado += 5000

# =============================================================================
# 3. RUTINA PRINCIPAL (Loop de Simulación)
# =============================================================================

while T < TF:
    # 3.1 Subrutina de tiempo y selección de distribuciones
    hora = T % 24
    
    # Lógica de Consumo según franja horaria
    if hora >= 5:
        if hora <= 10:
            consumo = obtener_muestra(datos_consumo.get("manana"))
        elif hora <= 17:
            consumo = obtener_muestra(datos_consumo.get("mediodia_tarde"))
        elif hora <= 22:
            consumo = obtener_muestra(datos_consumo.get("noche"))
        else: # 23 a 4 hs
            consumo = obtener_muestra(datos_consumo.get("madrugada"))
    else:
        consumo = obtener_muestra(datos_consumo.get("madrugada"))

    # Lógica de Generación según franja horaria
    if hora >= 4:
        if hora <= 8:
            generacion = obtener_muestra(datos_generacion.get("manana_4hs_a_8hs"))
        elif hora <= 13:
            generacion = obtener_muestra(datos_generacion.get("mediodia_9hs_a_13hs"))
        elif hora <= 18:
            generacion = obtener_muestra(datos_generacion.get("tarde_14hs_a_18hs"))
        else:
            generacion = 0.0
    else:
        generacion = 0.0
        
    # Multiplicador por potencia instalada
    generacion *= potencia_paneles
    
    # 3.2 Lógica principal del diagrama
    consumo_total += consumo
    generacion = generacion * eficiencia_cables
    generacion_total += generacion
    
    if generacion >= consumo:
        cant_operaciones_independientes += 1
        excedente = (generacion - consumo) * eficiencia_cables
        
        # Verificación de capacidad de batería frente al excedente
        if excedente >= (capacidad_actual_bateria - carga_bateria):
            excedente = excedente - (capacidad_actual_bateria - carga_bateria)
            energia_bateria_ciclada += capacidad_actual_bateria - carga_bateria
            carga_bateria = capacidad_actual_bateria
            
            if gestor_inteligente:
                energia_inyectada_red += excedente
                costo_acumulado -= excedente * 0.05
            else:
                energia_desperdiciada += excedente
                lucro_cesante += excedente * 0.05
        else:
            carga_bateria += excedente
            energia_bateria_ciclada += excedente
            
    else: # generacion < consumo
        faltante = (consumo - generacion) / eficiencia_cables
        
        if faltante <= carga_bateria:
            energia_bateria_ciclada += faltante
            carga_bateria -= faltante
            cant_operaciones_independientes += 1
        else:
            energia_bateria_ciclada += carga_bateria
            cant_veces_bateria_agotada += 1
            energia_consumida += (faltante - carga_bateria)
            costo_acumulado += (faltante - carga_bateria) * precio_consumo
            carga_bateria = 0

    # 3.3 Degradación de la Batería
    ciclos_actuales = energia_bateria_ciclada / (capacidad_bateria * 2)
    capacidad_actual_bateria = capacidad_bateria - (capacidad_bateria * 0.0002 * ciclos_actuales)
    
    if capacidad_actual_bateria < (capacidad_bateria * 0.5):
        capacidad_actual_bateria = capacidad_bateria
        costo_acumulado += precio_bateria
        energia_ciclada_historica += energia_bateria_ciclada
        energia_bateria_ciclada = 0
        carga_bateria = capacidad_bateria
        
    # Avance del tiempo
    T += 1

# =============================================================================
# 4. CÁLCULO DE RESULTADOS FINALES
# =============================================================================

# Protecciones para evitar divisiones por cero en el primer ciclo
if T > 0:
    porcentaje_autosuficiencia_anual = (cant_operaciones_independientes / T) * 100
    promedio_anual_energia_desperdiciada = energia_desperdiciada * (24 * 365 / T)
    promedio_mensual_deficit_energetico = energia_consumida * (24 * 30 / T)
    ciclos_desgaste_anual = (energia_ciclada_historica + energia_bateria_ciclada) / (capacidad_bateria * 2) * (24 * 365 / T)
    porcentaje_tiempo_bateria_agotada = (cant_veces_bateria_agotada / T) * 100
    
    # Manejo de división por cero si no hubo generación en toda la simulación
    if generacion_total > 0:
        porcentaje_aprovechamiento_solar = (1 - (energia_desperdiciada / generacion_total)) * 100
    else:
        porcentaje_aprovechamiento_solar = 0.0
        
    promedio_mensual_ingresos_inyeccion = energia_inyectada_red * 0.05 * (24 * 30 / T)
    promedio_ahorro_economico_anual = (consumo_total * 0.25 - costo_acumulado) * (24 * 365 / T)
    promedio_mensual_lucro_cesante = lucro_cesante * (24 * 30 / T)

print("--- RESULTADOS DE LA SIMULACIÓN ---")
print(f"Costo Acumulado Total: ${costo_acumulado:.2f}")
print(f"Porcentaje Autosuficiencia Anual: {porcentaje_autosuficiencia_anual:.2f}%")
print(f"Promedio Ahorro Económico Anual: ${promedio_ahorro_economico_anual:.2f}")
print(f"Porcentaje de Tiempo con Batería Agotada: {porcentaje_tiempo_bateria_agotada:.2f}%")
print(f"Ciclos Desgaste Anual (Promedio): {ciclos_desgaste_anual:.2f}")
print(f"Porcentaje de Aprovechamiento Solar: {porcentaje_aprovechamiento_solar:.2f}%")