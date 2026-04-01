import logging

from fastapi import FastAPI
from opentelemetry import _logs as logs
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from sqlalchemy import Engine

from app.config import settings

logger = logging.getLogger(__name__)


def setup_telemetry(app: FastAPI, engine: Engine) -> None:
    if not settings.otel_enabled:
        logger.info("telemetry.disabled")
        return

    resource = Resource.create({"service.name": "easyorder"})

    dev = settings.otel_dev_mode

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    if dev:
        tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
    else:
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(),
        export_interval_millis=1000 if dev else 60_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Inject trace context into standard logging records before attaching the OTEL handler.
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Logs
    logger_provider = LoggerProvider(resource=resource)
    if dev:
        logger_provider.add_log_record_processor(SimpleLogRecordProcessor(OTLPLogExporter()))
    else:
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    logs.set_logger_provider(logger_provider)
    logging_handler = LoggingHandler(logger_provider=logger_provider, level=logging.NOTSET)
    logging.getLogger().addHandler(logging_handler)

    # Instrumentation
    SQLAlchemyInstrumentor().instrument(engine=engine)
    FastAPIInstrumentor.instrument_app(app)

    logger.info("telemetry.enabled", extra={"dev_mode": dev})


def shutdown_telemetry() -> None:
    if not settings.otel_enabled:
        return

    tracer_provider = trace.get_tracer_provider()
    if isinstance(tracer_provider, TracerProvider):
        tracer_provider.shutdown()

    meter_provider = metrics.get_meter_provider()
    if isinstance(meter_provider, MeterProvider):
        meter_provider.shutdown()

    logger_provider = logs.get_logger_provider()
    if isinstance(logger_provider, LoggerProvider):
        logger_provider.shutdown()
