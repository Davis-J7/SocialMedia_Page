import datetime
import os
from flask import Flask, redirect, render_template, request, abort, url_for, flash
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from dotenv import load_dotenv

# 1. Load variables and initialize Flask
load_dotenv()
app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI") + "&tlsAllowInvalidCertificates=true"
app.secret_key = "admin-secret-key"

# 2. Initialize PyMongo
mongo = PyMongo(app)

def get_db():
    return mongo.cx['SocialMediaDB']

def get_user_pipeline(query='', sort_type='name_asc', group_field='category'):
    pipeline = []
    
    # 1. MATCH (Search)
    if query:
        pipeline.append({
            "$match": {
                "$or": [
                    {"name.first": {"$regex": query, "$options": "i"}},
                    {"name.last": {"$regex": query, "$options": "i"}},
                    {"email": {"$regex": query, "$options": "i"}}
                ]
            }
        })
    
    # 2. SORT (Order By)
    sort_config = {"name.first": 1} # Default
    if sort_type == 'name_desc': sort_config = {"name.first": -1}
    elif sort_type == 'newest': sort_config = {"date_of_creation": -1}
    elif sort_type == 'oldest': sort_config = {"date_of_creation": 1}
    pipeline.append({"$sort": sort_config})
    
    # 3. GROUP BY
    if group_field != 'none':
        pipeline.append({
            "$group": {
                "_id": f"${group_field}",
                "users_in_category": {"$push": "$$ROOT"},
                "count": {"$sum": 1}
            }
        })
        pipeline.append({"$sort": {"_id": 1}})
    
    return pipeline

# --- DASHBOARD & USERS ---

@app.route('/')
def index():
    db = get_db()
    sort_type = request.args.get('sort', 'name_asc')
    group_by = request.args.get('group', 'category')
    
    pipeline = get_user_pipeline(sort_type=sort_type, group_field=group_by)
    
    users = []
    grouped_results = []
    
    if group_by != 'none':
        grouped_results = list(db.users.aggregate(pipeline))
        for group in grouped_results:
            users.extend(group['users_in_category'])
    else:
        users = list(db.users.aggregate(pipeline))
    
    # Statistics
    stats = {
        "total_users": db.users.count_documents({}),
        "total_posts": db.posts.count_documents({}),
        "total_messages": db.messages.count_documents({}),
        "total_stories": db.stories.count_documents({})
    }
    
    return render_template('index.html', users=users, stats=stats, 
                           grouped_results=grouped_results, sort=sort_type, group_by=group_by)

@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        # 1. Capture Form Data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        dob_str = request.form.get('dob')
        gender = request.form.get('gender')
        category = request.form.get('category')

        # 2. TRIGGER-LIKE VALIDATION: Minimum Age Requirement (16)
        if dob_str:
            try:
                dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d')
                today = datetime.datetime.utcnow()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                
                if age < 16:
                    flash(f'Validation Error: User must be at least 16 years old (current age: {age}).', 'danger')
                    return render_template('create_user.html')
            except ValueError:
                flash('Invalid date format.', 'danger')
                return render_template('create_user.html')

        # 3. Proceed with Insertion
        db = get_db()
        user_doc = {
            "user_id": "U" + os.urandom(3).hex().upper(),
            "name": {"first": first_name, "last": last_name},
            "email": email,
            "dob": dob_str,
            "gender": gender,
            "category": category,
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
        # Capture form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        dob_str = request.form.get('dob')
        gender = request.form.get('gender')
        category = request.form.get('category')

        # TRIGGER-LIKE VALIDATION: Minimum Age Requirement (16)
        if dob_str:
            try:
                dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d')
                today = datetime.datetime.utcnow()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                
                if age < 16:
                    flash(f'Validation Error: User must be at least 16 years old (current age: {age}).', 'danger')
                    user = db.users.find_one({"_id": obj_id})
                    return render_template('edit_user.html', user=user)
            except ValueError:
                flash('Invalid date format.', 'danger')
                user = db.users.find_one({"_id": obj_id})
                return render_template('edit_user.html', user=user)

        db.users.update_one({"_id": obj_id}, {"$set": {
            "name.first": first_name,
            "name.last": last_name,
            "email": email,
            "dob": dob_str,
            "gender": gender,
            "category": category
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
    
    # OPTIMIZED: Use aggregation pipeline to join users with posts in one go
    pipeline = [
        {"$sort": {"date_of_posting": -1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "author"
            }
        },
        # Unwind the author array (since each post has one author)
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},
        # Add a computed field for the full name
        {
            "$addFields": {
                "user_name": {
                    "$cond": {
                        "if": {"$gt": ["$author", None]},
                        "then": {"$concat": ["$author.name.first", " ", "$author.name.last"]},
                        "else": "Unknown User"
                    }
                }
            }
        }
    ]
    
    posts = list(db.posts.aggregate(pipeline))
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
    
    # ADVANCED AGGREGATION: Resolve both Sender and Receiver in one pipeline
    pipeline = [
        {"$sort": {"time": -1}},
        {
            "$lookup": {
                "from": "users",
                "localField": "sender_id",
                "foreignField": "_id",
                "as": "sender"
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "receiver_id",
                "foreignField": "_id",
                "as": "receiver"
            }
        },
        {"$unwind": {"path": "$sender", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$receiver", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "sender_name": {
                    "$cond": [
                        {"$gt": ["$sender", None]},
                        {"$concat": ["$sender.name.first", " ", "$sender.name.last"]},
                        "Unknown"
                    ]
                },
                "receiver_name": {
                    "$cond": [
                        {"$gt": ["$receiver", None]},
                        {"$concat": ["$receiver.name.first", " ", "$receiver.name.last"]},
                        "Unknown"
                    ]
                }
            }
        }
    ]
    
    messages = list(db.messages.aggregate(pipeline))
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
    sort_type = request.args.get('sort', 'name_asc')
    group_by = request.args.get('group', 'category')
    
    pipeline = get_user_pipeline(query, sort_type, group_by)
    
    users = []
    grouped_results = []
    
    if group_by != 'none':
        grouped_results = list(db.users.aggregate(pipeline))
        for group in grouped_results:
            users.extend(group['users_in_category'])
    else:
        users = list(db.users.aggregate(pipeline))

    stats = {"total_users": len(users), "total_posts": 0, "total_messages": 0, "total_stories": 0}
    return render_template('index.html', users=users, stats=stats, query=query, 
                           grouped_results=grouped_results, sort=sort_type, group_by=group_by)

if __name__ == "__main__":
    # Import and run the seeder automatically
    try:
        from seed import seed_database
        print("--- AUTOMATIC SEEDING STARTING ---")
        seed_database()
        print("--- AUTOMATIC SEEDING COMPLETED ---")
    except ImportError:
        print("Warning: seed.py not found, skipping automatic seeding.")
    except Exception as e:
        print(f"Warning: Automatic seeding failed: {e}")

    app.run(host='0.0.0.0', port=5000, debug=True)
