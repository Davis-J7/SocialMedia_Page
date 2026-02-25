import datetime
import os
from functools import wraps
from flask import Flask, redirect, render_template, request, abort, url_for, flash, session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from triggers import validate_content_trigger

# 1. Load variables and initialize Flask
load_dotenv()
app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI") + "&tlsAllowInvalidCertificates=true"
app.secret_key = "admin-secret-key"

# 2. Initialize PyMongo
mongo = PyMongo(app)

def get_db():
    return mongo.cx['SocialMediaDB']

# --- AUTH DECORATORS ---

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role == 'admin' and session.get('role') != 'admin':
                flash('Admin access required.', 'danger')
                return redirect(url_for('user_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- PIPELINES ---

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

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Simple Admin Login
        if email == 'admin@example.com' and password == 'admin123':
            session['user_id'] = 'admin'
            session['role'] = 'admin'
            session['user_name'] = 'Admin'
            return redirect(url_for('index'))
        
        # User Login
        db = get_db()
        user = db.users.find_one({"email": email, "password": password})
        if user:
            session['user_id'] = str(user['_id'])
            session['role'] = 'user'
            session['user_name'] = f"{user['name']['first']} {user['name']['last']}"
            return redirect(url_for('user_dashboard'))
        
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        dob_str = request.form.get('dob')
        gender = request.form.get('gender')
        
        # Age Validation
        if dob_str:
            dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d')
            today = datetime.datetime.utcnow()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 16:
                flash('You must be at least 16 years old to register.', 'danger')
                return render_template('register.html')
        
        db = get_db()
        if db.users.find_one({"email": email}):
            flash('Email already registered.', 'danger')
            return render_template('register.html')
            
        user_doc = {
            "user_id": "U" + os.urandom(3).hex().upper(),
            "name": {"first": first_name, "last": last_name},
            "email": email,
            "password": password,
            "dob": dob_str,
            "gender": gender,
            "category": "Regular User",
            "date_of_creation": datetime.datetime.utcnow()
        }
        db.users.insert_one(user_doc)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

# --- USER ROUTES ---

@app.route('/user/dashboard')
@login_required(role='user')
def user_dashboard():
    db = get_db()
    user_id = ObjectId(session['user_id'])
    
    posts = list(db.posts.find({"user_id": user_id}).sort("date_of_posting", -1))
    stories = list(db.stories.find({"user_id": user_id}).sort("created_at", -1))
    
    # Received Messages
    messages = list(db.messages.aggregate([
        {"$match": {"receiver_id": user_id}},
        {"$sort": {"time": -1}},
        {"$lookup": {
            "from": "users",
            "localField": "sender_id",
            "foreignField": "_id",
            "as": "sender"
        }},
        {"$unwind": "$sender"}
    ]))
    
    return render_template('user_dashboard.html', posts=posts, stories=stories, messages=messages)

@app.route('/user/create_post', methods=['POST'])
@login_required(role='user')
def user_create_post():
    db = get_db()
    content = request.form.get('content')
    media_type = request.form.get('media_type', 'Text')
    privacy = request.form.get('privacy', 'Everyone')
    
    # TRIGGER: Content Moderation
    is_valid, error_msg = validate_content_trigger(content)
    if not is_valid:
        flash(error_msg, 'danger')
        return redirect(url_for('user_dashboard'))
    
    post_doc = {
        "post_id": "P" + os.urandom(2).hex().upper(),
        "user_id": ObjectId(session['user_id']),
        "content": {
            "media_type": media_type,
            "text": content,
            "audio": "None"
        },
        "permissions": {
            "permission_name": "Public",
            "accessibility": privacy
        },
        "date_of_posting": datetime.datetime.utcnow()
    }
    db.posts.insert_one(post_doc)
    flash('Post created!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/create_story', methods=['POST'])
@login_required(role='user')
def user_create_story():
    db = get_db()
    media_type = request.form.get('media_type', 'Image')
    
    story_doc = {
        "story_id": "S" + os.urandom(2).hex().upper(),
        "user_id": ObjectId(session['user_id']),
        "media": {
            "type": media_type,
            "audio_type": "Stereo",
            "length": 15
        },
        "created_at": datetime.datetime.utcnow(),
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    db.stories.insert_one(story_doc)
    flash('Story created!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/send_message', methods=['POST'])
@login_required(role='user')
def user_send_message():
    db = get_db()
    receiver_email = request.form.get('receiver_email')
    content = request.form.get('content')
    
    # TRIGGER: Content Moderation
    is_valid, error_msg = validate_content_trigger(content)
    if not is_valid:
        flash(error_msg, 'danger')
        return redirect(url_for('user_dashboard'))
        
    receiver = db.users.find_one({"email": receiver_email})
    if not receiver:
        flash('User not found.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    msg_doc = {
        "message_id": "M" + os.urandom(2).hex().upper(),
        "sender_id": ObjectId(session['user_id']),
        "receiver_id": receiver['_id'],
        "content": content,
        "type": "Text",
        "status": "Delivered",
        "time": datetime.datetime.utcnow()
    }
    db.messages.insert_one(msg_doc)
    flash('Message sent!', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/update_post_privacy/<post_id>', methods=['POST'])
@login_required(role='user')
def update_post_privacy(post_id):
    db = get_db()
    privacy = request.form.get('privacy')
    db.posts.update_one(
        {"_id": ObjectId(post_id), "user_id": ObjectId(session['user_id'])},
        {"$set": {"permissions.accessibility": privacy}}
    )
    flash('Privacy updated.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/delete_post/<post_id>', methods=['POST'])
@login_required(role='user')
def user_delete_post(post_id):
    db = get_db()
    db.posts.delete_one({"_id": ObjectId(post_id), "user_id": ObjectId(session['user_id'])})
    flash('Post deleted.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/delete_story/<story_id>', methods=['POST'])
@login_required(role='user')
def user_delete_story(story_id):
    db = get_db()
    db.stories.delete_one({"_id": ObjectId(story_id), "user_id": ObjectId(session['user_id'])})
    flash('Story deleted.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/delete_message/<msg_id>', methods=['POST'])
@login_required(role='user')
def user_delete_message(msg_id):
    db = get_db()
    # Users can delete messages they sent OR received
    user_id = ObjectId(session['user_id'])
    db.messages.delete_one({
        "_id": ObjectId(msg_id),
        "$or": [{"sender_id": user_id}, {"receiver_id": user_id}]
    })
    flash('Message deleted.', 'success')
    return redirect(url_for('user_dashboard'))

# --- DASHBOARD & USERS ---

@app.route('/')
@login_required(role='admin')
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

@app.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@login_required(role='admin')
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
@login_required(role='admin')
def delete_user(user_id):
    db = get_db()
    obj_id = ObjectId(user_id)
    db.users.delete_one({"_id": obj_id})
    
    db.posts.delete_many({"user_id": obj_id})
    db.messages.delete_many({"$or": [{"sender_id": obj_id}, {"receiver_id": obj_id}]})
    db.stories.delete_many({"user_id": obj_id})
    flash('User and all associated data deleted.', 'success')
    return redirect(url_for('index'))

# --- POSTS ---

@app.route('/posts')
@login_required(role='admin')
def all_posts():
    db = get_db()
    
    # Aggregation for counts by media type
    stats_pipeline = [
        {"$group": {"_id": "$content.media_type", "count": {"$sum": 1}}}
    ]
    type_stats = list(db.posts.aggregate(stats_pipeline))
    total_count = db.posts.count_documents({})

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
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},
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
    return render_template('posts.html', posts=posts, total_count=total_count, type_stats=type_stats)

@app.route('/delete_post/<post_id>', methods=['POST'])
@login_required(role='admin')
def delete_post(post_id):
    db = get_db()
    db.posts.delete_one({"_id": ObjectId(post_id)})
    flash('Post deleted.', 'success')
    return redirect(request.referrer or url_for('all_posts'))

# --- MESSAGES ---

@app.route('/messages')
@login_required(role='admin')
def all_messages():
    db = get_db()
    
    # Aggregation for counts by status
    stats_pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_stats = list(db.messages.aggregate(stats_pipeline))
    total_count = db.messages.count_documents({})

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
    return render_template('messages.html', messages=messages, total_count=total_count, status_stats=status_stats)

@app.route('/delete_message/<msg_id>', methods=['POST'])
@login_required(role='admin')
def delete_message(msg_id):
    db = get_db()
    db.messages.delete_one({"_id": ObjectId(msg_id)})
    flash('Message deleted.', 'success')
    return redirect(request.referrer or url_for('all_messages'))

# --- STORIES ---

@app.route('/stories')
@login_required(role='admin')
def all_stories():
    db = get_db()
    
    # Aggregation for counts by type
    stats_pipeline = [
        {"$group": {"_id": "$media.type", "count": {"$sum": 1}}}
    ]
    type_stats = list(db.stories.aggregate(stats_pipeline))
    total_count = db.stories.count_documents({})

    stories = list(db.stories.find().sort("expires_at", -1))
    for story in stories:
        user = db.users.find_one({"_id": story['user_id']})
        story['user_name'] = f"{user['name']['first']} {user['name']['last']}" if user else "Unknown"
    
    return render_template('stories.html', stories=stories, total_count=total_count, type_stats=type_stats)

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

# --- DAILY STATISTICS ---

@app.route('/daily_stats')
def daily_stats():
    db = get_db()
    date_str = request.args.get('date', datetime.datetime.utcnow().strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        end_date = start_date + datetime.timedelta(days=1)
    except ValueError:
        flash('Invalid date format. Using today instead.', 'warning')
        start_date = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + datetime.timedelta(days=1)
        date_str = start_date.strftime('%Y-%m-%d')

    # 1. Counts for messages, stories, and posts
    post_count = db.posts.count_documents({"date_of_posting": {"$gte": start_date, "$lt": end_date}})
    message_count = db.messages.count_documents({"time": {"$gte": start_date, "$lt": end_date}})
    story_count = db.stories.count_documents({"created_at": {"$gte": start_date, "$lt": end_date}})

    # 2. Users who posted the most that day (Group By + Sort)
    top_posters_pipeline = [
        {"$match": {"date_of_posting": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
        {"$lookup": {
            "from": "users",
            "localField": "_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$unwind": "$user"}
    ]
    top_posters = list(db.posts.aggregate(top_posters_pipeline))

    # 3. List of posts ordered (Order By)
    posts_list_pipeline = [
        {"$match": {"date_of_posting": {"$gte": start_date, "$lt": end_date}}},
        {"$sort": {"date_of_posting": -1}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "author"
        }},
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}}
    ]
    posts_list = list(db.posts.aggregate(posts_list_pipeline))

    # 4. Posts grouped by type (Group By)
    posts_by_type_pipeline = [
        {"$match": {"date_of_posting": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": "$content.media_type", "count": {"$sum": 1}}}
    ]
    posts_by_type = list(db.posts.aggregate(posts_by_type_pipeline))

    return render_template('daily_stats.html', 
                           date=date_str,
                           post_count=post_count,
                           message_count=message_count,
                           story_count=story_count,
                           top_posters=top_posters,
                           posts_list=posts_list,
                           posts_by_type=posts_by_type)

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
