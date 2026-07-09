import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from fitter import Fitter
from pathlib import Path
import json

# 1. Cargar y preparar el dataset
df = pd.read_csv('household_data_60min_singleindex.csv')
df['utc_timestamp'] = pd.to_datetime(df['utc_timestamp'])
df.set_index('utc_timestamp', inplace=True)

salida_graficos = Path(__file__).resolve().parent / 'graficos_fdp'
salida_graficos.mkdir(exist_ok=True)
salida_fdp = Path(__file__).resolve().parent / 'fdp_mejor_ajuste_residential3.json'

resultados_fdp = {}

columnas_consumo = [
    'DE_KN_residential3_circulation_pump',
    'DE_KN_residential3_dishwasher',
    'DE_KN_residential3_freezer',
    'DE_KN_residential3_refrigerator',
    'DE_KN_residential3_washing_machine'
]

df_consumo_real = df[columnas_consumo].diff().fillna(0)
df['Demanda_Total'] = df_consumo_real.sum(axis=1)
df['Hora'] = pd.DatetimeIndex(df.index).hour

# 2. SEPARAR LOS DATOS (usamos .values)
datos_madrugada = df[(df['Hora'] >= 23) | (df['Hora'] <= 4)]['Demanda_Total'].values
datos_manana = df[(df['Hora'] >= 5) & (df['Hora'] <= 10)]['Demanda_Total'].values
datos_tarde = df[(df['Hora'] >= 11) & (df['Hora'] <= 17)]['Demanda_Total'].values
datos_noche = df[(df['Hora'] >= 18) & (df['Hora'] <= 22)]['Demanda_Total'].values

# 3. FUNCIÓN MEJORADA CON GRÁFICOS PROLIJOS
def normalizar_valor(valor):
    if isinstance(valor, dict):
        return {clave: normalizar_valor(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normalizar_valor(contenido) for contenido in valor]
    if isinstance(valor, np.generic):
        return valor.item()
    return valor


def ajustar_fdp(datos, nombre_franja, clave_franja):
    print(f"\n{'='*50}")
    print(f"Analizando FDP para: {nombre_franja}")
    print(f"{'='*50}")
    
    # Excluimos ceros y valores atípicos absurdamente altos (recorte al percentil 98)
    # Esto soluciona que el eje X se extienda demasiado
    datos_limpios = datos[datos > 0]
    limite_superior = np.percentile(datos_limpios, 98)
    datos_filtrados = datos_limpios[datos_limpios <= limite_superior]
    
    # Preparamos la figura de matplotlib antes de llamar a Fitter
    plt.figure(figsize=(10, 6))
    
    distribuciones_sed = ['norm', 'expon', 'uniform', 'gamma', 'lognorm', 'weibull_min', 'triang']
    
    # Corremos Fitter
    f = Fitter(datos_filtrados, distributions=distribuciones_sed)
    f.fit()
    
    # Mostramos los resultados en consola
    print(f.summary())
    mejor_dist = f.get_best(method='sumsquare_error')
    print(f"\n--> Mejor ajuste para {nombre_franja}: {mejor_dist}")

    nombre_distribucion = next(iter(mejor_dist))
    parametros_distribucion = normalizar_valor(mejor_dist[nombre_distribucion])
    resultados_fdp[clave_franja] = {
        'nombre_franja': nombre_franja,
        'distribucion': nombre_distribucion,
        'parametros': parametros_distribucion,
        'n_muestras': int(len(datos_filtrados)),
        'limite_superior_outlier': float(limite_superior),
    }
    
    # -- PERSONALIZACIÓN DEL GRÁFICO --
    plt.title(f'Ajuste de Distribuciones - {nombre_franja}', fontsize=14, pad=15)
    
    # Etiquetas de los ejes
    plt.xlabel('Consumo de Energía Total de la Casa (kWh)', fontsize=12, labelpad=10)
    plt.ylabel('Densidad de Frecuencia\n(Qué tan común es este consumo)', fontsize=12, labelpad=10)
    
    # Forzar el límite del eje X para hacer el "zoom" sobre la zona importante
    # Le damos un 10% más de margen sobre el límite para que respire el gráfico
    plt.xlim(0, limite_superior * 1.1)
    
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    nombre_archivo = (
        nombre_franja.lower()
        .replace(' ', '_')
        .replace('/', '_')
        .replace('(', '')
        .replace(')', '')
    )
    ruta_salida = salida_graficos / f'fdp_{nombre_archivo}.png'
    plt.savefig(ruta_salida, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Gráfico guardado en: {ruta_salida}")

# 4. EJECUTAR EL ANÁLISIS
ajustar_fdp(datos_madrugada, "Madrugada (23hs a 4hs)", "madrugada")
ajustar_fdp(datos_manana, "Mañana (5hs a 10hs)", "manana")
ajustar_fdp(datos_tarde, "Mediodía/Tarde (11hs a 17hs)", "mediodia_tarde")
ajustar_fdp(datos_noche, "Noche (18hs a 22hs)", "noche")

with salida_fdp.open('w', encoding='utf-8') as archivo:
    json.dump(resultados_fdp, archivo, ensure_ascii=False, indent=2)

print(f"\nArchivo de mejor ajuste guardado en: {salida_fdp}")