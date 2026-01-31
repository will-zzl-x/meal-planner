# Flexible Dieting Requirements (EARS Format)
# Meal Planning App - Weekly Calorie Management & Banking

## Body Composition Assessment
**EARS-DIET-001**: WHEN user selects body fat percentage via photo reference slider, THE SYSTEM SHALL calculate recommended weekly weight loss percentage range based on selected body fat level.

**EARS-DIET-002**: WHERE user confirms body fat selection, THE SYSTEM SHALL generate target weekly caloric deficit and daily calorie targets based on weight loss recommendation.

**EARS-DIET-003**: IF user prefers custom targets, THE SYSTEM SHALL allow manual calorie target input while maintaining minimum safety thresholds.

## Weekly Calorie Distribution
**EARS-DIET-004**: WHEN user sets weekly calorie target, THE SYSTEM SHALL distribute evenly across 7 days as default daily targets.

**EARS-DIET-005**: WHERE user plans high-calorie day in advance, THE SYSTEM SHALL subtract planned overage from preceding days to maintain weekly target.

**EARS-DIET-006**: IF calorie reduction would drop any day below 10 calories per pound of bodyweight, THE SYSTEM SHALL display warning and suggest alternative distribution.

## Daily Calorie Banking & Borrowing
**EARS-DIET-007**: WHEN user exceeds daily calorie limit, THE SYSTEM SHALL subtract overage from remaining days in the week proportionally.

**EARS-DIET-008**: WHERE user has banked calories from previous days, THE SYSTEM SHALL distribute banked calories as additional allowance across remaining days.

**EARS-DIET-009**: IF user logs calories under daily target, THE SYSTEM SHALL bank the difference for future use within the same week.

## Restaurant/Special Event Planning
**EARS-DIET-010**: WHEN user schedules restaurant outing without calorie estimate, THE SYSTEM SHALL automatically reduce preceding days by 100 calories each as preparation buffer while maintaining 10 calories per pound bodyweight minimum.

**EARS-DIET-011**: WHERE user provides estimated calories for special event, THE SYSTEM SHALL calculate exact daily reductions needed to accommodate within weekly target.

## User Interface Requirements
**EARS-DIET-012**: WHEN user views weekly plan, THE SYSTEM SHALL display:
- Weekly calorie target and remaining balance
- Daily targets with actual consumption
- Meals planned for that day
- Banked/borrowed calorie amounts
- Visual progress indicators for each day

**EARS-DIET-013**: WHERE user interacts with daily view, THE SYSTEM SHALL show:
- Today's target vs consumed calories
- Available banked calories from previous days
- Weekly calorie budget vs remaining
- Macro breakdown (protein, carbs, fats)
- Impact of today's choices on remaining week

**EARS-DIET-014**: IF user approaches minimum calorie threshold, THE SYSTEM SHALL display prominent warning with alternative suggestions.

## Macro Tracking
**EARS-DIET-015**: WHEN user logs meals, THE SYSTEM SHALL track and display protein, carbohydrate, and fat macros alongside calories.

**EARS-DIET-016**: WHERE user views macro progress, THE SYSTEM SHALL show daily and weekly macro targets vs actual consumption.

## Safety & Validation
**EARS-DIET-017**: WHEN calculating daily minimums, THE SYSTEM SHALL enforce 10 calories per pound bodyweight floor and reject distributions below this threshold.

**EARS-DIET-018**: WHERE user has less than 20% body fat, THE SYSTEM SHALL limit weekly deficit to maximum 1.5% of bodyweight before displaying warning.

**EARS-DIET-019**: WHERE user has greater than 20% body fat, THE SYSTEM SHALL limit weekly deficit to maximum 2% of bodyweight before displaying warning.
