"""
Tests para los 3 agentes del pipeline de compliance.
Usan datos mock — no requieren conexión a BigQuery, GCS ni API LLM.
"""
import pytest
from data.models import DecisionType, RegulatoryBody
from agents import investigador, risk_analyzer, decision_agent


class TestInvestigadorAgent:
    def test_run_returns_case_context(self):
        context, steps = investigador.run("ALERT-001")
        assert context.alert_id == "ALERT-001"
        assert context.client_id == "CLI-001"
        assert context.regulator == RegulatoryBody.UIAF
        assert context.transaction_count > 0

    def test_pep_client_is_flagged(self):
        context, steps = investigador.run("ALERT-PEP-003")
        assert context.is_pep is True
        assert context.pep_category is not None

    def test_audit_trail_not_empty(self):
        _, steps = investigador.run("ALERT-001")
        assert len(steps) >= 3  # Mínimo: fetch_alert, query_bigquery, extract_gcs

    def test_flagged_transactions_detected(self):
        context, _ = investigador.run("ALERT-001")
        assert len(context.flagged_transactions) > 0

    def test_invalid_alert_raises_error(self):
        with pytest.raises(ValueError, match="no encontrada"):
            investigador.run("ALERT-INEXISTENTE")


class TestRiskAnalyzerAgent:
    def setup_method(self):
        self.context, self.audit_trail = investigador.run("ALERT-001")

    def test_risk_score_in_range(self):
        analysis, _ = risk_analyzer.run(self.context, self.audit_trail)
        assert 1 <= analysis.risk_score <= 10

    def test_analysis_has_justification(self):
        analysis, _ = risk_analyzer.run(self.context, self.audit_trail)
        assert len(analysis.risk_justification) > 10

    def test_analysis_has_analyst_summary(self):
        analysis, _ = risk_analyzer.run(self.context, self.audit_trail)
        assert len(analysis.analyst_summary) > 20

    def test_high_risk_alert_scores_high(self):
        """ALERT-001 tiene transacciones de estructuración — debe tener riesgo alto."""
        analysis, _ = risk_analyzer.run(self.context, self.audit_trail)
        assert analysis.risk_score >= 7


class TestDecisionAgent:
    def setup_method(self):
        self.context, self.trail = investigador.run("ALERT-001")
        self.analysis, self.trail = risk_analyzer.run(self.context, self.trail)

    def test_decision_valid_type(self):
        decision, _ = decision_agent.run(self.context, self.analysis, self.trail)
        assert decision.decision in DecisionType

    def test_decision_has_confidence(self):
        decision, _ = decision_agent.run(self.context, self.analysis, self.trail)
        assert 0.0 <= decision.confidence <= 1.0

    def test_pep_always_escalates(self):
        """PEP debe escalar siempre, sin importar el score de riesgo."""
        pep_context, pep_trail = investigador.run("ALERT-PEP-003")
        pep_analysis, pep_trail = risk_analyzer.run(pep_context, pep_trail)
        decision, _ = decision_agent.run(pep_context, pep_analysis, pep_trail)

        assert decision.decision == DecisionType.ESCALATE
        assert decision.is_pep_override is True
        assert decision.confidence == 1.0

    def test_audit_trail_has_reasoning(self):
        decision, _ = decision_agent.run(self.context, self.analysis, self.trail)
        assert len(decision.reasoning_chain) > 0

    def test_decision_has_regulatory_references(self):
        pep_context, pep_trail = investigador.run("ALERT-PEP-003")
        pep_analysis, pep_trail = risk_analyzer.run(pep_context, pep_trail)
        decision, _ = decision_agent.run(pep_context, pep_analysis, pep_trail)
        assert len(decision.regulatory_references) > 0
