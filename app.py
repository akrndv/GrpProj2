from flask import Flask, render_template, request, session, redirect, url_for, flash
import bcrypt
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import google.generativeai as genai
import os

# to add database stuff pls

app = Flask(__name__)
app.secret_key = "secret"
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

api = os.getenv("MAKERSUITE_API_TOKEN")
genai.configure(api_key=api)
model = genai.GenerativeModel("gemini-1.5-flash")

users = {}

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password").encode('utf-8')
        for user, data in users.items():
            if data['name'] == username:
                if bcrypt.checkpw(password, data['password']):
                    session['username'] = user
                    return redirect(url_for('dashboard'))
                else:
                    return render_template("login.html", error="Incorrect password")
        return render_template("login.html", error="Username not found")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if any(user['name'] == username for user in users.values()):
            return render_template("register.html", error="Username already exists")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        # Store user data
        users[username] = {
            'name': username,
            'email': '',
            'password': hashed_password,
            'plain_password': password  # Store the plain text password
        }
        session['username'] = username  
        return redirect(url_for('login'))
    return render_template("register.html")


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    username = session.get('username')

    if username in users:
        display_name = users[username]['name']
        return render_template("dashboard.html", username=display_name) 
    return redirect(url_for('login'))

@app.route("/profile", methods=['GET', 'POST'])
def profile():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "User Profile", "url": "/profile"}
    ]

    username = session.get('username')
    
    if request.method == 'POST':
        new_name = request.form.get('name')
        new_email = request.form.get('email')
        new_password = request.form.get('password')

        if new_name:
            old_name = users[username]['name']
            users[username]['name'] = new_name
            # Update all references to the old name
            for user, data in users.items():
                if data['name'] == old_name:
                    data['name'] = new_name
        if new_email:
            users[username]['email'] = new_email
        if new_password:
            # Update both the hashed and plain text password
            users[username]['password'] = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            users[username]['plain_password'] = new_password
        
        flash('Profile updated successfully!', 'success')

    user = users[username]
    display_name = users[session.get('username')]['name']
    return render_template("profile.html", breadcrumbs=breadcrumbs, user=user, username=display_name)

@app.route("/transfer",methods=["GET","POST"])
def transfer():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Money Transfer", "url": "/transfer"}
    ]
    display_name = users[session.get('username')]['name']
    return (render_template("transfer.html", breadcrumbs=breadcrumbs, username=display_name))

@app.route("/expense", methods=["GET", "POST"])
def expSum():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Expense Summary", "url": "/expSum"}
    ]

    display_name = users[session.get('username')]['name']

    expenses = session.get('expenses', {})
    
    # Initialize total expenses
    total_expenses = 0
    
    # Check if expenses is a dictionary
    if isinstance(expenses, dict):
        for date, categories in expenses.items():
            # Check if categories is a dictionary
            if isinstance(categories, dict):
                # Sum up only valid numeric amounts
                total_expenses += sum(amount for amount in categories.values() if isinstance(amount, (int, float)))
            else:
                print(f"Warning: Expected a dict for categories but got {type(categories)} for date {date}")

    return render_template("expSum.html", breadcrumbs=breadcrumbs, username=display_name, expenses=expenses, total_expenses=total_expenses)

@app.route("/add", methods=["GET", "POST"])
def add():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Expense Summary", "url": "/expSum"},
        {"name": "Add Expense", "url": "/add"}
    ]
    display_name = users[session.get('username')]['name']

    if request.method == 'POST':
        # Get data from the form
        category = request.form.get('category')  # Safely get the category field
        amount = request.form.get('amount')  # Safely get the amount field
        date = request.form.get('date')

        if not category or not amount or not date:
            return "Category, amount, or date missing!", 400

        try:
            amount = float(amount)
        except ValueError:
            return "Invalid amount!", 400

        # Initialize session if not already done
        if 'expenses' not in session:
            session['expenses'] = {}
        
        if date not in session['expenses']:
            session['expenses'][date] = {}

        # Update the expenses in session
        if category in session['expenses'][date]:
            session['expenses'][date][category] += amount
        else:
            session['expenses'][date][category] = amount

        return redirect(url_for('expSum'))

    return render_template("expAdd.html", breadcrumbs=breadcrumbs, username=display_name)

@app.route('/budget', methods=["GET", 'POST'])
def budget():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Budgeting", "url": "/budget"}
    ]
    display_name = users[session.get('username')]['name']

    if 'expenses' not in session:
        session['expenses'] = {}
    return render_template('budget.html', breadcrumbs=breadcrumbs, username=display_name, expenses=session['expenses'])

