from autogen import AssistantAgent
from tools.budget_checker import validate_budget

class BudgetAgent(AssistantAgent):
    def __init__(self, config_list, initial_budget):
        super().__init__(
            name="BudgetAgent",
            system_message="""
            You are a financial constraint validator. Your responsibilities:
            1. Verify meal costs against remaining budget
            2. Provide cost adjustment suggestions
            3. Track cumulative daily expenses
            """,
            llm_config={"config_list": config_list},
        )
        self.remaining_budget = initial_budget
        
    def validate_meal_cost(self, meal_cost: float) -> dict:
        result = validate_budget(meal_cost, self.remaining_budget)
        if result["approved"]:
            self.remaining_budget = result["remaining_budget"]
        return {
            "status": "approved" if result["approved"] else "denied",
            "message": result["message"],
            "remaining_budget": self.remaining_budget
        }