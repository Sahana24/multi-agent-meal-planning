def validate_budget(meal_cost: float, remaining_budget: float) -> dict:
    """Validates if a meal cost fits within remaining budget."""
    if meal_cost <= remaining_budget:
        return {
            "approved": True,
            "remaining_budget": remaining_budget - meal_cost,
            "message": f"Budget approved. ${remaining_budget - meal_cost:.2f} remaining"
        }
    return {
        "approved": False,
        "deficit": meal_cost - remaining_budget,
        "message": f"Exceeds budget by ${meal_cost - remaining_budget:.2f}",
        "remaining_budget": remaining_budget  
    }