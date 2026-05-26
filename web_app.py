from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from datetime import datetime
import uuid
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'smart_review_secret_key_2024'

# Database setup
try:
    client = MongoClient('mongodb://localhost:27017/')
    db = client['review_system']
    users_collection = db['users']
    reviews_collection = db['reviews']
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_default_users():
    if not users_collection.find_one({"username": "admin"}):
        users_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "username": "admin",
            "password": hash_password("admin123"),
            "role": "admin",
            "created_at": datetime.now()
        })
        print("✅ Default admin created")
    if not users_collection.find_one({"username": "user"}):
        users_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "username": "user",
            "password": hash_password("user123"),
            "role": "user",
            "created_at": datetime.now()
        })
        print("✅ Default user created")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm_password']
        role = request.form.get('role', 'user')
        
        if users_collection.find_one({"username": username}):
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        
        if password != confirm:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))
        
        users_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "username": username,
            "password": hash_password(password),
            "role": role,
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
        
        user = users_collection.find_one({
            "username": username,
            "password": hash_password(password)
        })
        
        if user:
            session['user_id'] = user['_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_reviews = list(reviews_collection.find().sort("date", -1))
    total_reviews = reviews_collection.count_documents({})
    total_products = len(reviews_collection.distinct("product"))
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         role=session['role'],
                         reviews=all_reviews,
                         total_reviews=total_reviews,
                         total_products=total_products)

@app.route('/add_review', methods=['GET', 'POST'])
def add_review():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        product = request.form['product']
        rating = int(request.form['rating'])
        review_text = request.form['review']
        
        reviews_collection.insert_one({
            "_id": str(uuid.uuid4()),
            "product": product,
            "user": session['username'],
            "user_role": session['role'],
            "rating": rating,
            "review": review_text,
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

@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    search_by = request.args.get('by', 'product')
    
    if query:
        if search_by == 'product':
            results = list(reviews_collection.find({
                "product": {"$regex": query, "$options": "i"}
            }))
        else:
            results = list(reviews_collection.find({
                "user": {"$regex": query, "$options": "i"}
            }))
    else:
        results = []
    
    return render_template('search.html', 
                         reviews=results, 
                         query=query,
                         search_by=search_by)

@app.route('/delete_review/<review_id>')
def delete_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    review = reviews_collection.find_one({"_id": review_id})
    
    if review and (session['role'] == 'admin' or review['user'] == session['username']):
        reviews_collection.delete_one({"_id": review_id})
        flash('🗑️ Review deleted successfully!', 'success')
    else:
        flash('❌ You can only delete your own reviews!', 'error')
    
    return redirect(url_for('view_reviews'))

@app.route('/helpful/<review_id>')
def helpful(review_id):
    reviews_collection.update_one(
        {"_id": review_id},
        {"$inc": {"helpful": 1}}
    )
    flash('👍 Thanks for marking as helpful!', 'success')
    return redirect(request.referrer or url_for('view_reviews'))

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('🔒 Admin access only!', 'error')
        return redirect(url_for('dashboard'))
    
    users = list(users_collection.find())
    stats = {
        'total_users': users_collection.count_documents({}),
        'total_reviews': reviews_collection.count_documents({}),
        'total_products': len(reviews_collection.distinct("product"))
    }
    
    return render_template('admin.html', users=users, stats=stats)

@app.route('/admin/delete_user/<user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    user = users_collection.find_one({"_id": user_id})
    if user and user['username'] != 'admin':
        users_collection.delete_one({"_id": user_id})
        reviews_collection.delete_many({"user": user['username']})
        flash(f'✅ User {user["username"]} deleted!', 'success')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/change_role/<user_id>/<new_role>')
def change_role(user_id, new_role):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    users_collection.update_one(
        {"_id": user_id},
        {"$set": {"role": new_role}}
    )
    flash('👑 User role updated!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 Logged out successfully!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_default_users()
    print("\n" + "="*50)
    print("📝 SMART REVIEW MANAGEMENT SYSTEM STARTING...")
    print("📱 Open: http://127.0.0.1:5000")
    print("="*50)
    app.run(debug=True, host='127.0.0.1', port=5000)