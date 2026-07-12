from aibenchmark.plugins.benchmarks.coding import CodingBenchmark
from aibenchmark.plugins.benchmarks.debugging import DebuggingBenchmark
from aibenchmark.plugins.benchmarks.general import GeneralBenchmark
from aibenchmark.plugins.benchmarks.instruction import InstructionBenchmark
from aibenchmark.plugins.benchmarks.json import JsonBenchmark
from aibenchmark.plugins.benchmarks.latency import LatencyBenchmark
from aibenchmark.plugins.benchmarks.reasoning import ReasoningBenchmark
from aibenchmark.plugins.benchmarks.research import ResearchBenchmark
from aibenchmark.plugins.benchmarks.code_review import CodeReviewBenchmark

__all__ = [
    "CodingBenchmark",
    "CodeReviewBenchmark",
    "DebuggingBenchmark",
    "GeneralBenchmark",
    "InstructionBenchmark",
    "JsonBenchmark",
    "LatencyBenchmark",
    "ReasoningBenchmark",
    "ResearchBenchmark",
]
