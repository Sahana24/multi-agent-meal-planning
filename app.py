from flask import Flask, render_template, request, jsonify, session
from agents.breakfast_agent import BreakfastAgent
from agents.lunch_agent import LunchAgent
from agents.dinner_agent import DinnerAgent
from agents.snack_agent import SnackAgent
from agents.budget_agent import BudgetAgent
from agents.shopping_list_agent import ShoppingListAgent
from dotenv import load_dotenv
import os
import autogen
import json

load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session

# Groq configuration
config_list = [
    {
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY"),
        "temperature": 0.3,
        "max_tokens": 1024,
        "timeout": 120
    }
]

def initialize_agents(user_budget):
    """Initialize all agents with shared configuration"""
    return {
        "budget": BudgetAgent(config_list, user_budget),
        "breakfast": BreakfastAgent(),
        "lunch": LunchAgent(),
        "dinner": DinnerAgent(),
        "snacks": SnackAgent(),
        "shopping": ShoppingListAgent()
    }

@app.route('/', methods=['GET', 'POST'])
def meal_planner():
    if request.method == 'POST':
        try:
            user_data = {
                "dietary": request.form.get('dietary', 'none'),
                "budget": float(request.form.get('budget', 30.0)),
                "calories": int(request.form.get('calories', 2000)),
                "time": request.form.get('time', '30 mins')
            }
            
            agents = initialize_agents(user_data["budget"])
            meal_plan = run_meal_planning(agents, user_data)
            
            # Store meal plan in session for shopping list access
            session['meal_plan'] = json.dumps(meal_plan)
            
            # Generate shopping list
            shopping_list = agents["shopping"].generate_shopping_list(meal_plan)
            
            # Debug print (remove in production)
            print("Meal Plan Data:", meal_plan)
            print("Shopping List:", shopping_list)
            
            return render_template('index.html', 
                                result=meal_plan,
                                shopping_list=shopping_list,
                                remaining_budget=meal_plan.get('remaining_budget', 0))

        except Exception as e:
            print(f"Error in meal_planner: {str(e)}")  # Debug print
            return render_template('index.html', 
                                error=f"Planning failed: {str(e)}")
    
    # Clear results on GET request
    return render_template('index.html', result=None, error=None)

@app.route('/shopping-list', methods=['GET'])
def view_shopping_list():
    """View the shopping list in a dedicated page"""
    try:
        # Get the meal plan from session
        meal_plan_json = session.get('meal_plan')
        if not meal_plan_json:
            return render_template('shopping_list.html', error="No meal plan found")
        
        meal_plan = json.loads(meal_plan_json)
        agents = initialize_agents(0)  # Budget not needed for shopping list
        shopping_list = agents["shopping"].generate_shopping_list(meal_plan)
        
        return render_template('shopping_list.html', 
                             shopping_list=shopping_list)
    except Exception as e:
        print(f"Error in view_shopping_list: {str(e)}")  # Debug print
        return render_template('shopping_list.html', 
                             error=f"Failed to generate shopping list: {str(e)}")

def run_meal_planning(agents: dict, user_data: dict) -> dict:
    """Orchestrate meal planning workflow"""
    meal_plan = {}
    remaining_budget = user_data["budget"]
    
    # Process meals in sequence
    for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
        agent = agents[meal_type]
        response = agent.generate_suggestions(user_data, agents["budget"])        
        if "error" in response:
            meal_plan[meal_type] = response  # Store error but continue
            continue
        
        budget_check = agents["budget"].validate_meal_cost(response.get("total_cost", 0))
        
        if budget_check["status"] == "approved":
            meal_plan[meal_type] = response
            remaining_budget = budget_check["remaining_budget"]
        else:
            meal_plan[meal_type] = {"error": budget_check["message"]}
    
    meal_plan["remaining_budget"] = remaining_budget
    return meal_plan

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)