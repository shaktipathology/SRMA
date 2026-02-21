# Import all models so alembic autogenerate can discover them
from app.models.base import Base
from app.models.review import Review
from app.models.paper import Paper
from app.models.stats_job import StatsJob
from app.models.protocol_version import ProtocolVersion
from app.models.search_query import SearchQuery
from app.models.screening_decision import ScreeningDecision
from app.models.grade_assessment import GradeAssessment
from app.models.phase_result import PhaseResult

__all__ = [
    "Base", "Review", "Paper", "StatsJob", "ProtocolVersion",
    "SearchQuery", "ScreeningDecision", "GradeAssessment", "PhaseResult",
]
