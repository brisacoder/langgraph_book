```markdown
# OpenTelemetry Python: Linking Multiple Processes Under One Root Span

This document gathers examples and explanations on how to use [OpenTelemetry](https://opentelemetry.io/) in Python to create and propagate spans across multiple functions, modules, or even separate services. It focuses on how to continue a single “run” or end-to-end trace that starts in one program (Program A) and continues in another (Program B), or within the same program across different functions.

---

## 1. Introduction

Distributed tracing in OpenTelemetry is centered on **traces** and **spans**:

- A **trace** represents a single end-to-end request or workflow.
- A **span** is an individual operation or step in that workflow.

In most cases:
1. You have **one root span** that represents the entry point of the request or workflow.
2. Each subsequent operation creates **child spans** (or further descendants) so that your observability tool can show you a tree (or DAG) of operations.

The key to connecting spans is **propagation** of the **trace context**, which includes:

- **Trace ID**: The unique identifier for the entire trace (128-bit, often expressed as a 32-hex-digit string).
- **Span ID**: The identifier for a single span (64-bit, often a 16-hex-digit string).
- **Trace flags**: Typically indicates whether this trace is being sampled or not (1 = “sampled”).
- **Trace state** (optional): A vendor- or system-specific key-value dictionary for advanced propagation.

Below are various scenarios and code snippets illustrating how to work with these concepts in Python.

---

## 2. Why the Trace ID Matters

**Question**: *“What is the trace ID? Isn’t the span name enough?”*

The **trace ID** is critical because it uniquely identifies an entire trace (all spans that belong to the same end-to-end operation). The **span name** is just a human-readable string for labeling the operation. If two spans share the same span name, that does *not* imply they are part of the same trace. They must share the **same trace ID** (and be connected via parent-child relationships).

---

## 3. Passing the Trace Context from Program A to Program B

### Explanation

If you want **Program B** to continue the trace that **Program A** started—so that all spans show up under one single trace—then **B** needs to receive the **Trace ID** and the **parent span ID** from **A**. B will then create *child spans* referencing A’s span as the parent.

### Example

#### Program A (sender)

```python
from opentelemetry import trace
from opentelemetry.propagate import inject
import requests

tracer = trace.get_tracer(__name__)

def main():
    with tracer.start_as_current_span("A_root") as root_span:
        # Optionally do some work under the root span
        headers = {}
        inject(headers)  # This injects the current trace context into the headers
        
        # Now call Program B (over HTTP, for example)
        response = requests.get("http://program-b:5000/do_work", headers=headers)
        # The trace context is passed along via standard W3C traceparent/tracestate headers.
```

#### Program B (receiver)

```python
from opentelemetry.propagate import extract
from opentelemetry import trace
from flask import Flask, request

app = Flask(__name__)
tracer = trace.get_tracer(__name__)

@app.route('/do_work', methods=['GET'])
def do_work():
    # Extract the trace context from incoming headers
    ctx = extract(request.headers)
    # Start a new span as a child of that incoming context
    with tracer.start_as_current_span("B_span", context=ctx) as span:
        # Do the work
        return "B span done"
```

**Result**:  
- Both `A_root` and `B_span` share the same **Trace ID**.  
- `B_span` is a *child* of `A_root`.  
- Observability backends (Jaeger, Zipkin, etc.) will show a single trace tree.

---

## 4. Getting the Current Span’s Trace ID and Span ID

Sometimes you need to **manually** extract the trace ID (and possibly the parent’s span ID) to build a custom payload for Program B or for logging/correlation.

### Explanation

1. Use `trace.get_current_span()` to get the currently active span.
2. Call `.get_span_context()` on that span to retrieve the **SpanContext**.
3. From the `SpanContext`, access:
   - `trace_id`
   - `span_id`
   - `trace_flags`
   - `trace_state`

4. Convert `trace_id` and `span_id` to hex strings if needed.

### Example

```python
from opentelemetry import trace

def do_something():
    # 1) Get the active span
    current_span = trace.get_current_span()
    # 2) SpanContext
    span_context = current_span.get_span_context()

    # 3) Extract IDs
    trace_id = span_context.trace_id       # int, typically 128-bit
    span_id = span_context.span_id         # int, typically 64-bit

    # Convert to hex
    hex_trace_id = format(trace_id, '032x')
    hex_span_id = format(span_id, '016x')

    # Build a custom payload
    payload = {
        "trace_id": hex_trace_id,
        "span_id": hex_span_id,
        "trace_flags": int(span_context.trace_flags),
        "trace_state": dict(span_context.trace_state),
    }

    # For example, send this payload via message queue, etc.
    return payload
```

---

## 5. Creating a Child Span Using a Received SpanContext

### Explanation

When you receive the parent’s trace context in some custom payload, you can construct a **remote parent** `SpanContext` and wrap it in a `NonRecordingSpan` to start child spans under it.

### Example

```python
from opentelemetry import trace
from opentelemetry.trace import SpanContext, TraceFlags, TraceState

