# Simulador de Balance Energético Residencial/Industrial Basado en Datos Reales

## Objetivo

Desarrollar un modelo de simulación de **tiempo discreto con Δt fijo (1 hora)** para evaluar la eficiencia de un sistema de energía renovable compuesto por **paneles solares y una batería**, utilizando series temporales históricas de generación y consumo eléctrico.

## Descripción

El proyecto consiste en utilizar el dataset de **Open Power System Data (OPSD)**, específicamente las series de:

- Generación de energía solar.
- Consumo (carga) eléctrica.

A partir de estos datos, se simulará el comportamiento de un sistema energético autosustentable a pequeña escala.

## Funcionamiento del simulador

El modelo utilizará un **paso de tiempo fijo de 1 hora (Δt = 1 h)** y ejecutará la siguiente lógica en cada intervalo:

### 1. Entrada

Se obtienen los datos históricos de una región geográfica determinada:

- Generación solar (oferta de energía).
- Demanda o carga eléctrica (consumo).

### 2. Procesamiento

Para cada instante de tiempo se calcula el balance energético:

```text
Balance = Generación − Demanda
```

### 3. Estado del sistema

Se actualiza el nivel de carga de una batería virtual:

- **Si el balance es positivo:**
  - El excedente de energía se almacena en la batería (hasta alcanzar su capacidad máxima).

- **Si el balance es negativo:**
  - El déficit se cubre utilizando la energía almacenada en la batería.
  - Si la batería no posee suficiente energía, el sistema registra un faltante.

### 4. Salida

El simulador generará distintas métricas de desempeño, por ejemplo:

- Horas de autosuficiencia energética.
- Energía excedente desperdiciada.
- Momentos críticos de falta de energía.
- Nivel de carga de la batería a lo largo del tiempo.
- Energía tomada de la red eléctrica (si se considera una conexión a la red).

## Utilidad

Esta herramienta permitirá:

- Comprender la intermitencia de las energías renovables.
- Analizar el comportamiento de un sistema fotovoltaico bajo condiciones reales.
- Dimensionar la capacidad óptima de una batería para lograr la autosuficiencia energética.
- Evaluar distintos escenarios de generación y consumo utilizando datos meteorológicos e históricos reales.

## Posible extensión: análisis económico

Como mejora al proyecto, se podría incorporar un módulo de evaluación económica que considere:

- Costo de instalación de los paneles solares.
- Costo de adquisición de las baterías.
- Costo de la electricidad suministrada por la red.
- Costos de mantenimiento del sistema.

Con esta información sería posible calcular indicadores como:

- Inversión inicial.
- Ahorro anual generado.
- Tiempo de amortización (payback).
- Retorno de la inversión (ROI).
- Comparación entre distintos tamaños de baterías y sistemas fotovoltaicos para determinar la alternativa más rentable.