@app.route('/calculate_budget', methods=['POST'])
def calculate_budget():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Budgeting", "url": "/budget"},
        {"name": "Budgeting Advice", "url": "/calculate_budget"},
    ]
    display_name = users[session.get('username')]['name']

    # Get monthly budget from the form
    monthly_budget = float(request.form.get('monthly_budget', 0))
    expenses = session.get('expenses', {})

    # Calculate total expenses and remaining budget
    total_spent = sum(amount for daily in expenses.values() for amount in daily.values())
    remaining_budget = monthly_budget - total_spent

    if remaining_budget < 0:
        status = "You're over budget."
    elif remaining_budget > monthly_budget * 0.5:
        status = "Good budgeting! Consider saving some funds for future goals."
    else:
        status = "You're within budget."

    # Generate advice with AI
    today = datetime.today()
    end_of_month = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
    days_remaining = (end_of_month-today).days
    

    q = (
        f"I have a monthly budget of ${monthly_budget} and expenses totaling ${total_spent}. "
        f"My expenses are {expenses}. There are {days_remaining} days left in the month. "
        f"Can you provide me with 5 pieces of advice on how to manage my budget based on my expenses?"
    )
    
    r = model.generate_content(q)
    formatted_r = r.text.replace("*", "").replace("\n", "<br>")

    return render_template('budget_advice.html', breadcrumbs=breadcrumbs, username=display_name, total_spent=total_spent, remaining_budget=remaining_budget, status= status, advice=formatted_r)

@app.route("/goal", methods=["GET", "POST"])
def goal():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Goal", "url": "/goal"}
    ]
    display_name = users[session.get('username')]['name']
    return render_template("goal.html",breadcrumbs=breadcrumbs,username=display_name)

@app.route("/goal_advice",methods=["GET","POST"])
def goal_advice():
    breadcrumbs = [
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Goal", "url": "/goal"},
        {"name": "Goal Advice", "url": "/goal_advice"}
    ]
    display_name = users[session.get('username')]['name']
        
    balance = request.form.get("balance", 0)
    retirementGoal = request.form.get("retirementGoal", 0)
    targetYear1 = request.form.get("targetYear1")

    q = (
        f"I have a bank account balance of ${balance} and a retirement goal of ${retirementGoal}. "
        f"I want to achieve this by the year {targetYear1}. Can you provide me with advice on how to reach this goal, "
        f"including potential investment strategies and budgeting tips?"
    )

    r = model.generate_content(q)
    formatted_r = r.text.replace("*", "").replace("\n", "<br>")
    return(render_template("goal_advice.html",breadcrumbs=breadcrumbs,username=display_name, r=formatted_r))


@app.route("/invest", methods = ["GET", "POST"])
def investment_dashboard():
    breadcrumbs = [
    {"name": "Dashboard", "url": "/dashboard"},
    {"name": "Investing", "url": "/invest"}
    ]
    display_name = users[session.get('username')]['name']

    investment_options = [
        {"type": "Stocks", "description": "Equity investments with high growth potential."},
        {"type": "Bonds", "description": "Debt securities with stable returns."},
        {"type": "Mutual Funds", "description": "Pooled investments managed by professionals."},
        {"type": "Real Estate", "description": "Property investments for steady cash flow."},
        {"type": "Commodities", "description": "Invest in resources like gold and oil."},
    ]

    return render_template("invest.html", breadcrumbs=breadcrumbs, username=display_name, investment_options=investment_options)

@app.route("/investment_advice", methods = ["GET", "POST"])
def investment_advice():
    breadcrumbs = [
    {"name": "Dashboard", "url": "/dashboard"},
    {"name": "Investing", "url": "/invest"},
    {"name": "Investment Advice", "url": "/investment_advice"}
    ]
    display_name = users[session.get('username')]['name']
    
    if request.method == "POST":
        #User inputs
        risk_level = request.form.get("risk_level")
        investment_amount = request.form.get("investment_amount")
        time_horizon = request.form.get("time_horizon")

        q = (
            f"I have an investment amount of ${investment_amount} with a {risk_level} risk tolerance and a time horizon of {time_horizon} years."
            "Please provide advice on how to allocate this investment in stocks, bonds, and other assets."
        )

        r = model.generate_content(q)
        formatted_r = r.generated_text.replace("*", "").replace("\n", "<br>")

        return render_template("investment_advSum.html", username=display_name, advice = formatted_r)
    
    return render_template("investment_advice.html", breadcrumbs=breadcrumbs, username=display_name, advice=None)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run()