tracer = trace.get_tracer(__name__)

def handle_incoming_payload(payload):
    # Convert hex to int
    trace_id_int = int(payload["trace_id"], 16)
    span_id_int = int(payload["span_id"], 16)

    parent_span_context = SpanContext(
        trace_id=trace_id_int,
        span_id=span_id_int,
        is_remote=True,
        trace_flags=TraceFlags(payload["trace_flags"]),
        trace_state=TraceState(payload["trace_state"])
    )

    # Wrap the SpanContext in a NonRecordingSpan
    parent_nonrecording_span = trace.NonRecordingSpan(parent_span_context)
    
    # Put that into the context
    parent_ctx = trace.set_span_in_context(parent_nonrecording_span)

    with tracer.start_as_current_span("child_span", context=parent_ctx) as child:
        # Do work under the parent's trace
        pass
```

- `NonRecordingSpan`: A lightweight stand-in for a “real” span that exists remotely, allowing you to continue the trace without needing the actual in-process Span object.

---

## 6. Ensuring Program B Spans Appear Under Program A’s **Root** Span

### Explanation

If you specifically want **Program B** to attach *directly* under **A’s root span**, B must use:

- **`trace_id`** = A’s root trace ID
- **`parent_span_id`** = A’s *root span ID* (not just any child’s span ID)

That way, B’s first span shows up in the trace tree as a child of that root. If you only have the *child’s* span ID, B will become a child of that child. Both scenarios are valid in distributed tracing—it depends on how you want to structure the hierarchy.

---

## 7. Global Root Span Within a Single Program

### Explanation

It is **uncommon** to have one single global root span for the entire lifetime of a long-running process, because typically you want separate traces for separate requests. However, if you have a **single** long-running operation or script, you *can* do it:

1. Create a **global** root span once at startup.
2. Store it in a global variable.
3. In other functions, retrieve the global root span and create child spans from it.

### Example

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
global_root_span = None

def initialize_global_span():
    global global_root_span
    global_root_span = tracer.start_span("global_root_span")

def do_something():
    # Create a child span under the global root
    if global_root_span is None:
        return  # or handle error

    parent_ctx = trace.set_span_in_context(global_root_span)
    with tracer.start_as_current_span("child_span", context=parent_ctx):
        # do work
        pass

def shutdown_global_span():
    global global_root_span
    if global_root_span is not None:
        global_root_span.end()
        global_root_span = None

if __name__ == "__main__":
    initialize_global_span()
    do_something()
    # Possibly more functions...
    shutdown_global_span()
```

**Caveats**:  
- If your program handles multiple requests or tasks in parallel, a single global root span lumps them all together into one trace, which is typically not desirable in production.  
- Long-lived root spans can make trace data unwieldy.

---

## 8. End-to-End Example: Single Root Span Across Multiple Services

### Explanation

A typical distributed scenario has multiple services (A, B, C, etc.). The **first** service that receives the request (Service A) creates the **root span**. Each subsequent service continues that trace by extracting context and creating child spans.

**Service A** (HTTP endpoint):
```python
from opentelemetry import trace
from opentelemetry.propagate import inject
import requests

tracer = trace.get_tracer(__name__)

def service_a_handler(request):
    # Root span (for this request)
    with tracer.start_as_current_span("A_root") as root_span:
        # Some local work
        headers = {}
        inject(headers)  # inject current trace context
        # Call Service B
        requests.get("http://service-b/do_something", headers=headers)
        # ...
```

**Service B**:
```python
from opentelemetry import trace
from opentelemetry.propagate import extract
from flask import Flask, request

app = Flask(__name__)
tracer = trace.get_tracer(__name__)

@app.route("/do_something", methods=["GET"])
def do_something():
    # Extract context from A
    ctx = extract(request.headers)
    with tracer.start_as_current_span("B_span", context=ctx):
        # Do some work, possibly call Service C
        return "OK"
```

All spans will share the **same Trace ID**, forming a single, continuous trace from A to B (and beyond).

---

## 9. Conclusion

**Key Takeaways**:

1. **One root span** per logical request or workflow—do *not* create multiple roots if you want a single view end-to-end.  
2. **Propagate** the trace context (Trace ID, Span ID, etc.) so that downstream services can attach as children.  
3. **Use built-in propagators** (HTTP headers, messaging headers) if possible.  
4. **Manually extract and inject** the trace context when you have custom needs, leveraging `NonRecordingSpan` if you only have a remote `SpanContext`.  
5. A **global root span** is an edge case—generally used only in single, long-running scripts or demos, not typical multi-request servers.

Following these patterns ensures you can see an entire “run” or request flow from beginning to end across your distributed services, all under one trace.
```
