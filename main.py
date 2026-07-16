import json
import csv
import itertools
import numpy as np
import scipy.stats as stats

# =============================================================================
# 1. CARGA DE ARCHIVOS Y CONFIGURACIÓN DE PATHS
# =============================================================================

path_consumo = "fdp/fdp_mejor_ajuste_consumo.json"
path_generacion = "fdp/fdp_mejor_ajuste_generacion.json"
path_opciones = "variables_de_control.json"

# Salida del reporte de escenarios
path_salida_csv = "resultados_simulacion.csv"
path_resumen_csv = "resumen_mejores_escenarios.csv"

def cargar_json(ruta):
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)

# Carga de datos iniciales
datos_consumo = cargar_json(path_consumo)
datos_generacion = cargar_json(path_generacion)
opciones = cargar_json(path_opciones)

anios_a_simular = 1

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


def es_mejor_escenario(nombre_metrica, direccion, nuevo, actual, criterios_nuevo, criterios_actual):
    # 0. Filtros excluyentes por definición del sistema
    gestor_nuevo = nuevo["Gestor Inteligente"]

    # El lucro cesante y la energía desperdiciada solo existen si NO hay gestor inteligente
    if nombre_metrica in ["Lucro Cesante Mensual Promedio ($/mes)", "Energía Desperdiciada Anual (kWh)"]:
        if gestor_nuevo: # Si tiene gestor, queda descalificado automáticamente
            return False

    # Los ingresos por inyección solo existen si SÍ hay gestor inteligente
    if nombre_metrica == "Ingresos por Inyección Mensual Promedio ($/mes)":
        if not gestor_nuevo: # Si no tiene gestor, queda descalificado automáticamente
            return False

    # Ahora sí, si pasó el filtro y es el primer escenario evaluado, gana por defecto
    if actual is None:
        return True

    # 1. Evaluamos primero la métrica principal (la que estamos buscando optimizar)
    val_nuevo_ppal = criterios_nuevo[nombre_metrica]
    val_actual_ppal = criterios_actual[nombre_metrica]

    if val_nuevo_ppal != val_actual_ppal:
        return val_nuevo_ppal > val_actual_ppal if direccion == "max" else val_nuevo_ppal < val_actual_ppal

    # 2. Si hay empate, recorremos el diccionario de desempates en cascada
    for metrica_desempate, dir_desempate in objetivos_metricas.items():
        if metrica_desempate == nombre_metrica:
            continue
            
        val_n = criterios_nuevo[metrica_desempate]
        val_a = criterios_actual[metrica_desempate]

        if val_n != val_a:
            return val_n > val_a if dir_desempate == "max" else val_n < val_a

    # 3. Retorno por defecto (solo ocurre si ambos escenarios son clones exactos)
    return False
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

objetivos_metricas = {
    "Autosuficiencia Anual (%)": "max",
    "Déficit Energético Mensual Promedio (kWh/mes)": "min",
    "Energía Desperdiciada Anual (kWh)": "min",
    "Lucro Cesante Mensual Promedio ($/mes)": "min",
    "Ahorro Económico Anual ($)": "max",
    "Porcentaje Bateria Agotada (%)": "min",
    "Promedio Ciclos de Desgaste Anual": "min",
    "Aprovechamiento Solar (%)": "max",
    "Ingresos por Inyección Mensual Promedio ($/mes)": "max",
}

