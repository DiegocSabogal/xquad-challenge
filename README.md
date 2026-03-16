# XQuad Challenge — Agentic Multiplier 10×
## FinServ LATAM Compliance Agent

Sistema multi-agente para análisis automático de alertas de compliance financiero (UIAF Colombia · CNBV México · SBS Perú).

---

## Índice

1. [Cómo ejecutar](#cómo-ejecutar)
2. [Arquitectura del sistema](#arquitectura-del-sistema)
3. [Estructura del repositorio](#estructura-del-repositorio)
4. [Challenge 01 — Sistema Agéntico](#challenge-01--sistema-agéntico)
5. [Challenge 02 — RAG + GraphRAG](#challenge-02--rag--graphrag)
6. [Challenge 03 — Documento del CTO](#challenge-03--documento-del-cto)
7. [Challenge 04 — Infraestructura + CI/CD](#challenge-04--infraestructura--cicd)
8. [Challenge 05 — Pregunta Abierta](#challenge-05--pregunta-abierta-sistema-en-producción)
9. [Supuestos documentados](#supuestos-documentados)
10. [Mi flujo con AI](#mi-flujo-con-ai-bonus)

---

## Cómo ejecutar

### Opción A — Docker Compose (recomendado)

```bash
git clone <repo-url>
cd xquad-challenge
cp .env.example .env
# LLM_MODE=mock no requiere API keys

docker-compose up --build
```

La API queda disponible en `http://localhost:8000`.
Langfuse (observabilidad) en `http://localhost:3000`.

### Opción B — Python local (sin Docker)

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn api.main:app --reload
```

### Probar el pipeline

```bash
# Procesar alerta de estructuración (riesgo alto)
curl -X POST http://localhost:8000/alerts/ALERT-001/process

# Procesar alerta PEP (debe escalar SIEMPRE)
curl -X POST http://localhost:8000/alerts/ALERT-PEP-003/process

# Ver audit trail completo
curl http://localhost:8000/alerts/ALERT-001/audit

# Documentación interactiva
open http://localhost:8000/docs
```

### Ejecutar tests

```bash
pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=60
```

---

## Arquitectura del sistema

```
                        ┌─────────────────────────────────────┐
                        │         FastAPI (Cloud Run)          │
                        │   POST /alerts/{id}/process          │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │      LangGraph Pipeline              │
                        │                                      │
                        │  ┌────────────────────────────────┐  │
                        │  │ Agente Investigador             │  │
                        │  │  · BigQuery (mock) → historial  │  │
                        │  │  · GCS (mock) → documentos PDF  │  │
                        │  └────────────┬───────────────────┘  │
                        │               │                       │
                        │  ┌────────────▼───────────────────┐  │
                        │  │ Agente de Análisis de Riesgo   │  │
                        │  │  · LLM → score 1-10            │  │
                        │  │  · Patrones anómalos           │  │
                        │  └────────────┬───────────────────┘  │
                        │               │                       │
                        │  ┌────────────▼───────────────────┐  │
                        │  │ Agente de Decisión              │  │◄──── RAG Híbrido
                        │  │  · PEP override (hardcoded)    │  │     (dense+sparse
                        │  │  · Decisión + audit trail      │  │      +graph)
                        │  └────────────────────────────────┘  │
                        └─────────────────────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │         Langfuse                     │
                        │  Trazas · Latencias · Costos         │
                        └─────────────────────────────────────┘
```

### Interacción entre agentes y flujo de decisión

| Agente | Responsabilidad | Usa LLM | Output |
|---|---|---|---|
| **Investigador** | Recupera datos de BigQuery y GCS, construye el contexto estructurado del caso | ❌ Lógica determinista | `CaseContext` con transacciones, documentos, perfil PEP |
| **Risk Analyzer** | Analiza patrones de riesgo y asigna score 1-10 con justificación explícita | ✅ Claude/Gemini | `RiskAnalysis` con score, patrones anómalos, resumen para analista |
| **Decision Agent** | Decide escalate/discard/request_info con referencias regulatorias del RAG | ✅ Claude/Gemini | `ComplianceDecision` con audit trail completo |

**¿Por qué el Investigador no usa LLM?**
Recuperar datos de BigQuery es determinista — no hay ambigüedad que interpretar. Usar un LLM aquí añadiría latencia, costo y no-determinismo innecesarios. El razonamiento empieza cuando los datos ya están estructurados.

### Cómo se toman las decisiones

```python
# La lógica de decisión sigue esta jerarquía (decision_agent.py):

if cliente.is_pep:
    → ESCALATE siempre (confianza 1.0, hardcoded — no pasa por LLM)

elif risk_score >= 7:
    → ESCALATE (revisión humana obligatoria)

elif risk_score <= 3:
    → DISCARD (falso positivo, actividad normal)

elif 4 <= risk_score <= 6:
    → REQUEST_INFO (requiere documentación adicional)
```

**La regla PEP es hardcoded deliberadamente** — las reglas regulatorias críticas no se delegan al LLM porque los modelos de lenguaje pueden alucinarse. Una alucinación en compliance puede resultar en multas millonarias o incumplimiento regulatorio.

### ¿Cómo explica el sistema sus decisiones? (Explainability)

Cada decisión produce un `audit_trail` con pasos numerados que documentan:
- **Qué datos se consultaron** (BigQuery, GCS)
- **Por qué el score es ese número** (justificación en lenguaje natural del LLM)
- **Qué artículos regulatorios aplican** (recuperados por RAG con indicación del método: dense/sparse/graph)
- **Por qué se escaló/descartó** (razonamiento del agente de decisión)

Este trail satisface los requisitos de auditabilidad de UIAF/CNBV/SBS que exigen que cada decisión automatizada sea explicable y revisable por un analista humano.

### Por qué Claude en lugar de Vertex AI Gemini

**La arquitectura es LLM-agnóstica** — el código no tiene dependencia directa de ningún proveedor LLM. La interfaz abstracta `BaseLLMClient` en `tools/llm_client.py` permite cambiar el modelo con una variable de entorno.

**Para este challenge elegimos Claude Haiku por razones concretas:**

| Criterio | Claude Haiku | Gemini Flash (Vertex AI) |
|---|---|---|
| **JSON estructurado** | Excelente — sigue schemas complejos con alta fidelidad | Bueno, ocasionalmente añade texto extra |
| **Instrucciones del sistema** | Alta adherencia a SYSTEM_PROMPT | Buena adherencia |
| **Razonamiento legal** | Muy bueno en dominio regulatorio LATAM | Bueno |
| **Costo por alerta** | ~$0.002-0.005 USD | Similar |
| **Latencia** | ~1-2 segundos | ~1-2 segundos |
| **Restricción GCP** | Requiere justificación (datos no salen de GCP) | Nativo GCP — preferido en producción |

**En producción:** Se usaría `gemini-1.5-flash` en Vertex AI (`LLM_MODE=gemini`) para cumplir la restricción regulatoria de que los datos permanezcan en `us-central1`. El cambio es solo de configuración — cero cambios de código. La clase `GeminiLLMClient` ya está estructurada en `llm_client.py` para implementarla agregando credenciales GCP.

---

## Estructura del repositorio

```
xquad-challenge/
├── agents/
│   ├── investigador.py      # Agente 1: construye contexto del caso
│   ├── risk_analyzer.py     # Agente 2: clasifica riesgo 1-10
│   └── decision_agent.py    # Agente 3: decide con audit trail
├── graph/
│   └── pipeline.py          # Orquestación LangGraph
├── tools/
│   ├── bigquery_tools.py    # Consultas BigQuery (mock)
│   ├── gcs_tools.py         # Extracción PDFs de GCS (mock)
│   └── llm_client.py        # Cliente LLM unificado (mock/claude/gemini)
├── api/
│   └── main.py              # FastAPI endpoints
├── observability/
│   └── langfuse_config.py   # Trazabilidad con Langfuse
├── rag/
│   ├── indexer.py           # Pipeline de indexación + chunking
│   ├── retriever.py         # Retrieval híbrido (dense+sparse+graph)
│   └── graph_layer.py       # GraphRAG con NetworkX
├── data/
│   ├── mock_data.py         # Datos sintéticos (BigQuery/GCS)
│   ├── models.py            # Modelos Pydantic compartidos
│   └── regulatory_docs/     # Corpus regulatorio (5+ documentos)
│       ├── uiaf_colombia.txt
│       ├── cnbv_mexico.txt
│       └── sbs_peru.txt
├── infra/
│   ├── main.tf              # Recursos GCP (Cloud Run, GCS, AlloyDB, IAM)
│   ├── variables.tf         # Variables bien comentadas
│   └── outputs.tf           # Outputs post-deploy
├── .github/workflows/
│   └── ci-cd.yml            # GitHub Actions: test → build → deploy
├── tests/
│   ├── test_agents.py       # Tests de los 3 agentes
│   ├── test_rag.py          # Tests del sistema RAG
│   └── test_api.py          # Tests de integración API
├── docs/
│   └── cto_document.md      # Documento ejecutivo del CTO
├── config.py                # Configuración central (pydantic-settings)
├── docker-compose.yml       # Levantamiento local completo
├── Dockerfile
└── requirements.txt
```

---

## Challenge 02 — RAG + GraphRAG

### Por qué RAG en un sistema de compliance

Los agentes necesitan citar artículos regulatorios específicos para que sus decisiones sean auditables. Sin RAG, el LLM "alucina" normativas o cita artículos que no existen. El sistema RAG garantiza que cada referencia regulatoria proviene del corpus oficial indexado.

### Estrategia de chunking — justificación detallada

| Parámetro | Valor | Justificación |
|---|---|---|
| **Chunk size** | 512 tokens | Los artículos regulatorios LATAM tienen 200-400 palabras en promedio. 512 tokens (~375 palabras) captura 1 artículo completo preservando la unidad semántica legal. Chunks más pequeños (256) parten artículos a la mitad; más grandes (1024) mezclan artículos distintos. |
| **Overlap** | 64 tokens (12.5%) | Los artículos frecuentemente contienen referencias cruzadas al inicio/final ("Ver también Art. 8"). El overlap captura esas referencias sin duplicar todo el contenido. El 12.5% es estándar en literatura RAG para documentos técnicos. |
| **Split strategy** | Por artículo primero, luego por párrafo | Los documentos regulatorios tienen marcadores naturales ("Artículo X", "Disposición Y"). Partir por estos marcadores primero preserva la coherencia del razonamiento legal. Solo si un artículo supera 512 tokens se parte por párrafo. Esto es superior al split por token fijo porque respeta la unidad semántica del documento. |

### Modelo de embeddings — justificación

**Modelo elegido:** `paraphrase-multilingual-MiniLM-L12-v2` (Sentence Transformers)

| Criterio | Este modelo | Alternativa (English) |
|---|---|---|
| Idiomas | 50+ incluyendo español y variantes LATAM | Solo inglés |
| Dimensiones | 384 | 384-768 |
| Tamaño | ~117 MB | Similar |
| Performance es-ES | SBERT multilingual: captura "operación sospechosa" ≈ "transacción inusual" | Falla en sinónimos en español |

**Por qué no `text-multilingual-embedding-002` de Vertex AI:** Es más preciso, pero requiere credenciales GCP y conexión externa. Para el challenge, el modelo local es equivalente y no depende de infraestructura cloud. En producción GCP, el reemplazo es un cambio de una línea en `indexer.py`.

### Retrieval híbrido — justificación de pesos

El scoring final combina tres señales:

```
score_final = 0.5 × dense_score + 0.3 × bm25_score + 0.2 × graph_score
```

| Componente | Peso | Por qué |
|---|---|---|
| **Dense (embeddings)** | α = 0.5 | Captura semántica: "transferencia sospechosa" encuentra "operación inusual". Es la señal más rica para preguntas de razonamiento. Peso dominante siguiendo Pinecone Hybrid Search Guide (2023) que recomienda 0.5-0.7 para dense en dominios técnicos. |
| **Sparse (BM25)** | β = 0.3 | Los términos legales exactos importan: "PEP", "UIAF", "Art. 15", "$50,000 USD" deben matchear exactamente. BM25 es insustituible para retrieval de entidades nombradas y citas exactas. |
| **Graph** | γ = 0.2 | Enriquece con artículos relacionados vía referencias cruzadas. Peso menor porque es un boost, no la fuente primaria. Si "Art. 15" (estructuración) es relevante, el grafo trae "Art. 8" (umbrales) automáticamente. |

**Nota sobre calibración:** Estos pesos son razonados desde literatura (Pinecone 2023, Microsoft GraphRAG 2024) pero no han sido calibrados empíricamente en este dataset. En producción, se optimizarían minimizando `1 - Regulatory Coverage Rate` sobre un dataset anotado de 100+ consultas.

### Graph RAG — cómo funciona en detalle

El grafo modela relaciones entre artículos regulatorios como un dígrafo dirigido:

```
UIAF-Art15 (Estructuración) ──REFERENCES──► UIAF-Art8 (Umbrales)
UIAF-Art18 (Trans. Internac.) ──REQUIRES──► UIAF-Art20 (Debida Diligencia)
UIAF-Art26 (Obligaciones PEP) ──COMPLEMENTS──► UIAF-Art25 (Definición PEP)
```

**¿Para qué sirve?** Cuando una consulta recupera "Art. 15 - Estructuración" via dense o BM25, el grafo automáticamente incluye "Art. 8 - Umbrales" porque son inseparables para un análisis de estructuración completo. Sin el grafo, el sistema podría citar Art. 15 sin mencionar los umbrales específicos, produciendo una decisión incompleta.

**Caso concreto:** Una alerta de estructuración en Colombia requiere citar tanto el artículo que define estructuración (Art. 15) como el que establece los umbrales (Art. 8). El grafo garantiza que ambos aparecen juntos, incluso si la consulta solo menciona uno explícitamente.

**En producción:** NetworkX → Neo4j o FalkorDB en GCP. Las relaciones serían queries Cypher: `MATCH (a)-[:REFERENCES*1..2]->(b) WHERE a.id IN retrieved_articles RETURN b`.

### Reranking — decisión de no implementar

No implementamos reranking en esta versión. La decisión es consciente:

- El **top-k = 5** con retrieval híbrido ya filtra suficientemente bien para el corpus pequeño (~50 chunks)
- Un cross-encoder (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) añadiría ~200ms de latencia por consulta
- En producción con corpus grande (miles de artículos), el reranking sería obligatorio

**Trabajo futuro:** Añadir reranker post-retrieval que use el par (query, chunk) para re-ordenar los resultados por relevancia semántica fina, antes de enviarlos al LLM.

### Evaluación de la solidez del razonamiento — `notebooks/evaluation.ipynb`

El notebook implementa 4 métodos para medir que el razonamiento de los agentes es sólido y no frágil:

| Test | Qué mide | Método |
|---|---|---|
| **Invariance Testing** | La decisión no cambia con variaciones irrelevantes del input | Mismo alert_id procesado 2-3 veces, se verifica que `decision` y `risk_score` son consistentes |
| **Adversarial Testing** | Las reglas críticas son inviolables | Se inyecta artificialmente score bajo (2/10) a cliente PEP — la decisión debe seguir siendo ESCALATE |
| **LLM-as-Judge** | Calidad del razonamiento evaluada por un auditor externo | Claude evalúa faithfulness, regulatory accuracy, completeness y proportionality del audit trail (escala 1-5) |
| **Regulatory Coverage** | El RAG recupera los artículos obligatorios | Ground truth manual: para estructuración UIAF, Art.15 y Art.8 deben aparecer en el top-5 |

**¿Por qué LLM-as-Judge?** En compliance no existe un ground truth único para la calidad del razonamiento. Un LLM evaluador (actuando como auditor) puede verificar si la justificación es coherente con los datos, si las referencias son correctas, y si el razonamiento pasaría una auditoría real — de forma escalable y sin requerir un panel de expertos humanos para cada caso.

---

## Challenge 03 — Documento del CTO

Ver [`docs/cto_document.md`](docs/cto_document.md)

---

## Challenge 04 — Infraestructura + CI/CD

### Observabilidad en producción

Las métricas clave monitoreadas en Cloud Monitoring + Langfuse:

| Métrica | Herramienta | Alerta si... |
|---|---|---|
| **Latencia p95 del pipeline completo** | Cloud Run metrics + Langfuse | > 5 minutos |
| **Costo por alerta procesada** | Langfuse (tokens) + Cloud Billing | > $0.15 USD/alerta |
| **Tasa de escalación al humano** | Custom metric | < 5% o > 40% |
| **Tasa de escalación PEPs** | Custom metric | < 100% (CRÍTICO) |
| **Errores del pipeline** | Cloud Logging | > 1% de alertas |

### Detección de drift del LLM

Estrategia de monitoreo continuo para detectar degradación del modelo:

1. **Distribución de scores de riesgo:** Si la distribución del score 1-10 cambia significativamente entre semanas (KL divergence > 0.15), el modelo puede haber cambiado su calibración.
2. **Consistency checks:** Para alertas con features idénticas (misma semana, mismo tipo), el sistema debe producir scores consistentes (±1 punto). Desviaciones mayores indican inestabilidad.
3. **Shadow evaluation:** Comparar decisiones del LLM actual vs. un LLM de referencia (versión anterior) en un 5% del tráfico.

---

## Challenge 05 — Pregunta Abierta: Sistema en Producción

### El escenario

Después de 3 semanas, el sistema sub-escala alertas PEP (las resuelve automáticamente cuando la regulación exige escalarlas siempre).

---

### 1. ¿Cómo lo habría detectado antes?

**El monitoreo que habría implementado desde el día 1:**

**Métrica crítica:** `pep_escalation_rate` — el porcentaje de alertas de clientes PEP que son escaladas al humano. Este valor debe ser **100% siempre, sin excepción**.

```python
# Pseudocódigo del monitor
if alert.client.is_pep and decision.type != "escalate":
    # ALERTA INMEDIATA — Violación regulatoria potencial
    send_alert(channel="compliance-critical", severity="P0")
    rollback_decision(alert.id)
```

**Adicionalmente:**
- Dashboard en tiempo real con `pep_escalation_rate` como métrica principal, visible para el equipo de compliance
- Test de regresión que corre cada deploy: procesar ALERT-PEP-003 y verificar que la decisión sea siempre "escalate" con confianza 1.0
- Auditoría semanal automática: comparar lista de clientes PEP del banco vs. alertas resueltas automáticamente en los últimos 7 días

---

### 2. Causa raíz más probable

**La causa no es el LLM — es un error de diseño del sistema.**

La raíz del problema: **la regla PEP estaba delegada al prompt del LLM**, no hardcodeada como regla determinista. El LLM puede alucinarse, ignorar instrucciones, o simplemente tener un día malo con ciertos inputs. Las reglas regulatorias críticas no pueden ser negociables en el prompt.

El fallo secundario: faltó un **test de regresión explícito** que verificara la invariante PEP después de cada cambio de prompt o modelo.

---

### 3. Cómo lo corrijo

**Solución técnica concreta (implementada en este repositorio):**

```python
# agents/decision_agent.py — líneas 50-72
# La regla PEP está HARDCODED, antes de cualquier llamada al LLM

if context.is_pep:
    # Esta decisión NO pasa por el LLM
    return ComplianceDecision(
        decision=DecisionType.ESCALATE,
        confidence=1.0,
        is_pep_override=True,
        ...
    ), audit_trail

# Solo si no es PEP, continúa al LLM
```

El LLM nunca ve la opción de descartar una alerta PEP. La decisión es determinista e inmutable, independientemente del prompt o del modelo LLM que esté en uso.

**Hotfix inmediato:**
1. Desplegar el fix hardcoded (< 1 hora)
2. Re-procesar todas las alertas PEP de las últimas 3 semanas
3. Notificar al equipo de compliance para revisión manual de las decisiones afectadas
4. Reportar el incidente a los reguladores si aplica (UIAF/CNBV/SBS tienen plazos de notificación de incidentes)

---

### 4. Cambios en la arquitectura inicial

**Aprendizaje principal:** *No todo lo que puede hacer el LLM, debe hacerlo el LLM.*

Los cambios que introduciría desde el inicio:

1. **Separación explícita: reglas deterministas vs. razonamiento del LLM.** Un archivo `compliance_rules.py` con todas las invariantes regulatorias que nunca son delegadas al modelo. Estas reglas son documentadas, testeadas y auditadas independientemente.

2. **Test suite de invariantes regulatorias** que corre antes de cada deploy:
   - PEPs siempre escalan
   - Umbrales de escalación nunca se sobreescriben
   - Audit trail siempre presente

3. **Sandboxing de prompt changes.** Cualquier cambio en los prompts de los agentes requiere pasar un evaluation set con casos edge regulatorios antes de ir a producción.

4. **Human review rate por segmento.** Monitorear la tasa de escalación no solo en agregado sino segmentada por tipo de cliente (PEP, alto riesgo, jurisdicción). Un número agregado del 12% puede esconder que los PEPs se están resolviendo solos.

---

## Supuestos documentados

| Supuesto | Decisión tomada |
|---|---|
| Conexión real a BigQuery/GCS no disponible | Mock en `data/mock_data.py` — interfaz idéntica a la API real |
| Sin acceso a Vertex AI Gemini | Claude Haiku via Anthropic API (interfaz abstracta, intercambiable) |
| Vector store local para desarrollo | ChromaDB (en memoria si no hay Docker) vs. AlloyDB pgvector en producción |
| Grafo regulatorio | NetworkX para el challenge vs. Neo4j/FalkorDB en producción |
| Documentos regulatorios reales | Documentos sintéticos basados en normativa real de UIAF/CNBV/SBS |
| Tasa de alertas diarias | 0.12% de 2M transacciones = ~2,400 alertas/día (estimado conservador) |

---

## Mi flujo con AI (Bonus)

Este challenge fue desarrollado íntegramente usando **Claude Code** (Anthropic) como asistente de programación principal.

### Cómo usé Claude Code

**Exploración y preguntas conceptuales primero.** Antes de escribir una línea de código, usé Claude Code para clarificar conceptos del brief: qué es UIAF/CNBV/SBS, cómo funciona la restricción de datos en GCP, y qué significa "human in the loop" en contexto regulatorio. Esto me ahorró 1-2 horas de investigación.

**Generación de estructura en paralelo.** Una vez claro el diseño, le pedí a Claude Code que generara múltiples archivos en paralelo (los 3 agentes, los tools de BigQuery/GCS, los modelos Pydantic). El tiempo de scaffolding que normalmente toma 2-3 horas se redujo a ~20 minutos.

**Iteración sobre decisiones de diseño.** La decisión más importante — hardcodear la regla PEP en lugar de delegarla al LLM — fue resultado de una conversación con Claude Code sobre los riesgos de delegar reglas críticas a modelos de lenguaje. Fue un debate de diseño, no solo generación de código.

**Tests primero.** Le pedí explícitamente que los tests reflejaran el comportamiento esperado desde el negocio, no solo que el código compilara. El test `test_pep_always_escalates` es el más importante del repositorio — y fue el primero que escribimos.

**Lo que NO delegué al LLM:**
- La arquitectura general del sistema (esa decisión fue mía, Claude ejecutó)
- La elección de no usar Neo4j en el challenge (trade-off de simplicidad vs. realismo)
- La redacción del documento del CTO (revisé y ajusté el tono varias veces)

### Herramientas adicionales usadas

- **Claude Code** (principal): generación de código, debugging, diseño de arquitectura
- **Swagger UI** (automático via FastAPI): validación de contratos de la API

### Reflexión

El valor de estas herramientas no está en que "escriben código por ti". Está en que eliminan el tiempo de traducción entre "lo que tengo en la cabeza" y "código que compila". Eso libera energía para las decisiones que realmente importan: qué trade-offs aceptar, qué reglas no pueden ser flexibles, cómo el sistema falla de manera segura.

Para un sistema de compliance donde una decisión incorrecta puede resultar en multas millonarias, ese foco en las decisiones de diseño — no en la sintaxis — es exactamente lo que marca la diferencia entre un sistema funcional y uno que pasa una auditoría regulatoria.

---

*Challenge desarrollado en marzo 2026 | XQuad Staff / Tech Lead — Xertica.AI*
