"""
Configuración de Langfuse para observabilidad del pipeline.
Registra: trazas de agentes, latencias, costo estimado por alerta, y prompts.

Si Langfuse no está disponible (LANGFUSE_ENABLED=false), usa un tracer no-op
para que el sistema funcione sin observabilidad en desarrollo local.
"""
from contextlib import contextmanager
from typing import Any, Generator

from config import settings


class NoOpSpan:
    """Span vacío para cuando Langfuse no está configurado."""
    def update(self, **kwargs: Any) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class NoOpTracer:
    """Tracer vacío. El sistema funciona normalmente sin observabilidad."""
    def span(self, name: str, **kwargs: Any):
        return NoOpSpan()

    def generation(self, name: str, **kwargs: Any):
        return NoOpSpan()


class LangfuseTracer:
    """Tracer real usando la SDK de Langfuse."""

    def __init__(self):
        from langfuse import Langfuse
        self._client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

    @contextmanager
    def span(self, name: str, **kwargs: Any) -> Generator:
        trace = self._client.trace(name=name, **kwargs)
        span = trace.span(name=name)
        try:
            yield span
        finally:
            span.end()
            self._client.flush()

    @contextmanager
    def generation(self, name: str, **kwargs: Any) -> Generator:
        trace = self._client.trace(name=name)
        generation = trace.generation(name=name, **kwargs)
        try:
            yield generation
        finally:
            generation.end()
            self._client.flush()


_tracer = None


def get_tracer() -> NoOpTracer | LangfuseTracer:
    """
    Retorna el tracer activo.
    - Si LANGFUSE_ENABLED=true y hay keys: tracer real
    - En cualquier otro caso: no-op (no rompe el sistema)
    """
    global _tracer
    if _tracer is None:
        if settings.langfuse_enabled and settings.langfuse_public_key:
            try:
                _tracer = LangfuseTracer()
            except Exception:
                _tracer = NoOpTracer()
        else:
            _tracer = NoOpTracer()
    return _tracer
