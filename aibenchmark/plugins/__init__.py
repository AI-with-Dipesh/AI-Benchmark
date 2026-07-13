# Plugin auto-registration: importing built-in modules triggers
# the @register decorator and registers them with the global PluginManager.

from aibenchmark.plugins.providers import (  # noqa: F401
    huggingface,
    nvidia,
    ollama,
    openrouter,
)
from aibenchmark.plugins.benchmarks import (  # noqa: F401
    coding,
    latency,
)
from aibenchmark.plugins.reporters import (  # noqa: F401
    analytics,
    generator,
    sprint4,
)
