"""
Body Composition Service - Photo Reference and Target Calculations
Clean Architecture - Business Logic Layer
"""
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class BodyFatReference:
    """Body fat percentage reference with photo description."""
    percentage: Decimal
    description: str
    male_characteristics: List[str]
    female_characteristics: List[str]

@dataclass
class WeightLossRecommendation:
    """Weight loss recommendation based on body composition."""
    current_bf_percentage: Decimal
    recommended_weekly_loss_rate: Decimal  # Percentage of body weight
    max_weekly_loss_pounds: Decimal
    recommended_calorie_deficit: int
    timeline_weeks: Optional[int]
    safety_notes: List[str]

class BodyCompositionService:
    """Service for body composition assessment and weight loss recommendations."""
    
    def __init__(self):
        """Initialize body composition service with reference data."""
        self.body_fat_references = self._create_body_fat_references()
    
    def _create_body_fat_references(self) -> List[BodyFatReference]:
        """Create body fat percentage reference data for photo comparison."""
        return [
            BodyFatReference(
                percentage=Decimal('8'),
                description="Very Lean - Competition Ready",
                male_characteristics=[
                    "Visible abs with deep cuts",
                    "Visible striations in shoulders/legs",
                    "Very vascular throughout body",
                    "No visible fat on torso"
                ],
                female_characteristics=[
                    "Visible abs with definition",
                    "Very low fat on hips/thighs", 
                    "Visible muscle striations",
                    "Competition-level leanness"
                ]
            ),
            BodyFatReference(
                percentage=Decimal('12'),
                description="Lean - Athletic",
                male_characteristics=[
                    "Visible 6-pack abs",
                    "Defined shoulders and arms",
                    "Some vascularity",
                    "Minimal fat on torso"
                ],
                female_characteristics=[
                    "Flat stomach, some ab definition",
                    "Defined arms and shoulders",
                    "Minimal fat on hips",
                    "Athletic appearance"
                ]
            ),
            BodyFatReference(
                percentage=Decimal('15'),
                description="Fit - Above Average",
                male_characteristics=[
                    "Abs visible in good lighting",
                    "Defined upper body",
                    "Some definition in arms/shoulders",
                    "Slight fat layer on lower abs"
                ],
                female_characteristics=[
                    "Flat stomach",
                    "Some muscle definition",
                    "Healthy fat distribution",
                    "Fit appearance"
                ]
            ),
            BodyFatReference(
                percentage=Decimal('18'),
                description="Average - Healthy Range",
                male_characteristics=[
                    "No visible abs",
                    "Some muscle definition in arms",
                    "Slight love handles",
                    "Overall healthy appearance"
                ],
                female_characteristics=[
                    "Slight curve to stomach",
                    "Healthy fat on hips/thighs",
                    "Some arm/shoulder definition",
                    "Typical healthy range"
                ]
            ),
            BodyFatReference(
                percentage=Decimal('22'),
                description="Slightly Above Average",
                male_characteristics=[
                    "Soft appearance to midsection",
                    "Love handles present",
                    "Less muscle definition",
                    "Rounder face"
                ],
                female_characteristics=[
                    "Soft stomach curve",
                    "More fat on hips/thighs",
                    "Less muscle definition",
                    "Still within healthy range"
                ]
            ),
            BodyFatReference(
                percentage=Decimal('25'),
                description="Above Average - Consider Weight Loss",
                male_characteristics=[
                    "Noticeable belly fat",
                    "Love handles prominent",
                    "Minimal muscle definition",
                    "Rounder appearance overall"
                ],
                female_characteristics=[
                    "Noticeable stomach fat",
                    "Significant fat on hips/thighs",
                    "Arms appear softer",
                    "May benefit from fat loss"
                ]
            ),
            BodyFatReference(
                percentage=Decimal('30'),
                description="High - Weight Loss Recommended",
                male_characteristics=[
                    "Significant belly fat",
                    "Fat covers muscle definition",
                    "Double chin may be present",
                    "Health risks increase"
                ],
                female_characteristics=[
                    "Significant fat on stomach/hips",
                    "Thighs touch when standing",
                    "Arms appear larger",
                    "Health benefits from weight loss"
                ]
            ),
            BodyFatReference(
                percentage=Decimal('35'),
                description="Very High - Medical Consultation Advised",
                male_characteristics=[
                    "Large belly overhang",
                    "Significant fat throughout body",
                    "Difficulty seeing feet",
                    "Health risks significant"
                ],
                female_characteristics=[
                    "Large stomach and hip area",
                    "Significant fat on arms/back",
                    "May have mobility issues",
                    "Medical guidance recommended"
                ]
            )
        ]
    
    def get_body_fat_references(self, gender: str = "both") -> List[BodyFatReference]:
        """
        Get body fat reference data for photo comparison.
        
        Args:
            gender: "male", "female", or "both"
            
        Returns:
            List of body fat references for comparison
        """
        return self.body_fat_references
    
    def calculate_weight_loss_recommendation(self, 
                                           current_weight: Decimal,
                                           body_fat_percentage: Decimal,
                                           target_body_fat: Optional[Decimal] = None) -> WeightLossRecommendation:
        """
        Calculate weight loss recommendations based on body composition.
        
        Args:
            current_weight: Current body weight
            body_fat_percentage: Current body fat percentage
            target_body_fat: Optional target body fat percentage
            
        Returns:
            Weight loss recommendation with timeline and safety notes
        """
        # Determine recommended weekly loss rate based on body fat
        if body_fat_percentage >= 30:
            weekly_rate = Decimal('2.0')  # Up to 2% per week
            safety_notes = ["Higher body fat allows more aggressive approach"]
        elif body_fat_percentage >= 25:
            weekly_rate = Decimal('1.5')  # Up to 1.5% per week
            safety_notes = ["Moderate approach recommended"]
        elif body_fat_percentage >= 20:
            weekly_rate = Decimal('1.0')  # Up to 1% per week
            safety_notes = ["Conservative approach to preserve muscle"]
        elif body_fat_percentage >= 15:
            weekly_rate = Decimal('0.75')  # Up to 0.75% per week
            safety_notes = ["Very conservative approach", "Focus on body recomposition"]
        else:
            weekly_rate = Decimal('0.5')  # Up to 0.5% per week
            safety_notes = ["Extremely conservative", "Consider maintenance or reverse diet"]
        
        # Calculate maximum weekly loss in pounds
        max_weekly_loss = current_weight * (weekly_rate / 100)
        
        # Calculate recommended calorie deficit (3500 calories = 1 lb)
        recommended_deficit = int(max_weekly_loss * 3500 / 7)
        
        # Calculate timeline if target is provided
        timeline_weeks = None
        if target_body_fat and target_body_fat < body_fat_percentage:
            # Rough estimate - assumes 1 lb fat loss = 1% body fat reduction
            # This is simplified and varies by individual
            fat_to_lose = current_weight * (body_fat_percentage - target_body_fat) / 100
            timeline_weeks = int(fat_to_lose / max_weekly_loss) if max_weekly_loss > 0 else None
        
        # Add safety notes based on aggressiveness
        if recommended_deficit > 1000:
            safety_notes.append("Large deficit - monitor energy levels closely")
        if body_fat_percentage < 15:
            safety_notes.append("Low body fat - prioritize strength training")
        if timeline_weeks and timeline_weeks > 52:
            safety_notes.append("Long timeline - consider periodic diet breaks")
        
        return WeightLossRecommendation(
            current_bf_percentage=body_fat_percentage,
            recommended_weekly_loss_rate=weekly_rate,
            max_weekly_loss_pounds=max_weekly_loss,
            recommended_calorie_deficit=recommended_deficit,
            timeline_weeks=timeline_weeks,
            safety_notes=safety_notes
        )
    
    def get_body_fat_slider_data(self) -> List[Dict]:
        """
        Get body fat reference data formatted for UI slider component.
        
        Returns:
            List of body fat references formatted for slider display
        """
        slider_data = []
        
        for ref in self.body_fat_references:
            slider_data.append({
                "percentage": float(ref.percentage),
                "description": ref.description,
                "male_characteristics": ref.male_characteristics,
                "female_characteristics": ref.female_characteristics,
                "color": self._get_color_for_body_fat(ref.percentage)
            })
        
        return slider_data
    
    def _get_color_for_body_fat(self, percentage: Decimal) -> str:
        """Get color coding for body fat percentage ranges."""
        if percentage <= 12:
            return "green"  # Very lean
        elif percentage <= 18:
            return "lightgreen"  # Healthy
        elif percentage <= 25:
            return "yellow"  # Average
        elif percentage <= 30:
            return "orange"  # Above average
        else:
            return "red"  # High
    
    def estimate_lean_body_mass(self, total_weight: Decimal, body_fat_percentage: Decimal) -> Decimal:
        """
        Estimate lean body mass from total weight and body fat percentage.
        
        Args:
            total_weight: Total body weight
            body_fat_percentage: Body fat percentage
            
        Returns:
            Estimated lean body mass
        """
        fat_mass = total_weight * (body_fat_percentage / 100)
        lean_mass = total_weight - fat_mass
        return lean_mass
    
    def calculate_goal_weight(self, current_weight: Decimal, 
                            current_bf: Decimal, 
                            target_bf: Decimal) -> Decimal:
        """
        Calculate goal weight to achieve target body fat percentage.
        Assumes lean mass stays constant.
        
        Args:
            current_weight: Current total weight
            current_bf: Current body fat percentage
            target_bf: Target body fat percentage
            
        Returns:
            Goal weight to achieve target body fat
        """
        lean_mass = self.estimate_lean_body_mass(current_weight, current_bf)
        goal_weight = lean_mass / (1 - target_bf / 100)
        return goal_weight
