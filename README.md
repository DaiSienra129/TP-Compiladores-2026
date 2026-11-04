# Regex2AFD — Compilador de Expresiones Regulares a Código C Optimizado

**Materia:** Compiladores (2026) — Universidad Gastón Dachary  
**Proyecto:** Trabajo Práctico Integrador  

---

## 👥 Integrantes del Equipo
* **Daiana Micaela Sienra**
* **Giuliano Hillebrand**
* **Martín Gonzalez**

---
## 🌍 Entorno de Aplicación y Contexto del Compilador

### ¿Dónde se aplica este compilador?
**Regex2AFD** está diseñado para ser utilizado en **sistemas embebidos, dispositivos IoT y microcontroladores** con recursos de hardware (RAM y memoria Flash) estrictamente limitados.

### Solución propuesta
**Regex2AFD** funciona como un compilador de dominio específico que toma una expresión regular durante la etapa de compilación en la PC (Host) y genera una función en código C estándar (Target) altamente optimizada:
* **Sin memoria dinámica:** 0 asignaciones en tiempo de ejecución (verificable con Valgrind).
* **Sin dependencias externas:** Código C99 autónomo sin incluir librerías pesadas.
* **Tiempo de ejecución lineal $O(N)$:** Garantiza respuesta determinista y predecible realizando un solo acceso a la tabla de transiciones por cada carácter.

---

## ⚙️ Arquitectura del Pipeline

El compilador realiza 6 transformaciones consecutivas sobre el patrón de entrada:

```text
Expresión Regular (.regex) 
   └─► 1. Árbol de Sintaxis Abstracta (AST)
   └─► 2. AFND (Construcción de Thompson)
   └─► 3. AFD (Construcción de Subconjuntos + Agrupamiento en Clases)
   └─► 4. AFD Mínimo (Algoritmo de Hopcroft)
   ├─► 5. Código C (Función de validación C99)
   └─► 6. Diagrama de Autómata (Graphviz .dot / PNG)
```

---

## 💻 Entorno de Desarrollo y Requisitos

### Host (Máquina de desarrollo)
* **Lenguaje principal:** Python 3.12+ (Pipeline de análisis léxico, sintáctico y síntesis)

---

## 🧪 Pruebas

Las pruebas usan `pytest`, gestionado con [uv](https://docs.astral.sh/uv/):

```bash
make test                              # uv run pytest
make test PYTEST="python3 -m pytest"   # sin uv, con pytest instalado
```

Los errores conocidos están marcados como `xfail` estrictos: al corregir uno, quitar su marca.
