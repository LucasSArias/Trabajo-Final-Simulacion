import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fitter import Fitter
from pathlib import Path
import json

# 1. Cargar y preparar el dataset
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'

df = pd.read_csv(DATA_DIR / 'household_data_60min_singleindex.csv')
df['utc_timestamp'] = pd.to_datetime(df['utc_timestamp'])
df.set_index('utc_timestamp', inplace=True)

salida_graficos = Path(__file__).resolve().parent / 'graficos_fdp_generacion'
salida_graficos.mkdir(exist_ok=True)
salida_fdp = Path(__file__).resolve().parent / 'fdp_mejor_ajuste_generacion.json'

resultados_fdp = {}

# 2. Variable de generación solar para residential3
columna_pv = 'DE_KN_residential3_pv'

# 3. Calcular la generación real por hora (diferencia con la fila anterior)
# Como los medidores son acumulativos, restamos para tener la generación neta.
df['Generacion_Real'] = df[columna_pv].diff().fillna(0)

# Filtramos posibles errores del medidor (valores negativos) pasándolos a 0
df['Generacion_Real'] = df['Generacion_Real'].clip(lower=0)

df['Hora'] = pd.DatetimeIndex(df.index).hour

# 4. Separar los datos según las franjas de paneles de la consigna
datos_manana = df[(df['Hora'] >= 4) & (df['Hora'] <= 8)]['Generacion_Real'].values
datos_mediodia = df[(df['Hora'] >= 9) & (df['Hora'] <= 13)]['Generacion_Real'].values
datos_tarde = df[(df['Hora'] >= 14) & (df['Hora'] <= 18)]['Generacion_Real'].values


def normalizar_valor(valor):
	if isinstance(valor, dict):
		return {clave: normalizar_valor(contenido) for clave, contenido in valor.items()}
	if isinstance(valor, (list, tuple)):
		return [normalizar_valor(contenido) for contenido in valor]
	if isinstance(valor, np.generic):
		return valor.item()
	return valor


def ajustar_fdp(datos, nombre_franja):
	print(f"\n{'='*50}")
	print(f"Analizando FDP para: {nombre_franja}")
	print(f"{'='*50}")

	datos_limpios = datos[datos > 0]
	if len(datos_limpios) == 0:
		print("No hay datos positivos suficientes para ajustar una distribución.")
		return

	limite_superior = np.percentile(datos_limpios, 98)
	datos_filtrados = datos_limpios[datos_limpios <= limite_superior]

	plt.figure(figsize=(10, 6))

	distribuciones_sed = ['norm', 'expon', 'uniform', 'gamma', 'lognorm', 'weibull_min', 'triang']
	f = Fitter(datos_filtrados, distributions=distribuciones_sed)
	f.fit()

	print(f.summary())
	mejor_dist = f.get_best(method='sumsquare_error')
	print(f"\n--> Mejor ajuste para {nombre_franja}: {mejor_dist}")

	nombre_distribucion = next(iter(mejor_dist))
	parametros_distribucion = normalizar_valor(mejor_dist[nombre_distribucion])
	clave_franja = nombre_franja.lower()
	clave_franja = (
		clave_franja.replace(' ', '_')
		.replace('/', '_')
		.replace('(', '')
		.replace(')', '')
		.replace('á', 'a')
		.replace('í', 'i')
		.replace('ó', 'o')
		.replace('ú', 'u')
		.replace('ñ', 'n')
	)
	resultados_fdp[clave_franja] = {
		'nombre_franja': nombre_franja,
		'distribucion': nombre_distribucion,
		'parametros': parametros_distribucion,
		'n_muestras': int(len(datos_filtrados)),
		'limite_superior_outlier': float(limite_superior),
	}

	plt.title(f'Ajuste de Distribuciones - {nombre_franja}', fontsize=14, pad=15)
	plt.xlabel('Generación Solar Total (kWh)', fontsize=12, labelpad=10)
	plt.ylabel('Densidad de Frecuencia', fontsize=12, labelpad=10)
	plt.xlim(0, limite_superior * 1.1)
	plt.grid(axis='y', linestyle='--', alpha=0.5)
	plt.tight_layout()

	nombre_archivo = (
		nombre_franja.lower()
		.replace(' ', '_')
		.replace('/', '_')
		.replace('(', '')
		.replace(')', '')
		.replace('á', 'a')
		.replace('í', 'i')
		.replace('ó', 'o')
		.replace('ú', 'u')
		.replace('ñ', 'n')
	)
	ruta_salida = salida_graficos / f'fdp_{nombre_archivo}.png'
	plt.savefig(ruta_salida, dpi=200, bbox_inches='tight')
	plt.close()
	print(f"Gráfico guardado en: {ruta_salida}")


# 5. Ejecutar el análisis para cada franja de paneles
ajustar_fdp(datos_manana, 'Mañana (4hs a 8hs)')
ajustar_fdp(datos_mediodia, 'Mediodía (9hs a 13hs)')
ajustar_fdp(datos_tarde, 'Tarde (14hs a 18hs)')

with salida_fdp.open('w', encoding='utf-8') as archivo:
	json.dump(resultados_fdp, archivo, ensure_ascii=False, indent=2)

print(f"\nArchivo de mejor ajuste guardado en: {salida_fdp}")