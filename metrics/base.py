from abc import ABC, abstractmethod
import networkx as nx


class IMetric(ABC):
    """Base interface for all graph metrics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier used to select this metric."""
        pass

    @abstractmethod
    def evaluate(self, graph: nx.Graph) -> float:
        """Calculate a numeric score for the input graph."""
        pass
