import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# 1. Cargar el dataset
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'

df = pd.read_csv(DATA_DIR / 'household_data_60min_singleindex.csv')
df['utc_timestamp'] = pd.to_datetime(df['utc_timestamp'])
df.set_index('utc_timestamp', inplace=True)

salida_graficos = Path(__file__).resolve().parent / 'graficos_fdp_consumo'
salida_graficos.mkdir(exist_ok=True)

columnas_consumo_res3 = [
    'DE_KN_residential3_circulation_pump',
    'DE_KN_residential3_dishwasher',
    'DE_KN_residential3_freezer',
    'DE_KN_residential3_refrigerator',
    'DE_KN_residential3_washing_machine'
]

# 2. EL ARREGLO MAGISTRAL: Calcular el consumo real por hora (diferencia con la fila anterior)
# Usamos fillna(0) por si el primer registro queda nulo al no tener un valor previo para restar
df_consumo_real = df[columnas_consumo_res3].diff().fillna(0)

# Sumamos los electrodomésticos pero usando el dataframe con los consumos netos
df['Demanda_Total_Res3'] = df_consumo_real.sum(axis=1)

# 3. Esquivar el linter: Forzamos la lectura del índice como Datetime para sacar la hora
# Esto elimina la línea roja en el editor
hora_del_dia = pd.DatetimeIndex(df.index).hour
perfil_diario = df.groupby(hora_del_dia)['Demanda_Total_Res3'].agg(['mean', 'max'])

print("--- Perfil de Consumo Real por Hora del Día ---")
print(perfil_diario)

# 4. Visualización
plt.figure(figsize=(10, 5))
perfil_diario['mean'].plot(kind='bar', color='skyblue', edgecolor='black')
plt.title('Consumo Promedio Real por Hora - Residential 3')
plt.xlabel('Hora del día (0-23)')
plt.ylabel('Consumo Promedio (kWh)')
plt.xticks(rotation=0)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

ruta_salida = salida_graficos / 'perfil_consumo_real_dia_entero.png'
plt.savefig(ruta_salida, dpi=200, bbox_inches='tight')
plt.close()
print(f'Gráfico guardado en: {ruta_salida}')