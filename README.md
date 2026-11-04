# Regex2AFD: Compilador de Expresiones Regulares a Código C Optimizado

**Regex2AFD** es un compilador de dominio específico (DSL) desarrollado para la asignatura **Compiladores** de la **Universidad Gastón Dachary (UGD)**.

El objetivo principal del proyecto es transformar expresiones regulares en Autómatas Finitos Deterministas (AFD) mínimos y emitiros como funciones independientes en lenguaje C99 estándar, orientadas a entornos de recursos limitados (sistemas embebidos e IoT).

---

## 🚀 Características Principales

- **Sin Memoria Dinámica**: El código C generado no utiliza `malloc` ni liberaciones de memoria ($0$ bytes dinámicos).
- **Sin Dependencias Externas**: Emite funciones en C estándar listas para integrarse en microcontroladores.
- **Tiempo de Ejecución Lineal $O(n)$**: La validación recorre la cadena realizando un único acceso a matriz por carácter.
- **Minimización de Hopcroft**: Reduce al mínimo el número de estados en tiempo de compilación para generar binarios livianos.
- **Clases de Equivalencia ASCII**: Agrupa caracteres con transiciones equivalentes para comprimir la tabla de estados.

---

## 🏗️ Arquitectura del Pipeline

```text
  [ Entrada: .regex ]
           │
           ▼
  ┌─────────────────┐
  │ 1. Frontend     │ ──► Lexer + Parser (Árbol AST)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ 2. Motor        │ ──► Thompson (AST -> AFND) -> Subconjuntos (AFND -> AFD)
  └────────┬────────┘     -> Minimización de Hopcroft (AFD Mínimo)
           │
           ▼
  ┌─────────────────┐
  │ 3. Backend C    │ ──► Generación de tablas estáticas (validador.c)
  └─────────────────┘