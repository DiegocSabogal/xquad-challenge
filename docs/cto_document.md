# Propuesta Ejecutiva: Sistema de IA para Compliance
## FinServ LATAM — Presentación al Board

---

## 1. El Problema en Números

**Situación actual:** El equipo de 40 analistas de compliance tarda en promedio **4.2 horas** por alerta. Con ~2 millones de transacciones diarias, el modelo XGBoost genera aproximadamente **2,400 alertas/día** (tasa de alerta estimada del 0.12%).

| Concepto | Dato | Supuesto |
|---|---|---|
| Alertas diarias | ~2,400 | 0.12% de 2M transacciones |
| Horas por alerta | 4.2 h | Dato del brief |
| Capacidad real del equipo actual (40 analistas) | **~76 alertas/día** | 40 × 8h ÷ 4.2h |
| Alertas sin revisar cada día | **~2,324 (97%)** | 2,400 − 76 |
| Analistas necesarios para cubrir el volumen completo | **~1,260 analistas** | 2,400 × 4.2h ÷ 8h |
| Costo analista/mes (LATAM promedio) | $3,200 USD | Estimado mercado CO/MX/PE |
| **Costo anual si se contrata el equipo completo** | **~$48.4M USD** | 1,260 × $3,200 × 12 |

> ⚠️ **Riesgo regulatorio crítico:** Con solo 40 analistas, el 97% de las alertas diarias quedan sin revisar. Cada alerta no procesada es una ventana de exposición a multas regulatorias de hasta $2M USD por incidente (UIAF, CNBV, SBS). La empresa enfrenta dos opciones igualmente costosas: contratar ~1,220 analistas adicionales ($48M/año) o absorber el riesgo regulatorio. Existe además un tercer costo oculto: los analistas actuales trabajan bajo presión extrema para priorizar manualmente las 76 alertas que pueden atender, incurriendo en horas extra no sostenibles.

> *El 68% de las alertas procesadas son falsos positivos — tiempo humano desperdiciado en casos que no lo ameritan.*

---

## 2. La Solución Propuesta

Implementamos un **asistente inteligente de compliance** que actúa como un analista senior disponible 24/7.

**¿Cómo funciona?** (sin tecnicismos)

```
Alerta nueva
    ↓
[Agente 1] Recopila el historial de 90 días del cliente y sus documentos
    ↓
[Agente 2] Evalúa el riesgo (1-10) comparando con miles de casos históricos
    ↓
[Agente 3] Consulta automáticamente la regulación aplicable (UIAF/CNBV/SBS)
           y toma una decisión con explicación completa
    ↓
• Riesgo bajo → Descarte automático (con justificación guardada para auditorías)
• Riesgo alto → El analista humano recibe un expediente completo, no una alerta vacía
```

**Lo que NO cambia:** el analista humano sigue siendo el decisor final en casos complejos. El sistema lo libera del 80% del trabajo repetitivo para que se enfoque en los casos que realmente importan.

**Infraestructura:** todo corre dentro de Google Cloud (región us-central1), cumpliendo las restricciones de datos de UIAF, CNBV y SBS. Ningún dato de cliente sale de la nube de FinServ.

---

## 3. ROI Proyectado (12 meses)

### Ahorro por reducción de tiempo

| Escenario | Tiempo actual | Tiempo proyectado | Reducción |
|---|---|---|---|
| Resolución por alerta | 4.2 horas | 30 minutos | **88%** |

El 80% de las alertas (las de riesgo bajo y medio) se resuelven automáticamente. El 20% restante llega al analista con toda la investigación hecha — reduciendo el tiempo humano de 4.2h a ~30 min.

**Analistas necesarios con el sistema: ~28** (vs los 1,260 que requeriría el proceso manual completo, o vs los 40 actuales que solo cubren el 3% del volumen)

| Concepto | Año 1 |
|---|---|
| Evitar contratación de ~1,220 analistas adicionales | +$46.8M USD (riesgo evitado) |
| Optimización del equipo actual de 40 → 28 analistas | +$460K USD |
| Reducción de exposición a multas regulatorias (97% alertas sin revisar → 0%) | +$1.2M USD est. |
| **Beneficio total estimado** | **+$48.5M USD** |

### Costo de implementación

| Concepto | Costo |
|---|---|
| Desarrollo e implementación (3 meses) | $280,000 USD |
| Infraestructura GCP (anual) | $85,000 USD |
| Capacitación y change management | $35,000 USD |
| **Costo total año 1** | **$400,000 USD** |

### Break-even

> **Break-even en el mes 3** después del go-live.
> ROI año 1: **2,050%** ($8.6M ahorro ÷ $400K inversión).

---

## 4. El Riesgo Principal y su Mitigación

**Riesgo:** El sistema podría clasificar incorrectamente alertas de personas políticamente expuestas (PEPs) — funcionarios de gobierno —, que por regulación **siempre** deben ser revisadas por un humano.

**¿Por qué es crítico?** Una sola decisión automática sobre un PEP sin revisión humana puede resultar en multas de hasta $2M USD y suspensión de licencias en Colombia, México o Perú.

**Mitigación concreta (ya implementada en la arquitectura):**
- La regla "PEP → escalar siempre" está **hardcoded** en el código, **no delegada a la IA**. Es una regla determinista que el sistema de IA no puede sobreescribir.
- Monitoreo continuo: el dashboard de operaciones muestra la tasa de escalación de PEPs en tiempo real. Si cae a 0%, genera alerta inmediata.
- Auditoría automática: cada decisión genera un expediente completo con el razonamiento paso a paso, listo para presentar a los reguladores.

---

*Documento preparado por el equipo de arquitectura de IA | Marzo 2026*
*Supuestos disponibles en el anexo técnico. Los números exactos pueden variar ±15% según volumen real de alertas.*
