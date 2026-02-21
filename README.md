# 🌐 SocialMedia Admin Dashboard

A modern, sleek, and functional administrative interface for managing a MongoDB-backed social media platform. Built with **Flask** and **Flask-PyMongo**, this application provides full CRUD capabilities, global activity logs, and system-wide statistics.

---

## 🚀 Features

### 🛠 Administrative Control
- **User Management**: Create, search, edit, and delete user profiles.
- **Global Post Feed**: Monitor every post in the system with author identification and visibility status.
- **Message Logs**: A centralized view of all user-to-user communication (Admin-only access).
- **Story Management**: View and manage active short-lived content (Stories).

### 📊 System Insights
- **Live Statistics**: Real-time counts for Total Users, Posts, Messages, and Stories.
- **Profile Deep-Dive**: Detailed activity logs for individual users, including their post history and message exchanges.

### 🎨 Modern UI/UX
- **Responsive Design**: Sidebar-based navigation that works on all screen sizes.
- **Sleek Aesthetic**: Built with the Inter font and a professional indigo-themed color palette.
- **Interactive Feedback**: Real-time flash notifications for all administrative actions.

---

## 🛠 Tech Stack

- **Backend**: Python 3.x, Flask
- **Database**: MongoDB (via Flask-PyMongo)
- **Frontend**: HTML5, Vanilla CSS3 (Modern Flexbox/Grid), FontAwesome 6.4

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Davis-J7/SocialMedia_Page.git
cd SocialMedia_Page
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: If you don't have a requirements.txt, install: `pip install flask flask-pymongo python-dotenv`)*

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/SocialMediaDB?retryWrites=true&w=majority
```

### 5. Seed the Database (Optional)
If you want to start with sample data:
```bash
python seed.py
```

### 6. Run the Application
```bash
python app.py
```
Visit `http://127.0.0.1:5000` in your browser.

---

## 📂 Project Structure

- `app.py`: Main Flask application with admin logic.
- `static/style.css`: Modern, responsive CSS styling.
- `templates/`: Jinja2 templates for the dashboard and profiles.
- `seed.py`: Utility script for populating the database.
- `.gitignore`: Configured to protect sensitive `.env` and `venv` files.

---

## 📄 License
This project is open-source and available under the MIT License.

---

*Developed with ❤️ by Davis J7*
