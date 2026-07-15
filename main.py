import json
import csv
import itertools
import numpy as np
import scipy.stats as stats

# =============================================================================
# 1. CARGA DE ARCHIVOS Y CONFIGURACIÓN DE PATHS
# =============================================================================

# TODO: COLOCAR AQUÍ LAS RUTAS DE TUS JSON DE FDP Y OPCIONES
path_consumo = "fdp/fdp_mejor_ajuste_consumo.json"
path_generacion = "fdp/fdp_mejor_ajuste_generacion.json"
path_opciones = "variables_de_control.json"

# Salida del reporte de escenarios
path_salida_csv = "resultados_simulacion.csv"

def cargar_json(ruta):
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)

# Carga de datos iniciales
datos_consumo = cargar_json(path_consumo)
datos_generacion = cargar_json(path_generacion)
opciones = cargar_json(path_opciones)

# =============================================================================
# 2. GENERADOR DE MUESTRAS (FDP)
# =============================================================================
def obtener_muestra(datos_franja):
    if not datos_franja:
        return 0.0
    dist_nombre = datos_franja.get("distribucion")
    params = datos_franja.get("parametros", {})
    
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
    return 0.0

# =============================================================================
# 3. GENERACIÓN DE COMBINACIONES Y SIMULACIÓN
# =============================================================================

# Generamos las 160 combinaciones usando producto cartesiano
combinaciones = list(itertools.product(
    opciones["paneles"],
    opciones["baterias"],
    opciones["cables"],
    opciones["gestor_inteligente"]
))

resultados_globales = []
total_escenarios = len(combinaciones)
print(f"Iniciando simulación de {total_escenarios} escenarios...")

for idx, (panel, bateria, cable, gestor_inteligente) in enumerate(combinaciones, 1):
    if idx % 10 == 0 or idx == 1:
        print(f" -> Procesando escenario {idx}/{total_escenarios}...")

    # Configuración del escenario actual
    potencia_paneles = panel["potencia_kwp"]
    precio_panel = panel["precio_usd"]
    
    capacidad_bateria = bateria["capacidad_kwh"]
    precio_bateria = bateria["precio_usd"]
    
    eficiencia_cables = cable["eficiencia"]
    costo_instalacion_cable = cable["costo_instalacion_usd"]
    material_cable = cable["material"]
    
    # 3.1 Inicialización de Variables del Escenario
    T = 0
    TF = 8760
    
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
    capacidad_actual_bateria = capacidad_bateria
    
    precio_consumo = 0.05 if gestor_inteligente else 0.3
    costo_acumulado = costo_instalacion_cable + precio_panel + precio_bateria
    if gestor_inteligente:
        costo_acumulado += 5000
        
    # 3.2 Loop de Simulación por horas
    while T < TF:
        hora = T % 24
        
        # Obtener Consumo según hora
        if hora >= 5:
            if hora <= 10:
                consumo = obtener_muestra(datos_consumo.get("manana"))
            elif hora <= 17:
                consumo = obtener_muestra(datos_consumo.get("mediodia_tarde"))
            elif hora <= 22:
                consumo = obtener_muestra(datos_consumo.get("noche"))
            else:
                consumo = obtener_muestra(datos_consumo.get("madrugada"))
        else:
            consumo = obtener_muestra(datos_consumo.get("madrugada"))
            
        # Obtener Generación según hora
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
            
        # Escalar generación según los paneles instalados
        generacion *= potencia_paneles
        
        # Ejecución lógica del Diagrama de Flujo
        consumo_total += consumo
        generacion = generacion * eficiencia_cables
        generacion_total += generacion
        
        if generacion >= consumo:
            cant_operaciones_independientes += 1
            excedente = (generacion - consumo) * eficiencia_cables
            
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
        else:
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
                
        # Simulación de desgaste/degradación de batería
        ciclos_actuales = energia_bateria_ciclada / (capacidad_bateria * 2)
        capacidad_actual_bateria = capacidad_bateria - (capacidad_bateria * 0.0002 * ciclos_actuales)
        
        # Reemplazo de batería por fin de vida útil
        if capacidad_actual_bateria < (capacidad_bateria * 0.5):
            capacidad_actual_bateria = capacidad_bateria
            costo_acumulado += precio_bateria
            energia_ciclada_historica += energia_bateria_ciclada
            energia_bateria_ciclada = 0
            carga_bateria = capacidad_bateria
            
        T += 1
        
    # 3.3 Métricas finales de este escenario específico
    porcentaje_autosuficiencia = (cant_operaciones_independientes / TF) * 100
    promedio_ahorro_anual = (consumo_total * 0.3 - costo_acumulado) * (24 * 365 / TF)
    porcentaje_bateria_agotada = (cant_veces_bateria_agotada / TF) * 100
    ciclos_desgaste_anual = (energia_ciclada_historica + energia_bateria_ciclada) / (capacidad_bateria * 2)
    porcentaje_aprovechamiento_solar = (1 - (energia_desperdiciada / generacion_total)) * 100 if generacion_total > 0 else 0.0
    
    # Guardamos los parámetros de entrada y salida del escenario
    resultados_globales.append({
        "Escenario": idx,
        "Potencia Panel (kWp)": potencia_paneles,
        "Precio Panel ($)": precio_panel,
        "Capacidad Batería (kWh)": capacidad_bateria,
        "Precio Batería ($)": precio_bateria,
        "Cable": material_cable,
        "Eficiencia Cable (%)": eficiencia_cables * 100,
        "Costo Instalación Cable ($)": costo_instalacion_cable,
        "Gestor Inteligente": gestor_inteligente,
        "Costo Acumulado Total ($)": round(costo_acumulado, 2),
        "Autosuficiencia Anual (%)": round(porcentaje_autosuficiencia, 2),
        "Ahorro Económico Anual ($)": round(promedio_ahorro_anual, 2),
        "Tiempo Bat Agotada (%)": round(porcentaje_bateria_agotada, 2),
        "Ciclos de Desgaste Anual": round(ciclos_desgaste_anual, 2),
        "Aprovechamiento Solar (%)": round(porcentaje_aprovechamiento_solar, 2)
    })

# =============================================================================
# 4. EXPORTACIÓN A CSV
# =============================================================================
if resultados_globales:
    columnas = resultados_globales[0].keys()
    with open(path_salida_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(resultados_globales)
        
    print(f"\n¡Listo! Simulación completada con éxito.")
    print(f"Los resultados de los 160 escenarios se guardaron en: {path_salida_csv}")