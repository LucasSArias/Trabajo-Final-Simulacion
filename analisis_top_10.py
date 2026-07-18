import pandas as pd
import numpy as np

def analizar_mejores_escenarios():
    # 1. Cargar todos los resultados crudos de la simulación
    try:
        df = pd.read_csv("resultados_simulacion.csv")
    except FileNotFoundError:
        print("Error: No se encontró 'resultados_simulacion.csv'. Ejecutá el main primero.")
        return

    print("Procesando análisis multicriterio avanzado...")

    # 1. Cálculos de Inversión y Recupero
    df['Costo Gestor'] = np.where(df['Gestor Inteligente'] == True, 5000, 0)
    df['Inversión Inicial ($)'] = df['Precio Panel ($)'] + df['Precio Batería ($)'] + df['Costo Instalación Cable ($)'] + df['Costo Gestor']
    
    # Calculamos el Tiempo de Recupero (Años).
    # Si el ahorro es nulo o negativo, asignamos un castigo de 999 años para excluirlo.
    df['Tiempo de Recupero (Años)'] = np.where(
        df['Ahorro Económico Anual ($)'] > 0, 
        df['Inversión Inicial ($)'] / df['Ahorro Económico Anual ($)'], 
        999 
    )

    columnas_reporte = [
        "Escenario", "Potencia Panel (kWp)", "Capacidad Batería (kWh)", 
        "Gestor Inteligente", "Autosuficiencia Anual (%)", 
        "Energía Inyectada a Red Anual (kWh)", "Tiempo de Recupero (Años)", 
        "Promedio Ciclos de Desgaste Anual"
    ]

    # 2. TOP 3 RESILIENTES (Off-grid financieramente inteligente)
    # Mayor autosuficiencia, desempatando por el retorno de inversión más rápido (menor tiempo de recupero)
    resilientes = df.sort_values(
        by=["Autosuficiencia Anual (%)", "Tiempo de Recupero (Años)"], 
        ascending=[False, True]
    ).head(3).copy()
    resilientes.insert(1, 'Perfil de Diseño', 'Resiliente')

    # 3. TOP 3 INVERSORES / COLABORADORES DE RED
    # Priorizamos la mayor inyección de energía a la red, desempatando por el recupero más rápido
    inversores = df.sort_values(
        by=["Energía Inyectada a Red Anual (kWh)", "Tiempo de Recupero (Años)"], 
        ascending=[False, True]
    ).head(3).copy()
    inversores.insert(1, 'Perfil de Diseño', 'Inversor')

    # 4. TOP 4 EQUILIBRADOS (Multicriterio Ponderado Definitivo)
    escenarios_elegidos = pd.concat([resilientes, inversores])['Escenario'].tolist()
    df_restante = df[~df['Escenario'].isin(escenarios_elegidos)].copy()

    # Funciones de normalización segura (previene división por cero si todos los valores son iguales)
    def normalizar_max(serie):
        if serie.max() == serie.min(): return serie * 0.0
        return (serie - serie.min()) / (serie.max() - serie.min())
    
    def normalizar_min(serie):
        if serie.max() == serie.min(): return serie * 0.0
        return (serie.max() - serie) / (serie.max() - serie.min())

    # Llevamos las 4 métricas clave a una escala de 0 a 1
    auto_norm = normalizar_max(df_restante['Autosuficiencia Anual (%)'])
    inyeccion_norm = normalizar_max(df_restante['Energía Inyectada a Red Anual (kWh)'])
    recupero_norm = normalizar_min(df_restante['Tiempo de Recupero (Años)'])
    desgaste_norm = normalizar_min(df_restante['Promedio Ciclos de Desgaste Anual'])

    # Puntaje Global equilibrado:
    # 30% Autosuficiencia (Cumplir el objetivo base del usuario)
    # 30% Tiempo de Recupero (Viabilidad financiera real)
    # 20% Energía Inyectada (Ayuda sistémica a mitigar picos de la red)
    # 20% Ciclos de Desgaste (Durabilidad y salud del hardware)
    df_restante['Puntaje_Global'] = (auto_norm * 0.30) + (recupero_norm * 0.30) + (inyeccion_norm * 0.20) + (desgaste_norm * 0.20)

    equilibrados = df_restante.sort_values(by="Puntaje_Global", ascending=False).head(4).copy()
    equilibrados.insert(1, 'Perfil de Diseño', 'Equilibrado')

    # 5. UNIFICAR Y EXPORTAR
    top_10_final = pd.concat([resilientes, inversores, equilibrados])
    top_10_limpio = top_10_final[['Perfil de Diseño'] + columnas_reporte]

    nombre_salida = "top_10_escenarios_finales.csv"
    top_10_limpio.to_csv(nombre_salida, index=False)

    print(f"\n¡Análisis definitivo finalizado con éxito!")
    print(f"Archivo generado: '{nombre_salida}'\n")
    
    # Formateo visual para la terminal
    mostrar_terminal = top_10_limpio[['Escenario', 'Perfil de Diseño', 'Autosuficiencia Anual (%)', 'Energía Inyectada a Red Anual (kWh)', 'Tiempo de Recupero (Años)', 'Promedio Ciclos de Desgaste Anual']].copy()
    mostrar_terminal['Tiempo de Recupero (Años)'] = mostrar_terminal['Tiempo de Recupero (Años)'].round(1)
    mostrar_terminal['Energía Inyectada a Red Anual (kWh)'] = mostrar_terminal['Energía Inyectada a Red Anual (kWh)'].round(0)
    mostrar_terminal['Promedio Ciclos de Desgaste Anual'] = mostrar_terminal['Promedio Ciclos de Desgaste Anual'].round(1)
    
    print(mostrar_terminal.to_string(index=False))

if __name__ == "__main__":
    analizar_mejores_escenarios()