# Propuesta Ejecutiva: Sistema de IA para Compliance
## FinServ LATAM — Presentación al Board

---

## 1. El Problema en Números

Hoy FinServ paga **$1.5M al año** por un equipo de compliance que, por limitaciones físicas,
solo puede revisar el **3% de las alertas que genera su propio sistema.**

No es un problema de personas — es un problema de escala.

**Situación actual:** El equipo de 40 analistas tarda en promedio **4.2 horas** por alerta
(dato del brief). Con ~2 millones de transacciones diarias, el modelo XGBoost genera
aproximadamente **2,400 alertas/día.**

| Concepto | Dato | Supuesto / Fuente |
|---|---|---|
| Transacciones diarias | ~2,000,000 | Dato del brief |
| Alertas diarias (tasa 0.12%) | ~2,400 | Ver nota¹ |
| Horas por alerta | 4.2 h | Dato del brief |
| Capacidad real del equipo (40 analistas × 8h ÷ 4.2h) | **76 alertas/día** | Cálculo directo |
| Alertas que quedan sin revisar cada día | **2,324 (97%)** | 2,400 − 76 |
| Costo equipo actual | **$1,536,000/año** | 40 × $3,200 × 12 |

> ¹ *Tasa de alerta del 0.12%: alineada con el rango de industria de 0.05%–0.30% para banca
> retail en mercados emergentes con modelos de detección automatizada (XGBoost/ML).
> Fuente de referencia: ACAMS, "Best Practice Guide: Transaction Monitoring – Effectiveness
> Matters" (2023) — ;
> guía completa disponible para miembros ACAMS. El costo del analista ($3,200 USD/mes)
> corresponde al promedio de mercado para analistas AML senior en Colombia, México y Perú
> (referencias: Glassdoor CO, OCC México, LinkedIn Jobs PE — 2024).*

**El resultado:** los analistas priorizan manualmente qué 76 alertas atender cada día,
descartando implícitamente las 2,324 restantes. No por falta de voluntad, sino porque
es matemáticamente imposible hacer más con el equipo actual.

---

## 2. La Solución Propuesta

Implementamos un **asistente inteligente de compliance** que actúa como un analista
senior disponible 24/7, procesando cada alerta en segundos en lugar de horas.

**¿Cómo funciona?** (sin tecnicismos)

```
Alerta nueva
    ↓
[Agente 1] Recopila el historial de 90 días del cliente y sus documentos KYC
    ↓
[Agente 2] Evalúa el riesgo (1-10) comparando patrones históricos y señales del modelo
    ↓
[Agente 3] Consulta automáticamente la regulación aplicable (UIAF/CNBV/SBS)
           y toma una decisión con explicación completa
    ↓
• Score ≤ 3  → Descarte automático con justificación guardada para auditorías
• Score 4-6  → Solicita información adicional sin intervención humana
• Score ≥ 7  → El analista recibe un expediente completo, no una alerta vacía
• Cliente PEP → Escala siempre (regla regulatoria, no delegada a la IA)
```

**Lo que NO cambia:** el analista humano sigue siendo el decisor final en casos complejos.
El sistema lo libera del trabajo repetitivo para que se enfoque en los casos que
realmente importan.

**Infraestructura:** todo corre dentro de Google Cloud (región us-central1), cumpliendo
las restricciones de datos de UIAF, CNBV y SBS. Ningún dato de cliente sale de la nube
de FinServ.

---

## 3. ROI Proyectado

### Con el sistema: 30 analistas cubren el 100% del volumen

El sistema resuelve automáticamente el 80% de las alertas (descartes y solicitudes de
información). El 20% restante llega al analista con toda la investigación hecha,
reduciendo el tiempo de intervención humana de 4.2 horas a ~30 minutos por caso.

```
2,400 alertas/día × 20% que requieren analista = 480 casos/día
480 casos × 0.5 horas = 240 horas necesarias/día
240 horas ÷ 8 horas por analista = 30 analistas
```

*Supuesto: el 80/20 y los 30 minutos son proyecciones basadas en el diseño del sistema.
Se validarán con datos reales durante el piloto.*

### Flujo de caja

| Concepto | Año 0 (implementación) | Año 1 | Año 2 | Año 3 |
|---|---|---|---|---|
| Costo equipo (30 analistas) | — | −$1,152,000 | −$1,152,000 | −$1,152,000 |
| Infraestructura GCP | — | −$85,000 | −$85,000 | −$85,000 |
| Inversión one-time (desarrollo + capacitación) | −$315,000 | — | — | — |
| **Costo total** | **−$315,000** | **−$1,237,000** | **−$1,237,000** | **−$1,237,000** |
| Costo sin sistema (40 analistas) | — | −$1,536,000 | −$1,536,000 | −$1,536,000 |
| **Ahorro anual neto** | — | **+$299,000** | **+$299,000** | **+$299,000** |

### Break-even y ROI

```
Inversión one-time:         $315,000
Ahorro mensual neto:    $299,000 ÷ 12 = $24,917/mes

Break-even: mes 13 (primer mes del segundo año operativo)

ROI a 3 años:
  Inversión total:   $315,000 + ($85,000 × 3) = $570,000
  Ahorro total:      $299,000 × 3             = $897,000
  Ganancia neta:     $897,000 − $570,000      = $327,000
  ROI:               $327,000 ÷ $570,000      = 57%
```

### Desglose de la inversión one-time

| Concepto | Costo |
|---|---|
| Desarrollo e implementación (3 meses) | $280,000 |
| Capacitación y change management | $35,000 |
| **Total inversión one-time** | **$315,000** |

### Desglose infraestructura GCP (anual)

| Concepto | Costo/mes | Costo/año |
|---|---|---|
| Cloud Run / Vertex AI (inferencia) | $3,000 | $36,000 |
| BigQuery (consultas transaccionales) | $1,500 | $18,000 |
| Cloud Storage (documentos KYC) | $500 | $6,000 |
| Observabilidad y monitoreo (Langfuse) | $2,000 | $24,000 |
| **Total GCP** | **$7,000** | **$85,000** |

---

## 4. El Riesgo Principal y su Mitigación

**Riesgo:** El sistema podría clasificar incorrectamente alertas de personas políticamente
expuestas (PEPs) — funcionarios de gobierno —, que por regulación **siempre** deben ser
revisadas por un humano.

**¿Por qué es crítico?** Una sola decisión automática sobre un PEP sin revisión humana
puede resultar en multas significativas y suspensión de licencias en Colombia, México o Perú.

**Mitigación concreta (ya implementada en la arquitectura):**
- La regla "PEP → escalar siempre" está **hardcoded** en el código, **no delegada a la IA**.
  Es una regla determinista que el sistema de IA no puede sobreescribir bajo ninguna circunstancia.
- Monitoreo continuo: el dashboard de operaciones muestra la tasa de escalación de PEPs
  en tiempo real. Si cae a 0%, genera alerta inmediata.
- Auditoría automática: cada decisión genera un expediente completo con el razonamiento
  paso a paso, listo para presentar a los reguladores (UIAF, CNBV, SBS).

---

*Documento preparado por el equipo de arquitectura de IA | Marzo 2026*
*Todos los supuestos están detallados en las notas al pie. Los números pueden variar ±15%
según el volumen real de alertas validado durante el piloto.*
