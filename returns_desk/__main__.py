"""Answer one customer message and send the trace to an OTLP collector.

  GOOGLE_API_KEY=... python -m returns_desk "Hi, I'd like a refund for order N-1004."

OTEL_EXPORTER_OTLP_TRACES_ENDPOINT (default http://localhost:6006/v1/traces) is where the trace
goes; PHOENIX_PROJECT names the project it lands in.
"""

import os
import sys

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from returns_desk import agent


def main() -> None:
    provider = TracerProvider(
        resource=Resource({"openinference.project.name": os.environ.get("PHOENIX_PROJECT", "returns-desk")})
    )
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://localhost:6006/v1/traces")
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    trace_id, answer = agent.run(agent.client(), " ".join(sys.argv[1:]))
    print(answer)
    print(f"trace {trace_id}", file=sys.stderr)
    provider.shutdown()


if __name__ == "__main__":
    main()
