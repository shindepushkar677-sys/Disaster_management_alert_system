from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit
from flask_mail import Mail, Message
import uuid
import json
import os
from datetime import datetime
import traceback

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-change-in-production"
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

# Flask-Mail configuration (optional)
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='youremail@gmail.com',
    MAIL_PASSWORD='your-app-password'
)

mail = Mail(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

USERS_FILE = "users.json"
ALERTS_FILE = "alerts.json"

# Helper functions
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"WARNING: users.json corrupted, resetting")
                    return []
                return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading users: {e}")
            return []
    return []

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

def load_alerts():
    if os.path.exists(ALERTS_FILE):
        try:
            with open(ALERTS_FILE, 'r') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"WARNING: alerts.json corrupted (was {type(data)}), resetting to empty list")
                    save_alerts([])
                    return []
                return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ERROR: alerts.json corrupted: {e}")
            save_alerts([])
            return []
    return []

def save_alerts(alerts):
    try:
        if not isinstance(alerts, list):
            print(f"ERROR: Trying to save non-list as alerts: {type(alerts)}")
            alerts = []
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
        print(f"Successfully saved {len(alerts)} alerts")
    except Exception as e:
        print(f"Error saving alerts: {e}")
        traceback.print_exc()

def save_alert(alert):
    """Save a single alert"""
    try:
        alerts = load_alerts()
        if not isinstance(alerts, list):
            alerts = []
        alerts.append(alert)
        save_alerts(alerts)
        print(f"Alert saved: {alert.get('id', 'unknown')}")
        return True
    except Exception as e:
        print(f"Error in save_alert: {e}")
        traceback.print_exc()
        return False

class User(UserMixin):
    def __init__(self, email):
        self.id = email
        self.email = email

@login_manager.user_loader
def load_user(email):
    users = load_users()
    for u in users:
        if u["email"] == email:
            return User(email)
    return None

def send_alert_email(alert):
    """Send email notifications"""
    try:
        users = load_users()
        with mail.connect() as conn:
            for user in users:
                msg = Message(
                    f"🚨 New {alert['type']} Alert",
                    recipients=[user["email"]],
                    sender=app.config["MAIL_USERNAME"],
                    body=f"Alert Type: {alert['type']}\n"
                         f"Description: {alert['desc']}\n"
                         f"Location: ({alert['lat']:.4f}, {alert['lng']:.4f})\n"
                         f"Time: {alert.get('timestamp', 'N/A')}"
                )
                conn.send(msg)
    except Exception as e:
        print(f"Email error: {e}")

# PUBLIC ROUTES
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return redirect(url_for("public_map"))

@app.route("/map")
def public_map():
    username = current_user.id if current_user.is_authenticated else "Guest"
    return render_template("map.html", username=username, is_authenticated=current_user.is_authenticated)

@app.route("/dashboard")
@login_required
def index():
    return render_template("map.html", username=current_user.id, is_authenticated=True)

@app.route("/get_alerts")
def get_alerts():
    try:
        alerts = load_alerts()
        return jsonify(alerts)
    except Exception as e:
        print(f"Error in get_alerts: {e}")
        traceback.print_exc()
        return jsonify([])

# AUTHENTICATION ROUTES
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("register"))
        
        users = load_users()
        if any(u["email"] == email for u in users):
            flash("Email already registered. Please log in.")
            return redirect(url_for("login"))
        
        users.append({"email": email, "password": password})
        save_users(users)
        flash("Registration successful! Please login.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        users = load_users()
        user = next((u for u in users if u["email"] == email and u["password"] == password), None)
        if user:
            login_user(User(email), remember=True)
            return redirect(url_for("index"))
        flash("Invalid email or password")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("public_map"))

