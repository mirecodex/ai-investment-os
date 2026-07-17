from investment_os.core.agents.base import Analyst, AnalystError
from investment_os.core.agents.flow import ForeignFlowAnalyst
from investment_os.core.agents.fundamental import FundamentalAnalyst
from investment_os.core.agents.macro import MacroAnalyst
from investment_os.core.agents.manager import ResearchManager, RoutingDecision
from investment_os.core.agents.news import NewsAnalyst
from investment_os.core.agents.news_llm import LlmNewsAnalyst
from investment_os.core.agents.quant import QuantAnalyst
from investment_os.core.agents.sector import SectorRotationAnalyst
from investment_os.core.agents.technical import TechnicalAnalyst


def default_analysts() -> list[Analyst]:
    """The full committee roster; single source for app wiring and eval runs."""
    return [
        TechnicalAnalyst(),
        FundamentalAnalyst(),
        NewsAnalyst(),
        ForeignFlowAnalyst(),
        QuantAnalyst(),
        MacroAnalyst(),
        SectorRotationAnalyst(),
    ]


__all__ = [
    "Analyst",
    "AnalystError",
    "ForeignFlowAnalyst",
    "FundamentalAnalyst",
    "LlmNewsAnalyst",
    "MacroAnalyst",
    "NewsAnalyst",
    "QuantAnalyst",
    "ResearchManager",
    "RoutingDecision",
    "SectorRotationAnalyst",
    "TechnicalAnalyst",
    "default_analysts",
]
