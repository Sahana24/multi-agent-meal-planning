from autogen import AssistantAgent
from config import groq_config
import json
import re

class SnackAgent(AssistantAgent):
    def __init__(self):
        super().__init__(
            name="SnackAgent",
            system_message=f"""
                You are a snack optimization AI. Your responsibilities:
                1. Suggest a set number of healthy snacks matching dietary needs.
                2. Ensure each snack falls within a reasonable calorie range.
                3. Ensure snacks complement daily nutrition and dietary goals.
                4. Validate affordability using BudgetCheckerTool.

                Required format:
                {{
                    "options": [
                        {{
                            "name": "string (e.g., 'Greek Yogurt Parfait')",
                            "description": "string (brief snack description)",
                            "calories": "integer (e.g., 100-300)",
                            "cost": "float (e.g., 1.25)",
                            "prep_time": "string (e.g., '5 mins')",
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
                    "content": f"""Create exactly 3 snack options that:
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

    def reduce_meal_cost(self, meal, available_budget):
        """Attempt cost reduction through portion scaling"""
        original_cost = meal["cost"]
        if original_cost <= 0:
            return None
            
        max_scale = min(0.5, available_budget / original_cost)
        if max_scale >= 0.7: 
            scaled_cost = original_cost * max_scale
            meal["description"] += f" (portion reduced by {int((1-max_scale)*100)}%)"
            return scaled_cost
        return None
        
    def adjust_meal_plan(self, meal_data, budget_agent):
        """Adjusts meal plan to fit within budget."""
        try:            
            meal_data["options"].sort(key=lambda x: x["cost"], reverse=True)

            while sum(option["cost"] for option in meal_data["options"]) > budget_agent.remaining_budget:
                if len(meal_data["options"]) > 1:
                    meal_data["options"].pop(0)  
                else:
                    
                    meal_data["options"][0]["cost"] *= 0.9              
            total_cost = sum(option["cost"] for option in meal_data["options"])
            budget_check = budget_agent.validate_meal_cost(total_cost)            
            if budget_check["status"] == "approved":
                meal_data["total_cost"] = total_cost
                meal_data["budget_check"] = budget_check
                return meal_data
            return None
        except Exception as e:
            return {"error": f"{self.name} adjustment error: {str(e)}"}
