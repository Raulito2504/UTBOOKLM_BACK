# Flujo de Trabajo con Git y Estrategia de Branching

Para el control de versiones de **UTBookLM** se utiliza la estrategia de branching **GitFlow**, ya que se adapta bien a proyectos académicos desarrollados por módulos y tiene entregas parciales a lo largo del cuatrimestre.

## Ramas Principales

GitFlow define dos ramas principales:

* **`main`**: Contiene únicamente versiones estables del sistema, listas para ser entregadas o desplegadas.
* **`develop`**: Funciona como rama de integración continua; aquí se van uniendo todas las funcionalidades nuevas antes de preparar una *release*.

---

## Ramas de Trabajo Específicas

A partir de la rama `develop` se crean bifurcaciones específicas según el propósito del trabajo:

### 1. `feature/` (Ramas de funcionalidad)
* **Ejemplos:** `feature/auth`, `feature/documents-upload`, `feature/rag-chat`.
* **Flujo:** Cada funcionalidad se implementa y prueba de forma aislada. Cuando está completamente lista y verificada, se integra nuevamente en `develop` mediante un (PR).

### 2. `release/` (Ramas de preparación de versión)
* **Ejemplos:** `release/0.1.0`.
* **Flujo:** Se crearan cuando se desea congelar el código de una versión para realizar pruebas finales y correcciones menores de errores. Al finalizar la validación, se fusionan tanto en `main` (creando un tag de versión correspondiente) como en `develop` para mantener la sincronización.

### 3. `hotfix/` (Ramas de corrección urgente)
* **Ejemplos:** `hotfix/fix-rag-crash`.
* **Flujo:** Nacen directamente desde `main` cuando se detecta un fallo crítico en un entorno de producción (una versión ya liberada). Una vez solucionado el problema, los cambios se fusionan inmediatamente tanto en `main` como en `develop`.

---

## Resumen de Reglas de Branching

* **Prohibido trabajar directamente en `main`:** Ningún desarrollador debe realizar commits directos sobre esta rama.
* **Origen de las funcionalidades:** Toda nueva característica debe desarrollarse estrictamente en una rama `feature/` creada a partir de `develop`.
* **Estabilización de entregas:** Cuando un conjunto de *features* esté listo para una entrega parcial o final, se debe abrir una rama `release/*` desde `develop` con el fin de estabilizar el sistema.
* **Gestión de crisis:** Si ocurre un error crítico en producción, se abre un `hotfix/*` desde `main` y, tras solucionarlo, el código corregido debe integrarse de forma obligatoria en `main` y en `develop`.
