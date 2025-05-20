from typing import Dict, List
import json
from dataclasses import dataclass
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Ingredient:
    name: str
    quantity: float
    unit: str
    category: str
    estimated_price: float = 0.0

class ShoppingListAgent:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.store_categories = {
            "produce": ["vegetables", "fruits", "herbs"],
            "dairy": ["milk", "cheese", "yogurt", "butter"],
            "meat": ["beef", "chicken", "pork", "fish"],
            "pantry": ["grains", "canned goods", "spices", "oils"],
            "frozen": ["frozen vegetables", "frozen fruits", "frozen meals"],
            "bakery": ["bread", "pastries", "baked goods"],
            "deli": ["deli meats", "prepared foods"],
            "other": []
        }

    def process_meal_plans(self, meal_plans: Dict[str, Dict]) -> List[Ingredient]:
        """Process meal plans and extract ingredients."""
        all_ingredients = []
        
        for meal_type, meal_data in meal_plans.items():
            if isinstance(meal_data, dict) and "options" in meal_data:
                for meal in meal_data["options"]:
                    if "ingredients" in meal:
                        for ingredient in meal["ingredients"]:
                            # Create a basic ingredient entry
                            ingredient_data = {
                                "name": ingredient,
                                "quantity": 1.0,  # Default quantity
                                "unit": "piece",  # Default unit
                                "estimated_price": 0.0  # Will be updated if available
                            }
                            all_ingredients.append(self._parse_ingredient(ingredient_data))
        
        return self._consolidate_ingredients(all_ingredients)

    def _parse_ingredient(self, ingredient: Dict) -> Ingredient:
        """Parse ingredient data into Ingredient object."""
        return Ingredient(
            name=ingredient.get("name", ""),
            quantity=float(ingredient.get("quantity", 0)),
            unit=ingredient.get("unit", ""),
            category=self._categorize_ingredient(ingredient.get("name", "")),
            estimated_price=float(ingredient.get("estimated_price", 0))
        )

    def _categorize_ingredient(self, ingredient_name: str) -> str:
        """Categorize ingredient into store section."""
        ingredient_name = ingredient_name.lower()
        
        for category, keywords in self.store_categories.items():
            if any(keyword in ingredient_name for keyword in keywords):
                return category
        return "other"

    def _consolidate_ingredients(self, ingredients: List[Ingredient]) -> List[Ingredient]:
        """Consolidate similar ingredients and sum quantities."""
        consolidated = {}
        
        for ingredient in ingredients:
            key = (ingredient.name.lower(), ingredient.unit)
            if key in consolidated:
                consolidated[key].quantity += ingredient.quantity
                consolidated[key].estimated_price += ingredient.estimated_price
            else:
                consolidated[key] = ingredient
        
        return list(consolidated.values())

    def generate_shopping_list(self, meal_plans: Dict[str, Dict]) -> Dict:
        """Generate organized shopping list from meal plans."""
        ingredients = self.process_meal_plans(meal_plans)
        
        # Group by category
        categorized_list = {}
        for category in self.store_categories.keys():
            category_items = [i for i in ingredients if i.category == category]
            if category_items:
                categorized_list[category] = category_items
        
        # Calculate totals
        total_items = len(ingredients)
        total_estimated_cost = sum(i.estimated_price for i in ingredients)
        
        return {
            "categorized_list": categorized_list,
            "total_items": total_items,
            "total_estimated_cost": total_estimated_cost
        }

    def export_shopping_list(self, shopping_list: Dict, format: str = "text") -> str:
        """Export shopping list in specified format."""
        if format == "text":
            return self._format_text_list(shopping_list)
        elif format == "json":
            return json.dumps(shopping_list, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_text_list(self, shopping_list: Dict) -> str:
        """Format shopping list as text."""
        output = []
        output.append("Shopping List\n")
        output.append("=" * 50 + "\n")
        
        for category, items in shopping_list["categorized_list"].items():
            if items:
                output.append(f"\n{category.upper()}")
                output.append("-" * len(category))
                for item in items:
                    output.append(f"- {item.name}: {item.quantity} {item.unit}")
        
        output.append("\n" + "=" * 50)
        output.append(f"Total Items: {shopping_list['total_items']}")
        output.append(f"Estimated Total Cost: ${shopping_list['total_estimated_cost']:.2f}")
        
        return "\n".join(output) 