mejores_escenarios = {nombre: None for nombre in objetivos_metricas}
mejores_escenarios_crudos = {nombre: None for nombre in objetivos_metricas}

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
    TF = 8760 * anios_a_simular
    
    #Condiciones iniciales de variables de estado y variables intermedias (usadas para el cálculo de resultados)
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
    precio_reintegro = 0.05
    
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
                    costo_acumulado -= excedente * precio_reintegro
                else:
                    energia_desperdiciada += excedente
                    lucro_cesante += excedente * precio_reintegro
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
        if capacidad_actual_bateria < 1:
            capacidad_actual_bateria = capacidad_bateria
            costo_acumulado += precio_bateria
            energia_ciclada_historica += energia_bateria_ciclada
            energia_bateria_ciclada = 0
            carga_bateria = capacidad_bateria
            
        T += 1
        
    # 3.3 Métricas finales de este escenario específico
    anos_simulados = TF / 8760
    meses_simulados = anos_simulados * 12

    porcentaje_autosuficiencia = (cant_operaciones_independientes / TF) * 100
    promedio_ahorro_anual = (consumo_total * 0.3 - costo_acumulado) * (24 * 365 / TF)
    deficit_energetico_anual = energia_consumida
    deficit_energetico_mensual = deficit_energetico_anual / meses_simulados if meses_simulados > 0 else 0.0
    energia_desperdiciada_anual = energia_desperdiciada if not gestor_inteligente else 0.0
    lucro_cesante_mensual = (lucro_cesante / meses_simulados) if (not gestor_inteligente and meses_simulados > 0) else 0.0
    porcentaje_bateria_agotada = (cant_veces_bateria_agotada / TF) * 100
    ciclos_desgaste_anual = (energia_ciclada_historica + energia_bateria_ciclada) / (capacidad_bateria * 2)
    energia_inyectada_anual = energia_inyectada_red if gestor_inteligente else 0.0
    ingresos_inyeccion_mensual = (energia_inyectada_anual * precio_reintegro / meses_simulados) if (gestor_inteligente and meses_simulados > 0) else 0.0
    energia_utilizada_total = generacion_total - energia_desperdiciada_anual
    porcentaje_aprovechamiento_solar = (energia_utilizada_total / generacion_total) * 100 if generacion_total > 0 else 0.0

    criterios_desempate_escenario = {
        "Ahorro Económico Anual ($)": promedio_ahorro_anual,
        "Autosuficiencia Anual (%)": porcentaje_autosuficiencia,
        "Promedio Ciclos de Desgaste Anual": ciclos_desgaste_anual,
        "Aprovechamiento Solar (%)": porcentaje_aprovechamiento_solar,
        "Energía Desperdiciada Anual (kWh)": energia_desperdiciada_anual,
        "Déficit Energético Mensual Promedio (kWh/mes)": deficit_energetico_mensual,
        "Porcentaje Bateria Agotada (%)": porcentaje_bateria_agotada,
        "Ingresos por Inyección Mensual Promedio ($/mes)": ingresos_inyeccion_mensual,
        "Lucro Cesante Mensual Promedio ($/mes)": lucro_cesante_mensual,
    }
    
    # Guardamos los parámetros de entrada y salida del escenario
    resultado_escenario = {
        "Escenario": idx,
        "Potencia Panel (kWp)": potencia_paneles,
        "Precio Panel ($)": precio_panel,
        "Capacidad Batería (kWh)": capacidad_bateria,
        "Precio Batería ($)": precio_bateria,
        "Cable": material_cable,
        "Eficiencia Cable (%)": eficiencia_cables * 100,
        "Costo Instalación Cable ($)": costo_instalacion_cable,
        "Gestor Inteligente": gestor_inteligente,
        "Autosuficiencia Anual (%)": round(porcentaje_autosuficiencia, 2),
        "Déficit Energético Anual (kWh)": round(deficit_energetico_anual, 2),
        "Déficit Energético Mensual Promedio (kWh/mes)": round(deficit_energetico_mensual, 2),
        "Energía Desperdiciada Anual (kWh)": round(energia_desperdiciada_anual, 2),
        "Lucro Cesante Mensual Promedio ($/mes)": round(lucro_cesante_mensual, 2),
        "Ahorro Económico Anual ($)": round(promedio_ahorro_anual, 2),
        "Porcentaje Bateria Agotada (%)": round(porcentaje_bateria_agotada, 2),
        "Promedio Ciclos de Desgaste Anual": round(ciclos_desgaste_anual, 2),
        "Aprovechamiento Solar (%)": round(porcentaje_aprovechamiento_solar, 2),
        "Energía Inyectada a Red Anual (kWh)": round(energia_inyectada_anual, 2),
        "Ingresos por Inyección Mensual Promedio ($/mes)": round(ingresos_inyeccion_mensual, 2)
    }

    resultados_globales.append(resultado_escenario)

    for nombre_metrica, direccion in objetivos_metricas.items():
        mejor_actual = mejores_escenarios[nombre_metrica]
        mejor_actual_crudo = mejores_escenarios_crudos[nombre_metrica]

        if es_mejor_escenario(nombre_metrica, direccion, resultado_escenario, mejor_actual, criterios_desempate_escenario, mejor_actual_crudo):
            mejores_escenarios[nombre_metrica] = resultado_escenario
            mejores_escenarios_crudos[nombre_metrica] = criterios_desempate_escenario

