import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# 1. Cargar el dataset
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'

df = pd.read_csv(DATA_DIR / 'household_data_60min_singleindex.csv')
df['utc_timestamp'] = pd.to_datetime(df['utc_timestamp'])
df.set_index('utc_timestamp', inplace=True)

salida_graficos = Path(__file__).resolve().parent / 'graficos_fdp_generacion'
salida_graficos.mkdir(exist_ok=True)

columna_pv = 'DE_KN_residential3_pv'

# 2. Calcular la generación real por hora (diferencia con la fila anterior)
df['Generacion_Real_Res3'] = df[columna_pv].diff().fillna(0)
df['Generacion_Real_Res3'] = df['Generacion_Real_Res3'].clip(lower=0)

# 3. Perfil diario por hora
hora_del_dia = pd.DatetimeIndex(df.index).hour
perfil_diario = df.groupby(hora_del_dia)['Generacion_Real_Res3'].agg(['mean', 'max'])

print('--- Perfil de Generación Real por Hora del Día ---')
print(perfil_diario)

# 4. Visualización
plt.figure(figsize=(10, 5))
perfil_diario['mean'].plot(kind='bar', color='goldenrod', edgecolor='black')
plt.title('Generación Promedio Real por Hora - Residential 3 Paneles')
plt.xlabel('Hora del día (0-23)')
plt.ylabel('Generación Promedio (kWh)')
plt.xticks(rotation=0)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

ruta_salida = salida_graficos / 'perfil_generacion_real_paneles_dia_entero.png'
plt.savefig(ruta_salida, dpi=200, bbox_inches='tight')
plt.close()
print(f'Gráfico guardado en: {ruta_salida}')