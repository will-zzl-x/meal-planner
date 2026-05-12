"""
Built-in recipe seed for new households. Imported on first registration so a
fresh household has something to plan with on day one.

Calorie figures are taken from each recipe's notes where the original author
stated them; the rest are zero with a "[calories pending lookup]" flag in
notes — slice 7 will add a Look-up-from-food-database button so the planner
can fill these in from USDA / Open Food Facts.

Quantities use the simplest faithful conversion of the original entries:
- "to taste" / blank quantity  →  quantity 0 (the descriptor stays in the
  ingredient name so it's still visible to the user).
- "2-3"  →  upper bound (more garlic is rarely a mistake).
- Parenthetical context in unit fields (e.g. "oz (~4 thighs)") is moved into
  the ingredient name; the unit field keeps just "oz".

The metadata the React prototype tracked but our schema doesn't yet (meal
slots, protein category) is preserved in the notes field so it's not lost.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List

from core.domain.models import Ingredient, Recipe


def _ing(name: str, qty: str, unit: str, store: str = "Walmart") -> Ingredient:
    """Compact builder for seed ingredient lines."""
    return Ingredient(name=name, quantity=Decimal(qty), unit=unit, store=store)


def _notes(*parts: str) -> str:
    """Glue together metadata chips and the original recipe note."""
    return "  ".join(p for p in parts if p)


_PENDING = "[calories pending lookup]"


def all_seed_recipes() -> List[Recipe]:
    """Return the canonical list of seed recipes for a brand-new household."""
    return [
        Recipe(
            name="Chicken Teriyaki",
            base_servings=4,
            calories_per_serving=0,
            notes=_notes(
                "[Protein: Chicken Thigh] [Slots: M2]", _PENDING,
                "Scale to 2 packs (8 thighs) for 8 servings. Marinate 30 min to overnight.",
            ),
            instructions=[
                "Marinate thighs in dark soy sauce, light soy sauce, minced garlic, sweetener, five spice powder, and white pepper. Let sit 30 min to overnight.",
                "Start 1 cup of rice in the rice cooker.",
                "Air fry chicken at 360F for 17 minutes.",
                "Steam bok choy or gai lan for 11 minutes. Salt when done.",
                "Divide into 4 containers: rice, 1 thigh, and veg.",
            ],
            ingredients=[
                _ing("Chicken thighs (1 Costco pack)", "4", "thighs", "Costco"),
                _ing("Dark soy sauce", "2", "tbsp", "Asian Mart"),
                _ing("Light soy sauce", "3", "tbsp", "Asian Mart"),
                _ing("Garlic minced", "3", "cloves", "Walmart"),
                _ing("Zero calorie sweetener (Splenda)", "2", "packets", "Walmart"),
                _ing("Five spice powder (to taste)", "0", "tsp", "Asian Mart"),
                _ing("White pepper (to taste)", "0", "tsp", "Asian Mart"),
                _ing("Bok choy or gai lan", "1", "pack", "Asian Mart"),
                _ing("White rice (dry)", "1", "cup", "Walmart"),
            ],
        ),
        Recipe(
            name="Cheesy Chipotle Chicken Rice Bowls",
            base_servings=5,
            calories_per_serving=585,
            notes=_notes(
                "[Protein: Chicken Thigh] [Slots: M2]",
                "585 cal / 52g protein / 57g carbs / 17g fat per serving. Air fryer only. From @stealth_health_life.",
            ),
            instructions=[
                "Mix chicken thighs with avocado oil, hot honey, and all dry seasonings (chipotle/ancho chili powder, garlic powder, onion powder, black pepper, salt). Toss to coat evenly. Marinate in fridge - add lime juice just before cooking.",
                "Air fry chicken at 375F for 20-25 minutes, flipping halfway, until cooked through and lightly charred. Remove and chop into bite-sized pieces.",
                "Remove air fryer rack. Add diced bell peppers, half onion, 2 tsp oil, and 1 tbsp tomato paste directly to the basket. Air fry at 350F for 10-15 minutes, stirring once or twice, until softened and lightly browned.",
                "Add cooked rice to the veggies in the basket (or transfer to a large bowl). Stir in 1/2 cup mozzarella, 1/2 cup cheddar, and 1/2 cup Greek yogurt until melted and creamy. Add chopped chicken and cilantro. Mix until combined.",
                "Whisk together sauce ingredients: 3/4 cup Greek yogurt, 1/4 cup milk, 1 tsp honey, 3 tbsp adobo sauce, smoked paprika, and salt until smooth.",
                "Divide into 5 equal servings and top each with smoky chipotle sauce.",
            ],
            ingredients=[
                _ing("Skinless chicken thighs (~4 thighs)", "32", "oz", "Costco"),
                _ing("Avocado oil", "1", "tsp", "Walmart"),
                _ing("Hot honey", "1", "tbsp", "Walmart"),
                _ing("Lime juiced day-of", "0.5", "lime", "Walmart"),
                _ing("Chipotle or ancho chili powder (to taste, heavy)", "0", "tsp", "Walmart"),
                _ing("Garlic powder (to taste, heavy)", "0", "tsp", "Walmart"),
                _ing("Onion powder (to taste, heavy)", "0", "tsp", "Walmart"),
                _ing("Black pepper + salt (to taste)", "0", "tsp", "Walmart"),
                _ing("Bell peppers", "2", "peppers", "Walmart"),
                _ing("Yellow onion", "0.5", "onion", "Walmart"),
                _ing("Oil", "2", "tsp", "Walmart"),
                _ing("Tomato paste", "1", "tbsp", "Walmart"),
                _ing("White rice (dry)", "2", "cup", "Walmart"),
                _ing("Reduced fat mozzarella", "0.5", "cup", "Walmart"),
                _ing("Extra sharp cheddar", "0.5", "cup", "Walmart"),
                _ing("0% Greek yogurt (finishing)", "0.5", "cup", "Costco"),
                _ing("Cilantro", "1", "handful", "Walmart"),
                _ing("0% Greek yogurt (sauce)", "0.75", "cup", "Costco"),
                _ing("Milk", "0.25", "cup", "Walmart"),
                _ing("Honey", "1", "tsp", "Walmart"),
                _ing("Adobo sauce", "3", "tbsp", "Walmart"),
                _ing("Smoked paprika + salt (to taste)", "0", "tsp", "Walmart"),
            ],
        ),
        Recipe(
            name="Hoisin Chicken Thigh Chow Mein",
            base_servings=5,
            calories_per_serving=0,
            notes=_notes(
                "[Protein: Chicken Thigh] [Slots: M2]", _PENDING,
                "ON BREAK - rotate back in a future cycle. Adapted from Joshua Weissman. Protein doubled to 4 thighs, sauce scaled 1.5x, garlic bumped to 10 cloves. Veg quantities increased across the board. Dutch oven recommended given large volume. Optional toppings: fried egg, chili oil.",
            ),
            instructions=[
                "Whisk together soy sauce, rice vinegar, hoisin sauce, and sesame oil. Whisk in cornstarch until dissolved. Set sauce aside.",
                "Season the wok: add a little vegetable oil, heat over medium-high until smoking, turn off heat, pour out oil, wipe down with paper towels.",
                "Heat 3 tbsp vegetable oil in wok over medium-high. Working in two batches, sear chicken until cooked through, stirring often, about 5-8 minutes per batch. Set aside.",
                "Saute green onions until charred and slightly wilted (~30 seconds). Add 3/4 of the garlic, stir fry until golden. Add celery and carrot, stir fry until softened (~2 minutes). Raise to high heat, add cabbage and stir fry until charred and wilted (~2 minutes).",
                "Return chicken to wok, reduce to medium-high, stir fry 30 seconds.",
                "Add bean sprouts, stir fry 30 seconds. Add noodles, stir fry 45 seconds. Pour in sauce and toss to coat. Add 2 tbsp water and stir fry until noodles are glossy.",
                "Turn off heat, stir in remaining garlic. Add more soy sauce to taste. Garnish with scallions.",
            ],
            ingredients=[
                _ing("Chicken thighs boneless skinless", "24", "oz", "Costco"),
                _ing("Fresh chow mein / egg noodles", "16", "oz", "Asian Mart"),
                _ing("Soy sauce", "5", "tbsp", "Asian Mart"),
                _ing("Rice vinegar", "3", "tbsp", "Asian Mart"),
                _ing("Hoisin sauce", "4.5", "tbsp", "Asian Mart"),
                _ing("Toasted sesame oil", "2", "tsp", "Asian Mart"),
                _ing("Cornstarch", "1", "tbsp", "Walmart"),
                _ing("Vegetable oil", "3", "tbsp", "Walmart"),
                _ing("Green onions", "3", "stalks", "Walmart"),
                _ing("Garlic finely chopped", "10", "cloves", "Walmart"),
                _ing("Celery", "3", "ribs", "Walmart"),
                _ing("Carrot julienned", "2", "whole", "Walmart"),
                _ing("Napa cabbage thinly sliced", "5", "cup", "Asian Mart"),
                _ing("Bean sprouts", "10", "oz", "Asian Mart"),
                _ing("Water", "2", "tbsp", ""),
                _ing("Scallions garnish (to taste)", "0", "tsp", "Walmart"),
            ],
        ),
        Recipe(
            name="Mexican Chicken and Rice",
            base_servings=4,
            calories_per_serving=450,
            notes=_notes(
                "[Protein: Chicken Breast] [Slots: M2]",
                "450 cal / 45g protein / 47g carbs / 9g fat per serving (original macros - black beans and rice adjusted so may vary). Dutch oven recommended. Liquid ratio 2:1 - tomatoes provide ~1.5 cups + 1 cup stock = ~2.5 cups total for 1.2 cups rice. Do NOT add lime to chicken marinade - add at liquid step.",
            ),
            instructions=[
                "Season cubed chicken with oregano, paprika, garlic powder, cumin, chili powder, salt + pepper, and olive oil. Do NOT add lime yet.",
                "Cook chicken in Dutch oven over medium-high 6-8 minutes until cooked through. Set aside.",
                "In same Dutch oven, saute onion and red bell pepper over medium heat (lid off) until softened and lightly caramelized, 3-4 minutes.",
                "Add 1.2 cups dry basmati rice + 1 tsp of each seasoning. Toast with veg for 1-2 minutes, stirring constantly.",
                "Add 15oz can black beans, 1 can chopped tomatoes, 1 cup stock, and juice of 1 whole lime. Mix well.",
                "Lid on, simmer on lowest heat for 12-15 minutes. Stir gently at 7 minutes scraping bottom to prevent sticking. Check liquid - add splash of stock if dry.",
                "Check rice is cooked through. If not, add small splash of water, lid on 2-3 more minutes.",
                "Add chicken back in, mix in chopped cilantro stems + leaves. Taste and adjust salt + pepper.",
                "Divide into 4 containers. Garnish with cilantro leaves only.",
            ],
            ingredients=[
                _ing("Chicken breast cubed (~1.6lb)", "26.5", "oz", "Costco"),
                _ing("Oregano", "2", "tsp", "Walmart"),
                _ing("Paprika", "2", "tsp", "Walmart"),
                _ing("Garlic powder", "1", "tsp", "Walmart"),
                _ing("Cumin", "1", "tsp", "Walmart"),
                _ing("Chili powder", "1", "tsp", "Walmart"),
                _ing("Salt + pepper (each)", "1", "tsp", "Walmart"),
                _ing("Lime whole juiced", "1", "lime", "Walmart"),
                _ing("Olive oil", "2", "tsp", "Walmart"),
                _ing("Medium onion chopped", "1", "onion", "Walmart"),
                _ing("Medium red bell pepper chopped", "1", "pepper", "Walmart"),
                _ing("Black beans (15oz can)", "1", "can", "Walmart"),
                _ing("Canned chopped tomatoes (400g)", "1", "can", "Walmart"),
                _ing("Dry basmati rice", "1.2", "cup", "Walmart"),
                _ing("Water or chicken stock", "1", "cup", "Walmart"),
                _ing("Cilantro chopped", "0.25", "bunch", "Walmart"),
            ],
        ),
        Recipe(
            name="Crispy Chicken Sandwiches",
            base_servings=8,
            calories_per_serving=440,
            notes=_notes(
                "[Protein: Chicken Breast] [Slots: M4]",
                "440 cal / 50g protein / 43g carbs / 6g fat per sandwich. From @stealth_health_life. Parcooked for meal prep - finish on reheat day. Meal 4 only, does not reheat well in microwave.",
            ),
            instructions=[
                "Tenderize chicken breasts until flattened. Slice each in half to make 8 pieces. Season with salt and garlic powder.",
                "Set up dipping stations - Station 1: flour + salt, garlic powder, pepper. Station 2: egg whites + hot sauce. Station 3: crushed corn flakes.",
                "Dredge each piece: flour -> egg white/hot sauce -> cornflakes, pressing firmly to fully coat.",
                "Spray lightly with oil spray.",
                "PARCOOK: Air fry at 400F for 10 minutes, flipping at 5 minutes. Internal temp ~150F. Cool and refrigerate.",
                "REHEAT DAY-OF: Air fry at 350F for 5-6 minutes until internal temp reaches 165F.",
                "Toast brioche buns at 400F for 2-3 minutes.",
                "Mix sauce: 3/4 cup Greek yogurt + 2 tbsp + 2 tsp Sriracha + 1 tsp Gochujang (optional) + 2 tsp pickle juice. Adjust pickle juice to taste.",
                "Slice tomatoes, season with salt. Set aside.",
                "TWICE FRIED FRIES: Cut potatoes into fries. Boil in salted water for 10 minutes. Drain and pat dry. Air fry at 380F for 10 minutes (parcook). Toss with fry seasoning. Air fry at 400F for 10 minutes until crispy.",
                "Spread sauce on bun, top with chicken, sliced tomato, and pickles. Serve with fries.",
            ],
            ingredients=[
                _ing("Chicken breasts halved (~12oz each)", "4", "breasts", "Costco"),
                _ing("Salt + garlic powder (to taste)", "0", "tsp", "Walmart"),
                _ing("Flour (Station 1)", "0.33", "cup", "Walmart"),
                _ing("Salt + garlic powder + pepper (Station 1, to taste)", "0", "tsp", "Walmart"),
                _ing("Egg whites (Station 2)", "0.5", "cup", "Costco"),
                _ing("Hot sauce (Station 2, to taste)", "0", "tsp", "Walmart"),
                _ing("Corn flakes crushed (Station 3)", "2", "cup", "Walmart"),
                _ing("Oil spray", "1", "whole", "Walmart"),
                _ing("Brioche buns", "8", "buns", "Walmart"),
                _ing("Fat free Greek yogurt (sauce)", "0.75", "cup", "Costco"),
                _ing("Sriracha (sauce)", "2.66", "tbsp", "Walmart"),
                _ing("Gochujang optional (sauce)", "1", "tsp", "Asian Mart"),
                _ing("Pickle juice (sauce)", "2", "tsp", "Walmart"),
                _ing("Idaho potatoes cut into fries", "2", "large", "Walmart"),
                _ing("Roma tomato sliced", "2", "tomatoes", "Walmart"),
                _ing("Salt for tomato + fries (to taste)", "0", "tsp", "Walmart"),
                _ing("Garlic powder (fry seasoning)", "1", "tsp", "Walmart"),
                _ing("Paprika (fry seasoning)", "1", "tsp", "Walmart"),
                _ing("Onion powder (fry seasoning)", "0.5", "tsp", "Walmart"),
                _ing("Black pepper (fry seasoning)", "0.25", "tsp", "Walmart"),
            ],
        ),
        Recipe(
            name="Rotisserie Chicken with Garlic Rice and Kale",
            base_servings=4,
            calories_per_serving=0,
            notes=_notes(
                "[Protein: Rotisserie Chicken] [Slots: M3]", _PENDING,
                "Meal 3 only. Keep rotisserie drippings - key for moisture. Garlic rice replaces potatoes. Kale replaces asparagus. No parsley.",
            ),
            instructions=[
                "Cook 1.25 cups short grain rice per rice cooker instructions.",
                "While rice cooks, heat 1 tsp avocado oil in small pan over medium. Saute 3 cloves minced garlic 30 seconds. Toss with cooked rice, season with salt + pepper.",
                "Heat 1 tbsp olive oil in skillet over medium-high. Add torn kale, saute 3-4 minutes until wilted and lightly charred. Season with salt + pepper.",
                "Pull rotisserie chicken into 5 equal portions. Drizzle rotisserie drippings from container over each portion.",
                "Divide into 5 containers: chicken + garlic rice + kale.",
            ],
            ingredients=[
                _ing("Rotisserie chicken with drippings", "1", "whole", "Costco"),
                _ing("Short grain Japanese rice", "1.25", "cup", "Asian Mart"),
                _ing("Garlic minced", "3", "cloves", "Walmart"),
                _ing("Avocado oil", "1", "tsp", "Walmart"),
                _ing("Salt + pepper (to taste)", "0", "tsp", "Walmart"),
                _ing("Kale roughly torn", "1", "bunch", "Walmart"),
                _ing("Olive oil for kale", "1", "tbsp", "Walmart"),
            ],
        ),
        Recipe(
            name="Bibimbap",
            base_servings=6,
            calories_per_serving=0,
            notes=_notes(
                "[Protein: Ground Beef] [Slots: M2 M4]", _PENDING,
                "Traditional bibimbap inspired. Crispy rice step removed - cauliflower rice provides texture contrast. Store egg and sauce separately for meal prep. Fried egg replaces scrambled for better flavor - runny yolk acts as secondary sauce.",
            ),
            instructions=[
                "Cook 1.5 cups white rice in rice cooker.",
                "Brown 2 lbs ground beef over medium-high. Season with salt, pepper, 3 tbsp soy sauce, 1 tbsp gochugaru, 1/2 tsp ground ginger, 12 shakes garlic powder. Cook through.",
                "Microwave cauliflower rice per package instructions. Drain well, toss with 1 tsp salt. Air fry at 400F for 8 minutes.",
                "Saute shredded carrots 3 minutes over medium heat. Salt to taste.",
                "Boil spinach 1 minute, drain, toss with salt.",
                "Mix sauce: 5/8 cup gochujang + 9 packets sweetener + 1/2 cup hot water. Stir until combined.",
                "Fry 1 egg per serving sunny side up or over easy.",
                "Assemble: rice + cauliflower rice + beef + carrots + spinach. Top with fried egg and drizzle sauce.",
                "Divide into 6 containers. Store egg and sauce separately.",
            ],
            ingredients=[
                _ing("Ground beef 90/10", "2", "lb", "Costco"),
                _ing("Soy sauce", "3", "tbsp", "Asian Mart"),
                _ing("Gochugaru", "1", "tbsp", "Asian Mart"),
                _ing("Ground ginger", "0.5", "tsp", "Walmart"),
                _ing("Garlic powder", "12", "shakes", "Walmart"),
                _ing("Salt + pepper (to taste)", "0", "tsp", "Walmart"),
                _ing("White rice (dry)", "1.5", "cup", "Walmart"),
                _ing("Cauliflower rice", "1", "bag", "Walmart"),
                _ing("Shredded carrots", "1", "bag", "Walmart"),
                _ing("Spinach", "1", "bag", "Walmart"),
                _ing("Eggs (1 per serving fried)", "6", "eggs", "Costco"),
                _ing("Gochujang", "0.625", "cup", "Asian Mart"),
                _ing("No calorie sweetener", "9", "packets", "Walmart"),
                _ing("Hot water for sauce", "0.5", "cup", ""),
            ],
        ),
        Recipe(
            name="Spaghetti with Meat Sauce",
            base_servings=6,
            calories_per_serving=0,
            notes=_notes(
                "[Protein: Ground Beef] [Slots: M2 M4]", _PENDING,
                "M2 by default, overflow to M4. Reheats well in microwave. Needs large oven-safe pan. 90/10 subbed for 88/12 - slightly leaner.",
            ),
            instructions=[
                "Preheat oven to 425F.",
                "Toss carrot sticks with 1 tbsp oil + salt. Air fry at 375F for 20 minutes, shaking every 5 minutes until browned and soft.",
                "In a large oven-safe pan over medium-high, saute grated garlic + diced onion for 1 minute.",
                "Add ground beef + sausage. Sear 4 minutes, flip and break up until browned throughout.",
                "Stir in tomato paste, crushed tomatoes, beef bouillon, water, oregano, chili flakes, salt + pepper. Bring to a simmer.",
                "Stir in broken spaghetti until fully submerged.",
                "Transfer pan to oven. Bake uncovered 16-18 minutes, stirring thoroughly at the 5 and 10 minute marks.",
                "Remove from oven, rest 2 minutes.",
                "Divide into 6 containers with air fried carrots on the side.",
            ],
            ingredients=[
                _ing("Ground beef 90/10", "1.2", "lb", "Costco"),
                _ing("Ground sausage cheapest", "8", "oz", "Walmart"),
                _ing("Garlic grated", "6", "cloves", "Walmart"),
                _ing("Medium onion diced", "0.5", "onion", "Walmart"),
                _ing("Crushed tomatoes (28oz can ~800g)", "28", "oz", "Walmart"),
                _ing("Tomato paste", "4", "tbsp", "Walmart"),
                _ing("Beef bouillon", "1.5", "tbsp", "Walmart"),
                _ing("Water (~800ml)", "3.4", "cup", ""),
                _ing("Thin spaghetti broken in half", "16", "oz", "Walmart"),
                _ing("Oregano", "0.5", "tsp", "Walmart"),
                _ing("Chili flakes", "0.5", "tsp", "Walmart"),
                _ing("Salt + pepper (to taste)", "0", "tsp", "Walmart"),
                _ing("Carrots side", "1", "lb", "Walmart"),
                _ing("Oil for carrots", "1", "tbsp", "Walmart"),
            ],
        ),
        Recipe(
            name="NY Strip Steak and Salad",
            base_servings=2,
            calories_per_serving=0,
            notes=_notes(
                "[Protein: Steak] [Slots: M4]", _PENDING,
                "M4 only. Porcini powder adds deep umami. Carrot top chimichurri as steak sauce. Light sherry vinegar + EVOO dressing on salad. Use greens medley immediately - most perishable.",
            ),
            instructions=[
                "Pat steaks dry. Season with salt, pepper, garlic powder, and 1/2 tsp porcini powder per steak.",
                "Place steaks in freezer for 45 minutes.",
                "Make chimichurri: finely chop 1 cup packed carrot tops, combine with 3 cloves minced garlic, 2 tbsp sherry vinegar, 4 tbsp EVOO, 1/2 tsp chili flakes, salt + pepper. Set aside.",
                "Pull steaks, rest 5 minutes at room temp while cast iron heats to level 9.",
                "Preheat oven to 200F.",
                "Add grape seed oil to cast iron. Sear steaks 1 minute each side.",
                "Place rosemary under steaks, add 1 tbsp butter/ghee on top. Transfer to oven and finish until probe thermometer hits 135F.",
                "While steak rests, saute 4 large bulb green onions in same cast iron with 1 tsp avocado oil. Cook 3-4 minutes until charred.",
                "Dress salad: greens medley + torn kale, 1 tbsp sherry vinegar, 2 tbsp EVOO, salt + pepper. Toss lightly.",
                "Add sliced Roma tomato and avocado, toss gently.",
                "Plate: steak + chimichurri + salad + green onions.",
            ],
            ingredients=[
                _ing("NY strip steaks", "2", "steaks", "Costco"),
                _ing("Salt + pepper (to taste)", "0", "tsp", "Walmart"),
                _ing("Garlic powder (to taste)", "0", "tsp", "Walmart"),
                _ing("Porcini powder per steak", "0.5", "tsp", "Walmart"),
                _ing("Grape seed oil", "1", "tbsp", "Walmart"),
                _ing("Butter or ghee", "1", "tbsp", "Walmart"),
                _ing("Fresh rosemary", "2", "sprigs", "Walmart"),
                _ing("Greens medley + torn kale", "56", "g", "Walmart"),
                _ing("Roma tomato sliced", "1", "tomato", "Walmart"),
                _ing("Avocado sliced", "1", "whole", "Walmart"),
                _ing("Sherry vinegar (salad dressing)", "1", "tbsp", "Walmart"),
                _ing("EVOO (salad dressing)", "2", "tbsp", "Walmart"),
                _ing("Large bulb green onions trimmed", "4", "stalks", "Walmart"),
                _ing("Avocado oil for green onions", "1", "tsp", "Walmart"),
                _ing("Carrot tops finely chopped (chimichurri)", "1", "cup", "Walmart"),
                _ing("Garlic minced (chimichurri)", "3", "cloves", "Walmart"),
                _ing("Sherry vinegar (chimichurri)", "2", "tbsp", "Walmart"),
                _ing("EVOO (chimichurri)", "4", "tbsp", "Walmart"),
                _ing("Chili flakes (chimichurri)", "0.5", "tsp", "Walmart"),
            ],
        ),
        Recipe(
            name="Salmon Poke Bowl",
            base_servings=4,
            calories_per_serving=0,
            notes=_notes(
                "[Protein: Salmon] [Slots: M2 M4]", _PENDING,
                "M4 on weekdays, any slot on weekends. Batch prep rice (cheater sushi rice method), toppings, and sauce. Portion and freeze salmon individually - defrost per serving throughout the week and assemble fresh. Marinate defrosted salmon 15-20 min before assembling.",
            ),
            instructions=[
                "Cheater sushi rice: combine 1 cup short grain rice, water per rice cooker instructions minus 3 tbsp, 3 tbsp rice vinegar, 1 packet sweetener, 1/4 tsp salt. Cook in rice cooker as normal.",
                "Dice salmon into cubes.",
                "Mix sauce: 4 tbsp soy sauce + 1.5 tsp sesame oil + 1 tbsp rice vinegar + 2 packets sweetener + 1 tsp grated ginger + sliced spring onion + 1/2 tsp togarashi.",
                "Toss salmon in sauce. Marinate 15-20 minutes.",
                "Slice cucumber and avocado. Dice pineapple.",
                "Assemble in order: rice -> salmon -> cucumber -> pineapple -> avocado -> sauce drizzle -> 1 tsp sesame seeds -> togarashi -> cilantro -> spring onion.",
                "Serve immediately.",
            ],
            ingredients=[
                _ing("Farmed skin-off salmon diced", "4", "pieces", "Costco"),
                _ing("Short grain Japanese rice", "1", "cup", "Asian Mart"),
                _ing("Rice vinegar (rice + sauce)", "4", "tbsp", "Asian Mart"),
                _ing("Zero calorie sweetener", "3", "packets", "Walmart"),
                _ing("Salt for rice", "0.25", "tsp", "Walmart"),
                _ing("Soy sauce", "4", "tbsp", "Asian Mart"),
                _ing("Toasted sesame oil", "1.5", "tsp", "Asian Mart"),
                _ing("Fresh ginger grated", "1", "tsp", "Walmart"),
                _ing("Spring onion thinly sliced", "1", "stalks", "Walmart"),
                _ing("Togarashi", "0.5", "tsp", "Asian Mart"),
                _ing("Sesame seeds", "1", "tsp", "Asian Mart"),
                _ing("Cilantro", "1", "handful", "Walmart"),
                _ing("Pineapple diced", "2", "cup", "Costco"),
                _ing("Cucumber sliced", "1", "whole", "Walmart"),
                _ing("Avocado sliced", "1", "whole", "Walmart"),
            ],
        ),
    ]


def seed_recipes_for_household(recipe_repo, household_id: str, created_by_user_id: str) -> int:
    """Insert the seed recipes for a household. Returns the count saved.

    Idempotent: if any recipes already exist for this household, does nothing.
    """
    if recipe_repo.find_all_by_household(household_id):
        return 0
    count = 0
    for recipe in all_seed_recipes():
        recipe_repo.save(recipe, household_id=household_id, created_by_user_id=created_by_user_id)
        count += 1
    return count
