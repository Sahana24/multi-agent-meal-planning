from autogen import AssistantAgent
from config import groq_config
import json
import re

class BreakfastAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="BreakfastAgent",
            system_message=f"""
                You are a breakfast specialist AI. Your responsibilities:
                1. Suggest a set number of breakfast options matching the user's dietary needs.
                2. Ensure meals take a reasonable preparation time.
                3. Include cost estimates for each option.
                4. Validate affordability using BudgetCheckerTool.

                Required format:
                {{
                    "options": [
                        {{
                            "name": "string (e.g., 'Avocado Toast')",
                            "description": "string (brief meal description)",
                            "calories": "integer (e.g., 300-500)",
                            "cost": "float (e.g., 2.50)",
                            "prep_time": "string (e.g., '15 mins')",
                            "ingredients": ["string (e.g., 'item1')", "string (e.g., 'item2')"]
                        }}
                    ],
                    "budget_check": {{
                        "status": "string ('approved' or 'denied')",
                        "message": "string (budget feedback)"
                    }}
                }}
            """, 
            llm_config={
                **groq_config.llm_config,
                "temperature": 0.7,
                "functions": None,  
                "function_call": "none"  
            }
        )
    
    def generate_suggestions(self, user_input, budget_agent):
        max_retries = 3
        attempts = 0
        dietary = user_input.get("dietary", "").lower()
        
        # Dietary enforcement
        forbidden = {
        "vegetarian": [
            "bacon", "sausage", "ham", "chicken", "turkey", "beef", "pork", "fish", "shellfish", "gelatin"
        ],
        "vegan": [
            "egg", "yogurt", "honey", "milk", "butter", "cheese", "cream", "gelatin", "mayonnaise"
        ],
        "gluten-free": [
            "wheat", "bread", "pancake", "waffle", "croissant", "bagel", "muffin", "cereal", "oats (unless certified GF)",
            "french toast", "pasta", "flour", "barley", "rye", "crackers", "cookies", "cake"
        ]
        }.get(dietary, [])
        while attempts < max_retries:
            try:
                num_meal_types = 4
                max_meal_budget = budget_agent.remaining_budget / num_meal_types
                max_meal_calories = user_input.get("calorie_goal", 2000) / num_meal_types
                
                messages = [{
                    "role": "user",
                    "content": f"""Create exactly 3 breakfast options that:
                    - Strictly follow {dietary} dietary restrictions
                    - Have combined cost ≤ ${max_meal_budget:.2f}
                    - Total calories ≤ {max_meal_calories:.0f}kcal
                    - No single meal exceeds ${max_meal_budget/3:.2f}
                    - Use diverse ingredients and cooking methods
                    - Include both hot and cold options
                    - Use diverse protein sources
                    - Use labeled gluten-free or plant-based ingredients where necessary
                    - If constraints conflict, prioritize diet restrictions over cost
                    - Format response as:"""
                    + self.system_message.split("Required format:")[1]
                }]

                response = self.generate_reply(messages)
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if not json_match:
                    return {"error": "No valid JSON found"}
                
                meal_data = json.loads(json_match.group(0))

                if "options" not in meal_data or len(meal_data["options"]) != 3:
                        raise ValueError("Invalid meal options format")
                
                for option in meal_data["options"]:
                        ingredients = ' '.join(option['ingredients']).lower()
                        if any(ing in ingredients for ing in forbidden):
                            raise ValueError(f"Contains {dietary}-forbidden ingredients: {ingredients}")

                # Budget/calorie validation
                total_cost = sum(opt["cost"] for opt in meal_data["options"])
                total_cals = sum(opt["calories"] for opt in meal_data["options"])
                
                if total_cost > max_meal_budget:
                    return {"error": f"Budget exceeded ${max_meal_budget:.2f}"}
                if total_cals > max_meal_calories:
                    return {"error": f"Calories exceeded {max_meal_calories}kcal"}

                meal_data.update({
                    "total_cost": total_cost,
                    "total_calories": total_cals
                })
                return meal_data

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                    attempts += 1
                    if attempts == max_retries:
                        return {
                            "error": f"Failed after {max_retries} attempts: {str(e)}",
                            "suggestion": "Try relaxing constraints or increasing budget"
                        }
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        return {"error": "Exceeded maximum generation attempts"}