# ALERT MANAGEMENT
@app.route("/add_alert", methods=["POST"])
@login_required
def add_alert():
    try:
        print("\n=== ADD ALERT REQUEST ===")
        alert = request.json
        print(f"Received data: {alert}")
        
        # Validate
        if not alert or not isinstance(alert, dict):
            return jsonify({"status": "error", "message": "Invalid data format"}), 400
        
        if not alert.get('type') or not alert.get('desc'):
            return jsonify({"status": "error", "message": "Missing type or description"}), 400
        
        if not alert.get('lat') or not alert.get('lng'):
            return jsonify({"status": "error", "message": "Missing coordinates"}), 400
        
        # Build alert object
        alert["id"] = str(uuid.uuid4())
        alert["user"] = current_user.id
        alert["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert["resolved"] = False
        
        print(f"Saving alert: {alert}")
        
        # Save to file
        success = save_alert(alert)
        if not success:
            return jsonify({"status": "error", "message": "Failed to save alert"}), 500
        
        # Broadcast via SocketIO with push notification data
        try:
            with app.app_context():
                socketio.emit("new_alert", {
                    **alert,
                    "notification": {
                        "title": f"🚨 {alert['type']} Alert",
                        "body": alert['desc'],
                        "requireInteraction": True
                    }
                })
            print("SocketIO broadcast successful with notification")
        except Exception as e:
            print(f"SocketIO error: {e}")
            traceback.print_exc()
        
        # Try email
        try:
            send_alert_email(alert)
        except Exception as e:
            print(f"Email error: {e}")
        
        print(f"=== SUCCESS: Alert {alert['id']} added ===\n")
        return jsonify({"status": "ok", "id": alert["id"]})
        
    except Exception as e:
        print(f"=== ERROR in add_alert ===")
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/mark_resolved", methods=["POST"])
@login_required
def mark_resolved():
    try:
        print("\n=== MARK RESOLVED REQUEST ===")
        alert_id = request.json.get("id")
        print(f"Resolving alert: {alert_id}")
        
        if not alert_id:
            return jsonify({"status": "error", "message": "No alert ID"}), 400
        
        alerts = load_alerts()
        found = False
        alert_data = None
        
        for alert in alerts:
            if alert.get("id") == alert_id:
                alert["resolved"] = True
                alert["resolved_by"] = current_user.id
                alert["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                alert_data = alert
                found = True
                break
        
        if not found:
            return jsonify({"status": "error", "message": "Alert not found"}), 404
        
        save_alerts(alerts)
        
        try:
            socketio.emit("alert_resolved", {
                "id": alert_id,
                "notification": {
                    "title": f"✅ {alert_data['type']} Resolved",
                    "body": f"Alert has been resolved by {current_user.id}"
                }
            }, namespace='/')
        except Exception as e:
            print(f"SocketIO error: {e}")
        
        print(f"=== SUCCESS: Alert {alert_id} resolved ===\n")
        return jsonify({"status": "resolved"})
        
    except Exception as e:
        print(f"=== ERROR in mark_resolved ===")
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/remove_alert", methods=["POST"])
@login_required
def remove_alert():
    try:
        print("\n=== REMOVE ALERT REQUEST ===")
        alert_id = request.json.get("id")
        print(f"Removing alert: {alert_id}")
        
        if not alert_id:
            return jsonify({"status": "error", "message": "No alert ID"}), 400
        
        alerts = load_alerts()
        original_count = len(alerts)
        removed_alert = next((a for a in alerts if a.get("id") == alert_id), None)
        alerts = [a for a in alerts if a.get("id") != alert_id]
        
        if len(alerts) == original_count:
            return jsonify({"status": "error", "message": "Alert not found"}), 404
        
        save_alerts(alerts)
        
        try:
            socketio.emit("remove_alert", {
                "id": alert_id,
                "notification": {
                    "title": "🗑️ Alert Removed",
                    "body": f"{removed_alert.get('type', 'Alert')} has been removed"
                }
            }, namespace='/')
        except Exception as e:
            print(f"SocketIO error: {e}")
        
        print(f"=== SUCCESS: Alert {alert_id} removed ===\n")
        return jsonify({"status": "removed"})
        
    except Exception as e:
        print(f"=== ERROR in remove_alert ===")
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/check_auth")
def check_auth():
    return jsonify({"authenticated": current_user.is_authenticated})

if __name__ == "__main__":
    # Initialize files if they don't exist
    if not os.path.exists(USERS_FILE):
        save_users([])
    if not os.path.exists(ALERTS_FILE):
        save_alerts([])
    
    print("\n" + "="*50)
    print("🚨 DISASTER MANAGEMENT SYSTEM STARTING")
    print("="*50)
    print(f"Users file: {USERS_FILE}")
    print(f"Alerts file: {ALERTS_FILE}")
    print(f"Server: http://0.0.0.0:5000")
    print(f"Local: http://127.0.0.1:5000")
    print("✨ Push Notifications: ENABLED")
    print("="*50 + "\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
