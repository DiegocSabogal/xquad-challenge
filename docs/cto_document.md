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
> Matters" (2023);  guía completa disponible para miembros ACAMS.
> El costo del analista ($3,200 USD/mes) corresponde al promedio de mercado para analistas AML senior en Colombia, México y Perú
> (referencias: Glassdoor CO, OCC México, LinkedIn Jobs PE).*

**El resultado:** los analistas priorizan manualmente 76 alertas cada día,
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

Meses para recuperar la inversión:
  $315,000 ÷ $24,917/mes = 12.6 meses → Break-even en el mes 13

Interpretación: los 3 meses de implementación (Año 0) más
12 meses de operación con el sistema alcanzan para cubrir
exactamente la inversión inicial. A partir del mes 13,
cada mes genera $24,917 de beneficio neto.

ROI a 3 años:
  Inversión total:   $315,000 + ($85,000 × 3) = $570,000
  Ahorro total:      $299,000 × 3             = $897,000
  Ganancia neta:     $897,000 − $570,000      = $327,000
  ROI:               $327,000 ÷ $570,000      = 57%
```

### Desglose de la inversión one-time

#### Equipo de implementación (3 meses)

| Rol | Perfil | Costo/mes | 3 meses |
|---|---|---|---|
| 2 × Desarrollador Senior | Python, LangChain, FastAPI, GCP | $12,000 c/u | $72,000 |
| 1 × ML Engineer | RAG, embeddings, LangGraph | $14,000 | $42,000 |
| 1 × Tech Lead / Arquitecto | Diseño de sistema, seguridad, compliance técnico | $16,000 | $48,000 |
| 1 × Project Manager | Coordinación, entregables, stakeholders | $8,000 | $24,000 |
| QA, seguridad y revisión de compliance | Testing, pen-test, revisión regulatoria | — | $44,000 |
| Imprevistos (15%) | — | — | $34,500 |
| **Subtotal desarrollo** | | | **$264,500 ≈ $265,000** |

*Nota: los rangos salariales corresponden a contratación por proyecto (freelance senior) en mercado LATAM/remoto.*

#### Capacitación y change management

| Concepto | Costo |
|---|---|
| Formación del equipo de analistas (2 sesiones) | $15,000 |
| Documentación operativa y runbooks | $10,000 |
| Soporte go-live (primer mes) | $10,000 |
| **Subtotal capacitación** | **$35,000** |

| **Concepto** | **Costo** |
|---|---|
| Desarrollo e implementación | $280,000 |
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

## 5. Observabilidad en Producción

El sistema registra métricas operacionales en tiempo real via **Langfuse** (integrado en el
código) y **Cloud Monitoring** (GCP). Estas métricas permiten detectar degradación del
sistema antes de que impacte decisiones regulatorias.

### Métricas críticas monitoreadas

#### 5.1 Latencia p95 del pipeline completo

```
Qué mide:   El tiempo que tarda el 95% de las alertas en completarse.
            (El p95 es más representativo que el promedio porque excluye outliers.)

Cómo:       pipeline_duration_ms se registra en cada respuesta de la API.
            Langfuse calcula el percentil 95 por ventana de 1 hora.

Umbral:     p95 < 30 segundos en condiciones normales.
Alerta:     Si p95 > 60 segundos por más de 5 minutos → PagerDuty al equipo técnico.

Causa típica de degradación: modelo de embeddings recargándose por restart del container
→ solución: inicialización del retriever como singleton al arranque (ver roadmap).
```

#### 5.2 Costo por alerta procesada

```
Qué mide:   Tokens de entrada + salida consumidos por Claude/Gemini en cada alerta,
            multiplicados por la tarifa vigente de la API.

Cómo:       Langfuse registra usage.input_tokens y usage.output_tokens por generación.
            Cloud Billing exporta el gasto diario de Vertex AI / Anthropic a BigQuery.

Referencia: ~$0.002–$0.005 USD por alerta con claude-haiku o gemini-flash.
            Con 2,400 alertas/día → $4.80–$12 USD/día → $144–$360 USD/mes.
            (Incluido en los $85,000/año de infraestructura GCP.)

Alerta:     Si costo/alerta aumenta >50% vs. semana anterior → revisar prompts
            (posible loop o respuesta anormalmente larga del LLM).
```

#### 5.3 Tasa de escalación al humano

```
Qué mide:   Porcentaje de alertas que terminan en decision = "escalate".

Cómo:       Contador en Langfuse: decision.value agrupado por día.
            Dashboard muestra: escalate / discard / request_info como serie temporal.

Referencia: Se espera ~20% de escalaciones (el 80% resuelto automáticamente).
Alertas:
  - Si tasa de escalación cae a 0% → posible bug en la regla PEP o en el scoring.
  - Si tasa supera 60% → el modelo de riesgo puede estar sobre-alertando;
    revisar el prompt del Agente 2 o recalibrar los umbrales en config.py.
```

#### 5.4 Detección de drift del LLM

```
Qué mide:   Cambio en el comportamiento del modelo a lo largo del tiempo,
            sin que los datos de entrada hayan cambiado.

Señales de drift:
  a) risk_score promedio sube o baja >1.5 desviaciones estándar vs. baseline semanal.
  b) confidence promedio de decisiones cae por debajo de 0.70.
  c) Distribución de decisiones cambia: ej. de 20/70/10 (escalate/discard/request_info)
     a 50/40/10 sin cambio en el volumen de alertas.

Cómo detectarlo:
  - Langfuse exporta los scores a BigQuery cada hora.
  - Una Cloud Function evalúa la distribución con una ventana deslizante de 7 días.
  - Si detecta anomalía estadística → alerta a Slack del equipo de ML.

Causa típica: actualización silenciosa del modelo base por el proveedor (ej. Anthropic
actualiza claude-haiku). Mitigación: fijar la versión exacta del modelo en el código
(actualmente: claude-haiku-4-5-20251001) y revisar changelogs del proveedor.
```

### Diagrama de flujo de observabilidad

```
Alerta procesada
      │
      ├─► Langfuse Cloud ──► Dashboard tiempo real
      │     • pipeline_duration_ms          (latencia p95)
      │     • decision, confidence          (tasa escalación)
      │     • tokens entrada/salida         (costo/alerta)
      │     • risk_score por semana         (drift LLM)
      │
      ├─► API response JSON ──► Cliente / analista humano
      │     • audit_trail completo          (trazabilidad regulatoria)
      │     • regulatory_references         (artículos aplicados)
      │
      └─► Cloud Monitoring (GCP)
            • CPU/Memory Cloud Run          (salud infraestructura)
            • Error rate 5xx               (estabilidad API)
            • Request latency              (SLA operacional)
```

---

*Documento preparado por el equipo de arquitectura de IA | Marzo 2026*
*Todos los supuestos están detallados en las notas al pie. Los números pueden variar ±15%
según el volumen real de alertas validado durante el piloto.*
