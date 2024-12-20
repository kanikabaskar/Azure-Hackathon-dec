from flask import Flask, render_template, redirect, url_for
import os

app = Flask(__name__)

# Route for the homepage in GenSearch
@app.route('/', endpoint="home")
def index():
    return render_template('index.html')

# Route for the login page
@app.route('/login')
def login():
    return render_template('login.html')

# Route for the signup page
@app.route('/signup')
def signup():
    return render_template('signup.html')

# Route for Project1's homepage (connecting to Project1)
@app.route('/Project1')
def Project1():
    return redirect("http://localhost:5001/")  

if __name__ == '__main__':
    app.run(debug=True,port=5000)
