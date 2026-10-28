from __future__ import annotations

from .base import Analyzer, FileAnalyzer
from .conventions import ConventionsAnalyzer
from .dependencies import DependenciesAnalyzer
from .endpoints import EndpointsAnalyzer
from .overview import OverviewAnalyzer
from .security import SecurityAnalyzer
from .structure import StructureAnalyzer
from .todos import TodosAnalyzer

ALL_ANALYZERS = [
    OverviewAnalyzer(),
    StructureAnalyzer(),
    EndpointsAnalyzer(),
    DependenciesAnalyzer(),
    TodosAnalyzer(),
    SecurityAnalyzer(),
    ConventionsAnalyzer(),
]

FILE_ANALYZERS = [a for a in ALL_ANALYZERS if isinstance(a, FileAnalyzer)]
GLOBAL_ANALYZERS = [a for a in ALL_ANALYZERS if not isinstance(a, FileAnalyzer)]
