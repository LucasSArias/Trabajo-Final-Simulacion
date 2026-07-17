import pandas as pd

# 1. Cargar todos los resultados crudos de la simulación
df = pd.read_csv("resultados_simulacion.csv")

# 2. TOP 3 RESILIENTES (Prioridad: Independencia de la red)
resilientes = df.sort_values(
    by=["Autosuficiencia Anual (%)", "Porcentaje Bateria Agotada (%)"], 
    ascending=[False, True]
).head(3).copy()
resilientes.insert(1, 'Perfil', 'Resiliente')

# 3. TOP 3 INVERSORES (Prioridad: Beneficio económico)
inversores = df.sort_values(
    by=["Ahorro Económico Anual ($)"], 
    ascending=[False]
).head(3).copy()
inversores.insert(1, 'Perfil', 'Inversor')

# 4. TOP 4 EQUILIBRADOS (Análisis Multicriterio Ponderado)
# Armamos listas con los escenarios que ya ganaron para no repetirlos
escenarios_elegidos = pd.concat([resilientes, inversores])['Escenario'].tolist()
df_restante = df[~df['Escenario'].isin(escenarios_elegidos)].copy()

# Normalización Min-Max (Llevamos todo a una escala de 0 a 1)
max_auto = df_restante['Autosuficiencia Anual (%)'].max()
min_auto = df_restante['Autosuficiencia Anual (%)'].min()
auto_norm = (df_restante['Autosuficiencia Anual (%)'] - min_auto) / (max_auto - min_auto)

max_ahorro = df_restante['Ahorro Económico Anual ($)'].max()
min_ahorro = df_restante['Ahorro Económico Anual ($)'].min()
ahorro_norm = (df_restante['Ahorro Económico Anual ($)'] - min_ahorro) / (max_ahorro - min_ahorro)

max_desgaste = df_restante['Promedio Ciclos de Desgaste Anual'].max()
min_desgaste = df_restante['Promedio Ciclos de Desgaste Anual'].min()
# Al desgaste lo invertimos porque queremos MINIMIZARLO
desgaste_norm = (max_desgaste - df_restante['Promedio Ciclos de Desgaste Anual']) / (max_desgaste - min_desgaste)

# Calculamos el Puntaje Global (50% Auto, 30% Ahorro, 20% Cuidado de Batería)
df_restante['Puntaje_Global'] = (auto_norm * 0.50) + (ahorro_norm * 0.30) + (desgaste_norm * 0.20)

equilibrados = df_restante.sort_values(by="Puntaje_Global", ascending=False).head(4).copy()
equilibrados.insert(1, 'Perfil', 'Equilibrado')
# Eliminamos la columna extra de puntaje para que coincida con el resto
equilibrados = equilibrados.drop(columns=['Puntaje_Global'])

# 5. UNIFICAR Y EXPORTAR EL TOP 10 FINAL
top_10_final = pd.concat([resilientes, inversores, equilibrados])
top_10_final.to_csv("top_10_escenarios_finales.csv", index=False)

print("\nAnálisis Multicriterio finalizado.")
print("El archivo 'top_10_escenarios_finales.csv' fue generado con éxito.")
print("Distribución:")
print(top_10_final[['Escenario', 'Perfil', 'Autosuficiencia Anual (%)', 'Ahorro Económico Anual ($)', 'Gestor Inteligente']])