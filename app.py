from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import bcrypt
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
import os

api = os.getenv("MAKERSUITE_API_TOKEN")
genai.configure(api_key=api)
model = genai.GenerativeModel("gemini-1.5-flash")

users = {}

app = Flask(__name__)

app.secret_key = 'its_a_secret'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password").encode('utf-8')
        for user, data in users.items():
            if data['name'] == username:
                if bcrypt.checkpw(password, data['password']):
                    session['username'] = user
                    return redirect(url_for('index'))
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

@app.route("/index", methods=['GET', 'POST'])
def index():
    username = session.get('username')

    if username in users:
        display_name = users[username]['name']
        return render_template("index.html", username=display_name) 
    return redirect(url_for('login'))

@app.route("/transfer",methods=["GET","POST"])
def transfer():
    return(render_template("transfer.html"))

@app.route("/expense", methods=["GET", "POST"])
def expense():
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

        return redirect(url_for('summary'))

    return render_template("expense.html")

@app.route("/summary", methods=["GET", "POST"])
def summary():
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

    return render_template("summary.html", expenses=expenses, total_expenses=total_expenses)

@app.route("/profile", methods=['GET', 'POST'])
def profile():
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
    return render_template("profile.html", user=user)

@app.route("/goal", methods=["GET", "POST"])
def goal():
    return render_template("goal.html")

@app.route("/goal_advice",methods=["GET","POST"])
def goal_advice():
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
    return(render_template("goal_advice.html",r=formatted_r))

@app.route("/logout", methods=["POST"])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
