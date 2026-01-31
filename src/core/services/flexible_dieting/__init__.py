# Flexible Dieting Services Package
# Advanced business logic for calorie banking, weight tracking, and body composition

from .weight_tracking_service import WeightTrackingService, WeightLog, WeightProgress, TDEEEstimate
from .calorie_banking_service import CalorieBankingService, DailyCalorieTarget, WeeklyDistribution
from .body_composition_service import BodyCompositionService, BodyFatReference, WeightLossRecommendation

__all__ = [
    'WeightTrackingService', 'WeightLog', 'WeightProgress', 'TDEEEstimate',
    'CalorieBankingService', 'DailyCalorieTarget', 'WeeklyDistribution', 
    'BodyCompositionService', 'BodyFatReference', 'WeightLossRecommendation'
]
