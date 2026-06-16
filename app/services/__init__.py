"""Services package — business logic layer."""

from app.services.student_manager import StudentManager
from app.services.statistics_service import StatisticsService

__all__ = ["StudentManager", "StatisticsService"]
