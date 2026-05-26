from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from datetime import datetime
import uuid
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_2024'

# MongoDB Connection
try:
    client = MongoClient('mongodb://localhost:27017/')
    db = client['review_system']
    users_collection = db['users']
    reviews_collection = db['reviews']
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Create default admin and user if not exists
def init_db():
    if not users_collection.find_one({"username": "admin"}):
        users_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "username": "admin",
            "password": hash_password("admin123"),
            "role": "admin"
        })
        print("✅ Admin created (admin/admin123)")
    
    if not users_collection.find_one({"username": "user"}):
        users_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "username": "user",
            "password": hash_password("user123"),
            "role": "user"
        })
        print("✅ Demo user created (user/user123)")

init_db()

# ============== ROUTES ==============

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if users_collection.find_one({"username": username}):
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        
        if password != confirm:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters!', 'error')
            return redirect(url_for('register'))
        
        users_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "username": username,
            "password": hash_password(password),
            "role": "user",
            "created_at": datetime.now()
        })
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_role = request.form.get('role', 'user')
        
        user = users_collection.find_one({
            "username": username,
            "password": hash_password(password)
        })
        
        if user:
            if selected_role == 'admin' and user['role'] != 'admin':
                flash('❌ This account is not an admin account!', 'error')
                return redirect(url_for('login'))
            
            session['user_id'] = user['_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'💖 Welcome back, {username}!', 'success')
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid credentials!', 'error')
    
    return render_template('login.html')

# SIMPLE FORGOT PASSWORD - Direct HTML without Jinja2 issues
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    message_type = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not username:
            message = 'Please enter username!'
            message_type = 'error'
        elif not users_collection.find_one({"username": username}):
            message = 'No account found with this username!'
            message_type = 'error'
        elif not new_password or not confirm_password:
            message = 'Please enter new password!'
            message_type = 'error'
        elif new_password != confirm_password:
            message = 'Passwords do not match!'
            message_type = 'error'
        elif len(new_password) < 8:
            message = 'Password must be at least 8 characters!'
            message_type = 'error'
        else:
            # Update password
            users_collection.update_one(
                {"username": username},
                {"$set": {"password": hash_password(new_password)}}
            )
            message = '✅ Password reset successful! Please login with your new password.'
            message_type = 'success'
            return redirect(url_for('login'))
    
    # Return HTML directly
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Forgot Password - Makeup Review System</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #E8D5F5 0%, #D8F0E8 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .container {{
                background: white;
                border-radius: 35px;
                padding: 45px;
                width: 90%;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 25px 50px rgba(0,0,0,0.1);
            }}
            h2 {{ color: #6B4B8B; margin-bottom: 10px; }}
            .subtitle {{ color: #9B7BB5; margin-bottom: 30px; font-size: 0.9em; }}
            .form-group {{ margin-bottom: 20px; text-align: left; }}
            label {{ display: block; margin-bottom: 8px; color: #7B5B9B; font-weight: 600; }}
            input {{
                width: 100%;
                padding: 14px;
                border: 2px solid #E8D5F5;
                border-radius: 25px;
                font-size: 14px;
                transition: all 0.3s;
            }}
            input:focus {{
                outline: none;
                border-color: #9B7BB5;
                box-shadow: 0 0 0 3px rgba(155, 123, 181, 0.2);
            }}
            button {{
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #9B7BB5 0%, #7B5B9B 100%);
                color: white;
                border: none;
                border-radius: 50px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin-top: 10px;
                transition: all 0.3s;
            }}
            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(155, 123, 181, 0.4);
            }}
            .flash {{
                padding: 12px;
                border-radius: 20px;
                margin-bottom: 20px;
                font-size: 14px;
            }}
            .flash.success {{
                background: #D8F0E8;
                color: #4A8B7A;
                border-left: 4px solid #4A8B7A;
            }}
            .flash.error {{
                background: #FFE4E4;
                color: #D46B6B;
                border-left: 4px solid #D46B6B;
            }}
            .back-link {{
                text-align: center;
                margin-top: 20px;
            }}
            .back-link a {{
                color: #7B5B9B;
                text-decoration: none;
            }}
            .back-link a:hover {{
                text-decoration: underline;
            }}
            .hint {{
                font-size: 0.75em;
                color: #9B7BB5;
                margin-top: 5px;
            }}
            .logo {{ font-size: 55px; margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">💜🔐</div>
            <h2>Reset Password</h2>
            <p class="subtitle">Enter your username and new password</p>
            
            {f'<div class="flash {message_type}">{message}</div>' if message else ''}
            
            <form method="POST">
                <div class="form-group">
                    <label>👤 Username</label>
                    <input type="text" name="username" placeholder="Enter your username" required>
                </div>
                <div class="form-group">
                    <label>🔒 New Password</label>
                    <input type="password" name="new_password" placeholder="Enter new password" required>
                    <div class="hint">🔐 Minimum 8 characters</div>
                </div>
                <div class="form-group">
                    <label>✓ Confirm Password</label>
                    <input type="password" name="confirm_password" placeholder="Confirm new password" required>
                </div>
                <button type="submit">💖 Reset Password 💜</button>
            </form>
            
            <div class="back-link">
                <a href="/login">← Back to Login</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    reviews = list(reviews_collection.find().sort("date", -1))
    return render_template('dashboard.html', 
                         username=session['username'],
                         role=session['role'],
                         reviews=reviews)

@app.route('/add_review', methods=['GET', 'POST'])
def add_review():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        product = request.form['product']
        rating_value = request.form['rating']
        rating = int(float(rating_value))
        review_text = request.form['review']
        
        file_url = None
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename:
                if not os.path.exists('static/uploads'):
                    os.makedirs('static/uploads')
                filename = f"{uuid.uuid4().hex}_{file.filename}"
                file.save(os.path.join('static/uploads', filename))
                file_url = f"/static/uploads/{filename}"
        
        reviews_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "product": product,
            "user": session['username'],
            "rating": rating,
            "review": review_text,
            "file_url": file_url,
            "date": datetime.now(),
            "helpful": 0
        })
        flash('✅ Review added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_review.html')

@app.route('/view_reviews')
def view_reviews():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_reviews = list(reviews_collection.find().sort("date", -1))
    return render_template('view_reviews.html', 
                         reviews=all_reviews,
                         role=session['role'],
                         username=session['username'])

@app.route('/delete_review/<review_id>')
def delete_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    review = reviews_collection.find_one({"_id": review_id})
    
    if review and (session['role'] == 'admin' or review['user'] == session['username']):
        reviews_collection.delete_one({"_id": review_id})
        flash('🗑️ Review deleted!', 'success')
    else:
        flash('❌ Cannot delete this review!', 'error')
    
    return redirect(url_for('view_reviews'))

@app.route('/helpful/<review_id>')
def helpful(review_id):
    reviews_collection.update_one(
        {"_id": review_id},
        {"$inc": {"helpful": 1}}
    )
    flash('👍 Thanks for marking helpful!', 'success')
    return redirect(request.referrer or url_for('view_reviews'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Admin access only!', 'error')
        return redirect(url_for('dashboard'))
    
    all_reviews = list(reviews_collection.find().sort("date", -1))
    all_users = list(users_collection.find())
    return render_template('admin_dashboard.html', 
                         reviews=all_reviews,
                         users=all_users,
                         username=session['username'])

@app.route('/admin/delete_user/<user_id>')
def admin_delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    user = users_collection.find_one({"_id": user_id})
    if user and user['username'] not in ['admin']:
        reviews_collection.delete_many({"user": user['username']})
        users_collection.delete_one({"_id": user_id})
        flash(f'✅ User {user["username"]} deleted!', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    
    print("\n" + "="*50)
    print("💜 MAKEUP REVIEW MANAGEMENT SYSTEM")
    print("🌐 http://127.0.0.1:5000")
    print("="*50)
    app.run(debug=True, port=5000)