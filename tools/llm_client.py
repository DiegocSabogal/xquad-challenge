"""
Cliente LLM con interfaz unificada.

Justificacion de usar Claude en lugar de Vertex AI Gemini:
- Arquitectura diseñada para ser LLM-agnóstica (interfaz abstracta)
- En producción GCP: Vertex AI Gemini (mantiene datos en us-central1)
- En este challenge: Claude (Anthropic) via API, o modo mock sin API key
- El cambio es solo de configuracion (LLM_MODE en .env)

Razonamiento técnico para preferir Claude en el challenge:
Claude Sonnet/Haiku tiene mejor performance en razonamiento estructurado
y generación de JSON válido, lo que es crítico para audit trails.
En producción, Gemini Pro en Vertex AI sería la opción por compliance GCP.
"""
import json
from abc import ABC, abstractmethod
from typing import Any

from config import settings


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str:
        pass

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """Llama al LLM y parsea la respuesta como JSON."""
        raw = self.complete(system_prompt, user_message)
        # Extraer JSON si viene envuelto en ```json ... ```
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)


class MockLLMClient(BaseLLMClient):
    """
    LLM mock para desarrollo local sin API keys.
    Retorna respuestas realistas pre-definidas segun el tipo de prompt.
    """

    def complete(self, system_prompt: str, user_message: str) -> str:
        # Routing por marcadores únicos de cada prompt (orden importa)
        # Decision agent tiene "REGLAS OBLIGATORIAS" — no aparece en otros prompts
        # Risk agent tiene "risk_score: integer" — no aparece en el de decisión
        prompt_lower = system_prompt.lower()
        if "reglas obligatorias" in prompt_lower or "escalate" in prompt_lower:
            return self._mock_decision_response(user_message)
        elif "riesgo" in prompt_lower or "risk_score: integer" in prompt_lower:
            return self._mock_risk_response(user_message)
        else:
            return self._mock_generic_response(user_message)

    def _mock_risk_response(self, context: str) -> str:
        # Buscar "ES PEP: True" exacto para no matchear "ES PEP: False"
        is_pep = "ES PEP: True" in context
        is_high_risk = "SHELL-CORP" in context or "48500" in context
        score = 9 if (is_pep or is_high_risk) else 4

        return json.dumps({
            "risk_score": score,
            "risk_justification": (
                "Dos transferencias internacionales consecutivas por debajo del umbral "
                "de reporte ($50,000 USD) hacia una entidad en Panamá sin actividad "
                "comercial verificada. Patrón consistente con estructuración (smurfing)."
                if is_high_risk else
                "Patrón transaccional dentro de parámetros normales para el perfil "
                "del cliente. Variaciones menores sin indicadores de riesgo elevado."
            ),
            "anomalous_patterns": [
                {
                    "pattern_type": "structuring",
                    "description": "Dos transacciones de $48,500 y $49,800 USD en 48 horas "
                                   "hacia la misma contraparte offshore.",
                    "severity": "high" if is_high_risk else "low"
                }
            ] if is_high_risk else [],
            "analyst_summary": (
                "ALERTA DE ALTO RIESGO: El cliente realizó dos transferencias "
                "internacionales a Panama en 48 horas. El monto acumulado ($98,300 USD) "
                "y la contraparte (SHELL-CORP-PANAMA) son indicadores críticos de "
                "posible estructuración para evasión de reportes UIAF."
                if is_high_risk else
                "Actividad transaccional del cliente dentro de perfil esperado. "
                "No se identifican patrones de riesgo significativos en el período analizado."
            )
        })

    def _mock_decision_response(self, context: str) -> str:
        # Buscar "Es PEP: True" exacto para no matchear "Es PEP: False"
        is_pep = "Es PEP: True" in context
        # El user_message usa formato "- Score: 9/10", no JSON
        is_high_risk = "Score: 9" in context or "Score: 8" in context or "Score: 10" in context

        if is_pep:
            decision = "escalate"
            confidence = 1.0
            reasoning = "Cliente identificado como PEP. Normativa SBS artículo 18 exige " \
                        "escalación obligatoria independientemente del score de riesgo."
        elif is_high_risk:
            decision = "escalate"
            confidence = 0.92
            reasoning = "Riesgo score 9/10 supera umbral de escalación (7). " \
                        "Patrón de estructuración detectado requiere revisión humana."
        else:
            decision = "discard"
            confidence = 0.78
            reasoning = "Riesgo score 4/10 por debajo del umbral de escalación. " \
                        "Sin patrones anómalos significativos. Alerta descartada."

        return json.dumps({
            "decision": decision,
            "confidence": confidence,
            "regulatory_references": [
                {
                    "article": "Artículo 15 - Circular Básica Jurídica",
                    "body": "UIAF",
                    "description": "Operaciones en efectivo o transferencias que superen "
                                   "los umbrales establecidos deben ser reportadas.",
                    "retrieved_via": "rag_dense"
                }
            ],
            "reasoning_chain": [
                {
                    "step": 1,
                    "agent": "decision_agent",
                    "action": "evaluar_pep_status",
                    "reasoning": f"Cliente {'ES' if is_pep else 'NO ES'} PEP. "
                                 f"{'Escalación obligatoria activada.' if is_pep else 'Continúa evaluación normal.'}"
                },
                {
                    "step": 2,
                    "agent": "decision_agent",
                    "action": "evaluar_risk_score",
                    "reasoning": reasoning
                }
            ],
            "is_pep_override": is_pep,
            "final_summary": (
                f"Decisión: {'ESCALAR AL HUMANO' if decision == 'escalate' else 'DESCARTAR'}. "
                f"Confianza: {confidence:.0%}. {reasoning}"
            )
        })

    def _mock_generic_response(self, context: str) -> str:
        return "Análisis completado. Sin observaciones adicionales."


class ClaudeLLMClient(BaseLLMClient):
    """
    Cliente real usando Claude (Anthropic API).
    Usado en el challenge como alternativa justificada a Vertex AI Gemini.
    """

    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = "claude-haiku-4-5-20251001"  # Costo-eficiente para compliance

    def complete(self, system_prompt: str, user_message: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text


def get_llm_client() -> BaseLLMClient:
    """Factory que retorna el cliente LLM según configuración."""
    if settings.llm_mode == "claude" and settings.anthropic_api_key:
        return ClaudeLLMClient()
    # Default: mock (no requiere API keys)
    return MockLLMClient()
