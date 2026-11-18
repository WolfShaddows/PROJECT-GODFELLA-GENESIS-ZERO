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

---

# 10. REVISION METODOLOGICA — VERSION 1.1

Esta revisión amplía el protocolo 1.0. La versión original se conserva
sin modificaciones como evidencia histórica.

## 10.1 Orden de ejecución

El orden de los participantes se determinará aleatoriamente antes de
cada bloque experimental.

Se conservarán:
- Semilla aleatoria.
- Orden generado.
- Fecha y hora.
- Identificador de sesión.

El orden se equilibrará entre sesiones para reducir posibles efectos
de temperatura, carga del sistema y condiciones ambientales.

## 10.2 Repetibilidad

Cada condición de interacción tendrá como mínimo tres sesiones
independientes por participante.

Una sesión independiente comenzará con un contexto conversacional nuevo,
salvo cuando se esté ejecutando expresamente una prueba de continuidad.

Los resultados individuales se conservarán. No se reemplazarán por
promedios ni se descartarán respuestas atípicas.

## 10.3 Contexto conversacional

Se establecerán dos condiciones diferenciadas:

A. CONTEXTO NUEVO
Cada prueba comienza sin historial conversacional previo.

B. CONTEXTO CONSERVADO
Se mantiene el historial de una sesión anterior de acuerdo con un
procedimiento documentado.

Se registrarán por separado:
- Contexto enviado.
- Historial conservado.
- Identificador de sesión.
- Reinicios.
- Pérdidas de contexto.
- Respuestas obtenidas.

La conservación del historial no se interpretará como modificación
de los pesos del modelo.

## 10.4 Configuración operativa de Ollama

Se registrarán los parámetros efectivos de ejecución.

Se documentarán especialmente:
- keep_alive.
- temperature.
- top_p.
- num_ctx.
- num_predict.
- Parámetros adicionales aplicables.

No se asumirá que la duración de inactividad implica permanencia
en memoria.

Durante la FASE 2 se observará el comportamiento predeterminado
de Ollama, sin imponer artificialmente la permanencia del modelo.

## 10.5 Control de condiciones ambientales

Se registrarán cuando estén disponibles:
- Temperatura del sistema.
- Uso de CPU.
- Memoria disponible.
- Procesos concurrentes.
- Estado del servicio Ollama.
- Hora de inicio y finalización.

Las limitaciones de medición se documentarán explícitamente.

## 10.6 Integridad de la revisión

La versión 1.0 permanece inalterada.

Esta versión 1.1 constituye una revisión metodológica propuesta.
Su creación no implica aprobación definitiva ni ejecución experimental.

---

# 11. ESTADO DE LA REVISION

Versión: 1.1
Estado: PROPUESTA — PENDIENTE DE CONGELAMIENTO.

Las condiciones de ejecución deberán aprobarse antes de iniciar
cualquier participante.

---

# 12. REPRODUCIBILIDAD E INTERRUPCIONES — VERSION 1.2

## 12.1 Registro de reproducibilidad

Cada ejecución deberá disponer de:

- Identificador único.
- Identificador del participante.
- Fecha y hora de inicio.
- Fecha y hora de finalización.
- Identificador de sesión.
- Semilla aleatoria, cuando corresponda.
- Configuración efectiva.
- Versión del software.
- Identificación del equipo.
- Archivos de entrada y salida.
- Hashes SHA-256 de los artefactos generados.

Los resultados originales serán inmutables una vez registrados.

Las correcciones se documentarán mediante nuevos archivos y nunca
mediante sustitución silenciosa de evidencia.

## 12.2 Política de interrupciones

Se considerará interrupción cualquier acontecimiento que altere
la continuidad prevista de una sesión.

Ejemplos:

- Reinicio del servicio Ollama.
- Cierre inesperado de un proceso.
- Suspensión o hibernación de Windows.
- Reinicio o apagado del equipo.
- Pérdida de comunicación con la API local.
- Falta de memoria o recursos.
- Error de ejecución.
- Intervención externa no prevista.

Cada incidente tendrá:

- Identificador.
- Fecha y hora.
- Participante afectado.
- Descripción.
- Estado de la sesión.
- Evidencia disponible.
- Acción tomada.

No se completarán artificialmente períodos interrumpidos.

Una sesión interrumpida no será considerada una sesión completa.
Cualquier repetición tendrá un nuevo identificador y conservará
la referencia a la sesión original.

## 12.3 Condiciones ambientales

Se registrarán cuando estén disponibles:

- Temperatura de CPU.
- Temperatura de GPU.
- Uso de CPU.
- Uso de memoria.
- Memoria disponible.
- Procesos concurrentes.
- Estado energético del equipo.

Si un sensor no está disponible, se registrará como NO DISPONIBLE.

No se inferirán temperaturas a partir del uso de CPU ni de otros
indicadores indirectos.

## 12.4 Reproducibilidad de resultados

Una repetición utilizará las mismas condiciones documentadas
que la ejecución original.

Se distinguirán:

- Repetición exacta de configuración.
- Repetición con nueva semilla.
- Repetición con contexto nuevo.
- Repetición con contexto conservado.

Las diferencias se documentarán, no se ocultarán.

La reproducibilidad de una respuesta textual no se presumirá,
incluso cuando se utilice una misma semilla.

## 12.5 Política de evidencia

Los registros originales se conservarán en su ubicación de origen.

Los análisis derivados se almacenarán por separado.

Toda transformación de datos deberá documentar:

- Archivo de entrada.
- Procedimiento aplicado.
- Archivo de salida.
- Fecha de procesamiento.
- Hash de los archivos relevantes.

## 12.6 Conservación de versiones

Las versiones 1.0, 1.1 y 1.2 serán preservadas individualmente.

Ninguna revisión posterior modificará retroactivamente los documentos
anteriores.

---

# 13. ESTADO DE LA REVISION

Versión: 1.2
Estado: PROPUESTA FINAL — PENDIENTE DE APROBACIÓN Y CONGELAMIENTO.

La creación de esta revisión no implica que las pruebas hayan comenzado.
