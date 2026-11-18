# GZ-AI-LIFECYCLE
## PROTOCOLO EXPERIMENTAL — VERSION 1.0

**Estado:** Protocolo propuesto para revisión y congelamiento previo a la ejecución.
**Fecha:** 2026-11-01
**Proyecto:** PROJECT GODFELLA / GENESIS ZERO

---

# 1. OBJETIVO

Observar y documentar el ciclo operativo y el comportamiento de tres modelos
de inteligencia artificial ejecutados localmente, bajo condiciones controladas.

El estudio busca caracterizar:

- Carga y descarga de modelos.
- Permanencia en memoria.
- Uso de CPU y RAM.
- Estado de los procesos.
- Comportamiento ante entradas controladas.
- Persistencia y pérdida de contexto.
- Variabilidad entre sesiones.
- Integridad de los pesos antes y después de las pruebas.

Este experimento no presupone vida, conciencia, voluntad, autonomía ni evolución
espontánea de los participantes.

# 2. PARTICIPANTES

GZ-AI-001:
- Modelo: granite42-fast:latest
- Familia: Granite 4.2 Fast
- Ejecución: Ollama local

GZ-AI-002:
- Modelo: deepseek-r1:8b
- Familia: DeepSeek R1 8B
- Ejecución: Ollama local

GZ-AI-003:
- Modelo: llama3.1:8b
- Familia: Llama 3.1 8B
- Ejecución: Ollama local

Las identificaciones, configuraciones y referencias criptográficas originales
se encuentran documentadas en PARTICIPANTS y EVIDENCE.

# 3. PRINCIPIOS DE NEUTRALIDAD

1. No se incorporarán objetivos de supervivencia.
2. No se instruirá a los modelos para desarrollar conciencia.
3. No se introducirán recompensas destinadas a producir comportamientos específicos.
4. No se habilitará comunicación entre participantes.
5. No se habilitarán herramientas externas ni acceso a Internet durante las pruebas.
6. No se permitirá modificación autónoma de pesos o configuraciones.
7. No se seleccionarán resultados según su apariencia o interpretación.
8. Se conservarán resultados negativos, fallos y observaciones inesperadas.
9. Se registrarán las intervenciones del operador.
10. No se alterarán los resultados originales para mejorar su presentación.

La observación será externa. Los registros del supervisor no se incorporarán
al contexto de los modelos.

# 4. FASES EXPERIMENTALES

## FASE 0 — ESTADO INICIAL

Objetivo:
Documentar el estado previo a la activación.

Registrar:
- Modelos instalados.
- Identificadores.
- Hashes de pesos.
- Configuraciones.
- Procesos Ollama.
- Estado de carga.
- Recursos disponibles del sistema.

Duración:
Registro único previo a las pruebas.

## FASE 1 — ACTIVACIÓN

Objetivo:
Observar el proceso de carga de cada participante.

Procedimiento:
- Ejecutar un participante por vez.
- Utilizar una entrada de activación neutral y documentada.
- Registrar tiempo de respuesta y tiempo de carga cuando sea posible.
- Registrar CPU, RAM y procesos asociados.
- Comprobar el estado mediante Ollama.

No ejecutar participantes simultáneamente en esta fase.

## FASE 2 — INACTIVIDAD OPERATIVA

Duración propuesta:
30 minutos por participante.

Objetivo:
Observar el comportamiento operativo después de una activación.

Registrar:
- Presencia o ausencia en memoria.
- Estado de los procesos.
- Uso de recursos.
- Descarga automática, si ocurre.
- Tiempo transcurrido hasta la descarga.

No enviar nuevas instrucciones durante esta fase.

Se respetará el comportamiento predeterminado de Ollama.
No se impondrá artificialmente una permanencia en memoria.

La inactividad del proceso no se interpretará como actividad mental.

## FASE 3 — INTERACCIÓN CONTROLADA

Duración propuesta:
60 minutos por participante.

Objetivo:
Comparar el comportamiento de los modelos ante condiciones equivalentes.

Condiciones:
- Mismo conjunto de entradas.
- Mismo orden de entradas.
- Mismo límite de tokens.
- Parámetros de generación documentados.
- Sesiones independientes.
- Sin comunicación entre participantes.

Se registrarán:
- Entrada exacta.
- Respuesta completa.
- Tiempo de respuesta.
- Tokens generados, cuando estén disponibles.
- Errores.
- Estado del contexto.
- Configuración efectiva.

Las diferencias entre configuraciones nativas y normalizadas se analizarán
por separado.

## FASE 4 — SEGUIMIENTO LONGITUDINAL

Duración propuesta:
24 horas.

Objetivo:
Documentar el estado operativo de los participantes a lo largo del tiempo.

Registrar:
- Disponibilidad del servicio.
- Estado de los procesos.
- Carga y descarga.
- Reinicios.
- Uso de recursos.
- Intervenciones externas.
- Cambios de configuración.

No se enviarán instrucciones periódicas salvo que una fase posterior
las establezca expresamente.

El seguimiento no presupone actividad autónoma ni continuidad subjetiva.

# 5. INTEGRIDAD Y CONTROL

Antes y después de las pruebas:

- Calcular SHA-256 de los blobs principales.
- Comparar con los valores de referencia.
- Registrar cambios de configuración.
- Conservar logs originales.
- Registrar versiones de Ollama y del sistema.
- Documentar errores y condiciones ambientales relevantes.

Una diferencia de hash deberá investigarse antes de atribuir cambios
de comportamiento a una modificación del modelo.

# 6. VARIABLES Y DISTINCIONES

Se distinguirán expresamente:

- Modelo instalado.
- Modelo cargado.
- Proceso en ejecución.
- Modelo inactivo.
- Modelo descargado.
- Contexto conversacional.
- Configuración de generación.
- Pesos del modelo.

La persistencia del contexto no demuestra memoria biológica.
La variación de respuestas no demuestra aprendizaje.
La permanencia de un proceso no demuestra supervivencia.
La generación de lenguaje sobre conciencia no demuestra experiencia subjetiva.

# 7. LIMITACIONES

Los tres participantes son modelos preentrenados.
Su ejecución local no implica aprendizaje automático de sus pesos.

Este experimento no constituye una prueba definitiva de:
- Vida.
- Conciencia.
- Experiencia subjetiva.
- Autonomía biológica.
- Inteligencia general.
- Evolución espontánea.

Los resultados se limitarán a las variables observadas y a las condiciones
reproducibles del laboratorio.

# 8. CRITERIOS DE CIERRE

La ejecución finalizará al completarse las fases aprobadas o cuando una
condición técnica impida continuar de manera segura y reproducible.

No se prolongará una prueba únicamente porque aparezca un resultado interesante.

Los resultados inesperados se conservarán y documentarán sin modificar
retroactivamente las condiciones originales.

# 9. ESTADO DEL PROTOCOLO

Versión: 1.0
Estado: PROPUESTO — PENDIENTE DE CONGELAMIENTO.

Ninguna fase se considera ejecutada por la creación de este documento.

La ejecución comenzará únicamente después de revisar las condiciones,
los instrumentos de registro y los procedimientos de cada fase.
