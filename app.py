import datetime
import os
from flask import Flask, redirect, render_template, request, abort, url_for, flash
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

# 1. Load variables and initialize Flask
load_dotenv()
app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.secret_key = "admin-secret-key"

# 2. Initialize PyMongo
mongo = PyMongo(app)

def get_db():
    return mongo.cx['SocialMediaDB']

# --- DASHBOARD & USERS ---

@app.route('/')
def index():
    db = get_db()
    users = list(db.users.find().sort("date_of_creation", -1))
    
    # Statistics
    stats = {
        "total_users": db.users.count_documents({}),
        "total_posts": db.posts.count_documents({}),
        "total_messages": db.messages.count_documents({}),
        "total_stories": db.stories.count_documents({})
    }
    
    return render_template('index.html', users=users, stats=stats)

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        db = get_db()
        user_doc = {
            "user_id": "U" + os.urandom(3).hex().upper(),
            "name": {"first": request.form.get('first_name'), "last": request.form.get('last_name')},
            "email": request.form.get('email'),
            "dob": request.form.get('dob'),
            "gender": request.form.get('gender'),
            "category": request.form.get('category'),
            "date_of_creation": datetime.datetime.utcnow()
        }
        db.users.insert_one(user_doc)
        flash('User created successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('create_user.html')

@app.route('/edit_user/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    db = get_db()
    obj_id = ObjectId(user_id)
    if request.method == 'POST':
        db.users.update_one({"_id": obj_id}, {"$set": {
            "name.first": request.form.get('first_name'),
            "name.last": request.form.get('last_name'),
            "email": request.form.get('email'),
            "dob": request.form.get('dob'),
            "gender": request.form.get('gender'),
            "category": request.form.get('category')
        }})
        flash('User updated successfully!', 'success')
        return redirect(url_for('user_profile', user_hex_id=user_id))
    
    user = db.users.find_one({"_id": obj_id})
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    db = get_db()
    obj_id = ObjectId(user_id)
    db.users.delete_one({"_id": obj_id})
    # Also cleanup their posts and messages for consistency
    db.posts.delete_many({"user_id": obj_id})
    db.messages.delete_many({"$or": [{"sender_id": obj_id}, {"receiver_id": obj_id}]})
    db.stories.delete_many({"user_id": obj_id})
    flash('User and all associated data deleted.', 'success')
    return redirect(url_for('index'))

# --- POSTS ---

@app.route('/posts')
def all_posts():
    db = get_db()
    posts = list(db.posts.find().sort("date_of_posting", -1))
    for post in posts:
        user = db.users.find_one({"_id": post['user_id']})
        post['user_name'] = f"{user['name']['first']} {user['name']['last']}" if user else "Unknown User"
    return render_template('posts.html', posts=posts)

@app.route('/delete_post/<post_id>', methods=['POST'])
def delete_post(post_id):
    db = get_db()
    db.posts.delete_one({"_id": ObjectId(post_id)})
    flash('Post deleted.', 'success')
    return redirect(request.referrer or url_for('all_posts'))

# --- MESSAGES ---

@app.route('/messages')
def all_messages():
    db = get_db()
    messages = list(db.messages.find().sort("time", -1))
    for msg in messages:
        sender = db.users.find_one({"_id": msg['sender_id']})
        receiver = db.users.find_one({"_id": msg['receiver_id']})
        msg['sender_name'] = f"{sender['name']['first']} {sender['name']['last']}" if sender else "Unknown"
        msg['receiver_name'] = f"{receiver['name']['first']} {receiver['name']['last']}" if receiver else "Unknown"
    return render_template('messages.html', messages=messages)

@app.route('/delete_message/<msg_id>', methods=['POST'])
def delete_message(msg_id):
    db = get_db()
    db.messages.delete_one({"_id": ObjectId(msg_id)})
    flash('Message deleted.', 'success')
    return redirect(request.referrer or url_for('all_messages'))

# --- STORIES ---

@app.route('/stories')
def all_stories():
    db = get_db()
    stories = list(db.stories.find().sort("expires_at", -1))
    for story in stories:
        user = db.users.find_one({"_id": story['user_id']})
        story['user_name'] = f"{user['name']['first']} {user['name']['last']}" if user else "Unknown"
    return render_template('stories.html', stories=stories)

@app.route('/delete_story/<story_id>', methods=['POST'])
def delete_story(story_id):
    db = get_db()
    db.stories.delete_one({"_id": ObjectId(story_id)})
    flash('Story deleted.', 'success')
    return redirect(request.referrer or url_for('all_stories'))

# --- PROFILE ---

@app.route('/profile/<user_hex_id>')
def user_profile(user_hex_id):
    db = get_db()
    obj_id = ObjectId(user_hex_id)
    user = db.users.find_one({"_id": obj_id})
    if not user: abort(404)

    posts = list(db.posts.find({"user_id": obj_id}).sort("date_of_posting", -1))
    stories = list(db.stories.find({"user_id": obj_id}))
    messages = list(db.messages.find({"$or": [{"sender_id": obj_id}, {"receiver_id": obj_id}]}).sort("time", -1))
    
    return render_template('profile.html', user=user, posts=posts, stories=stories, messages=messages)

@app.route('/search')
def search():
    db = get_db()
    query = request.args.get('q', '')
    search_filter = {"$or": [
        {"name.first": {"$regex": query, "$options": "i"}},
        {"name.last": {"$regex": query, "$options": "i"}},
        {"email": {"$regex": query, "$options": "i"}}
    ]}
    users = list(db.users.find(search_filter))
    stats = {"total_users": len(users), "total_posts": 0, "total_messages": 0, "total_stories": 0} # Simplified for search
    return render_template('index.html', users=users, stats=stats, query=query)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
