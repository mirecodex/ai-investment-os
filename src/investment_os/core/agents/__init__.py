from investment_os.core.agents.base import Analyst, AnalystError
from investment_os.core.agents.flow import ForeignFlowAnalyst
from investment_os.core.agents.fundamental import FundamentalAnalyst
from investment_os.core.agents.news import NewsAnalyst
from investment_os.core.agents.technical import TechnicalAnalyst


def default_analysts() -> list[Analyst]:
    """The MVP committee roster; single source for app wiring and eval runs."""
    return [TechnicalAnalyst(), FundamentalAnalyst(), NewsAnalyst(), ForeignFlowAnalyst()]


__all__ = [
    "Analyst",
    "AnalystError",
    "ForeignFlowAnalyst",
    "FundamentalAnalyst",
    "NewsAnalyst",
    "TechnicalAnalyst",
    "default_analysts",
]