# =============================================================================
# 4. EXPORTACIÓN A CSV
# =============================================================================
if resultados_globales:
    columnas = resultados_globales[0].keys()
    with open(path_salida_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(resultados_globales)

    resumen_mejores_escenarios = []
    for nombre_metrica, direccion in objetivos_metricas.items():
        mejor_escenario = mejores_escenarios[nombre_metrica]
        if mejor_escenario is None:
            continue

        resumen_mejores_escenarios.append({
            "Metrica": nombre_metrica,
            "Objetivo": "Maximizar" if direccion == "max" else "Minimizar",
            "Escenario": mejor_escenario["Escenario"],
            "Valor": mejor_escenario[nombre_metrica],
            "Potencia Panel (kWp)": mejor_escenario["Potencia Panel (kWp)"],
            "Capacidad Batería (kWh)": mejor_escenario["Capacidad Batería (kWh)"],
            "Cable": mejor_escenario["Cable"],
            "Gestor Inteligente": mejor_escenario["Gestor Inteligente"],
            "Precio Panel ($)": mejor_escenario["Precio Panel ($)"],
            "Precio Batería ($)": mejor_escenario["Precio Batería ($)"],
            "Costo Instalación Cable ($)": mejor_escenario["Costo Instalación Cable ($)"],
            "Autosuficiencia Anual (%)": mejor_escenario["Autosuficiencia Anual (%)"],
            "Déficit Energético Anual (kWh)": mejor_escenario["Déficit Energético Anual (kWh)"],
            "Déficit Energético Mensual Promedio (kWh/mes)": mejor_escenario["Déficit Energético Mensual Promedio (kWh/mes)"],
            "Energía Desperdiciada Anual (kWh)": mejor_escenario["Energía Desperdiciada Anual (kWh)"],
            "Lucro Cesante Mensual Promedio ($/mes)": mejor_escenario["Lucro Cesante Mensual Promedio ($/mes)"],
            "Ahorro Económico Anual ($)": mejor_escenario["Ahorro Económico Anual ($)"],
            "Porcentaje Bateria Agotada (%)": mejor_escenario["Porcentaje Bateria Agotada (%)"],
            "Promedio Ciclos de Desgaste Anual": mejor_escenario["Promedio Ciclos de Desgaste Anual"],
            "Aprovechamiento Solar (%)": mejor_escenario["Aprovechamiento Solar (%)"],
            "Energía Inyectada a Red Anual (kWh)": mejor_escenario["Energía Inyectada a Red Anual (kWh)"],
            "Ingresos por Inyección Mensual Promedio ($/mes)": mejor_escenario["Ingresos por Inyección Mensual Promedio ($/mes)"],
        })

    with open(path_resumen_csv, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = list(resumen_mejores_escenarios[0].keys()) if resumen_mejores_escenarios else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(resumen_mejores_escenarios)
        
    print(f"\n¡Listo! Simulación completada con éxito.")
    print(f"Los resultados de los 160 escenarios se guardaron en: {path_salida_csv}")
    print(f"El resumen tabular de mejores escenarios se guardó en: {path_resumen_csv}")

    print("\nMejores escenarios por métrica:")
    for nombre_metrica, mejor_escenario in mejores_escenarios.items():
        if mejor_escenario is None:
            continue
        print(
            f"- {nombre_metrica}: Escenario {mejor_escenario['Escenario']} | "
            f"Valor = {mejor_escenario[nombre_metrica]} | "
            f"Panel = {mejor_escenario['Potencia Panel (kWp)']} kWp | "
            f"Batería = {mejor_escenario['Capacidad Batería (kWh)']} kWh | "
            f"Cable = {mejor_escenario['Cable']} | "
            f"Gestor Inteligente = {mejor_escenario['Gestor Inteligente']}"
        )

    #Fin