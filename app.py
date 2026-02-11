from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import os
import csv
import io
import secrets
import threading

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.config["SCHEMA_READY"] = False

# File upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------------- MODELS ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200), nullable=False)
    employee_id = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(100))
    role = db.Column(db.String(20), default='employee')  # 'employee' or 'admin'
    phone = db.Column(db.String(30))
    profile_pic = db.Column(db.String(200), default='default.png')
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_staff = db.Column(db.Boolean, default=True)
    position = db.Column(db.String(100))
    visa_type = db.Column(db.String(50))
    weekly_hour_limit = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)


class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    day = db.Column(db.Date, nullable=False)
    
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    lunch_start = db.Column(db.DateTime)
    lunch_end = db.Column(db.DateTime)
    dinner_start = db.Column(db.DateTime)
    dinner_end = db.Column(db.DateTime)
    
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    notes = db.Column(db.Text)
    shift_notes = db.Column(db.Text)
    approved_by = db.Column(db.Integer)  # Admin ID who approved
    approved_at = db.Column(db.DateTime)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    working_hours_per_day = db.Column(db.Float, default=8.0)
    lunch_break_duration = db.Column(db.Integer, default=60)  # minutes
    dinner_break_duration = db.Column(db.Integer, default=30)  # minutes
    weekly_target_hours = db.Column(db.Float, default=48.0)
    session_timeout_minutes = db.Column(db.Integer, default=480)  # 8 hours
    overtime_threshold_hours = db.Column(db.Float, default=40.0)
    overtime_multiplier = db.Column(db.Float, default=1.5)


class WeekApproval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='approved')
    approved_by = db.Column(db.Integer)
    approved_at = db.Column(db.DateTime)
    locked = db.Column(db.Boolean, default=True)


class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    leave_type = db.Column(db.String(20))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    reviewed_by = db.Column(db.Integer)
    reviewed_at = db.Column(db.DateTime)


class CorrectionRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    entry_date = db.Column(db.Date, nullable=False)
    requested_clock_in = db.Column(db.String(5))
    requested_clock_out = db.Column(db.String(5))
    requested_lunch_start = db.Column(db.String(5))
    requested_lunch_end = db.Column(db.String(5))
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    reviewed_by = db.Column(db.Integer)
    reviewed_at = db.Column(db.DateTime)


class Roster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    day_of_week = db.Column(db.String(20))  # Monday, Tuesday, etc.
    start_time = db.Column(db.String(5))    # HH:MM format
    end_time = db.Column(db.String(5))      # HH:MM format
    week_start = db.Column(db.Date)
    week_end = db.Column(db.Date)
    is_off = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    role_title = db.Column(db.String(100))


class HandoverMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text, nullable=False)
    shift_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.now)


class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_used = db.Column(db.Boolean, default=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- EMAIL HELPER ----------------
def send_email(to_email, subject, body):
    """Send email notification (simple version - can use sendgrid/mailgun in production)"""
    try:
        mail_server = app.config.get("MAIL_SERVER")
        mail_port = app.config.get("MAIL_PORT", 587)
        mail_username = app.config.get("MAIL_USERNAME")
        mail_password = app.config.get("MAIL_PASSWORD")
        mail_use_tls = app.config.get("MAIL_USE_TLS", True)
        mail_use_ssl = app.config.get("MAIL_USE_SSL", False)
        mail_from = app.config.get("MAIL_FROM") or mail_username

        if not mail_server or not mail_from:
            print(f"\n📧 EMAIL SENT (console)")
            print(f"   To: {to_email}")
            print(f"   Subject: {subject}")
            print(f"   Body: {body}")
            print()
            return True

        msg = MIMEMultipart()
        msg["From"] = mail_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if mail_use_ssl:
            server = smtplib.SMTP_SSL(mail_server, mail_port)
        else:
            server = smtplib.SMTP(mail_server, mail_port)
            if mail_use_tls:
                server.starttls()

        if mail_username and mail_password:
            server.login(mail_username, mail_password)

        server.sendmail(mail_from, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_sms(to_phone, message):
    """Send SMS (console fallback). Configure SMS settings to integrate a provider."""
    try:
        sms_enabled = app.config.get("SMS_ENABLED", False)
        if not sms_enabled:
            print(f"\n📱 SMS SENT (console)")
            print(f"   To: {to_phone}")
            print(f"   Message: {message}")
            print()
            return True
        # Integrate provider here
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False


def send_email_async(to_email, subject, body):
    t = threading.Thread(target=send_email, args=(to_email, subject, body), daemon=True)
    t.start()


# ---------------- HELPERS ----------------
def get_today_entry():
    entry = TimeEntry.query.filter_by(
        user_id=current_user.id,
        day=date.today()
    ).first()

    if not entry:
        entry = TimeEntry(
            user_id=current_user.id,
            day=date.today()
        )
        db.session.add(entry)
        db.session.commit()

    return entry


def minutes(a, b):
    if not a or not b:
        return 0
    if b < a:
        b = b + timedelta(days=1)
    return int((b - a).total_seconds() // 60)


def format_time(dt):
    """Format datetime to HH:MM"""
    if not dt:
        return "-"
    return dt.strftime("%H:%M")


def get_week_range(d=None):
    """Get Monday-Sunday range for a given date"""
    if d is None:
        d = date.today()
    if isinstance(d, datetime):
        d = d.date()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_image_type(header: bytes):
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"
    return None


def normalize_phone(value):
    if not value:
        return None
    raw = "".join(ch for ch in value.strip() if ch.isdigit() or ch == "+")
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if raw.startswith("+"):
        return f"+{digits}" if digits else None
    return digits or None


def log_activity(action, details=""):
    """Log user activity"""
    if current_user.is_authenticated:
        log = ActivityLog(user_id=current_user.id, action=action, details=details)
        db.session.add(log)
        db.session.commit()


def ensure_schema():
    db.create_all()

    def has_column(table, column):
        rows = db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)

    def add_column(table, column_def):
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))

    if not has_column("time_entry", "shift_notes"):
        add_column("time_entry", "shift_notes TEXT")

    if not has_column("user", "phone"):
        add_column("user", "phone TEXT")

    if not has_column("user", "is_staff"):
        add_column("user", "is_staff BOOLEAN DEFAULT 1")

    if not has_column("user", "position"):
        add_column("user", "position TEXT")

    if not has_column("user", "visa_type"):
        add_column("user", "visa_type TEXT")

    if not has_column("user", "weekly_hour_limit"):
        add_column("user", "weekly_hour_limit FLOAT")

    if not has_column("system_settings", "overtime_threshold_hours"):
        add_column("system_settings", "overtime_threshold_hours FLOAT DEFAULT 40.0")

    if not has_column("system_settings", "overtime_multiplier"):
        add_column("system_settings", "overtime_multiplier FLOAT DEFAULT 1.5")

    if not has_column("roster", "week_start"):
        add_column("roster", "week_start DATE")

    if not has_column("roster", "week_end"):
        add_column("roster", "week_end DATE")

    if not has_column("roster", "is_off"):
        add_column("roster", "is_off BOOLEAN DEFAULT 0")

    if not has_column("roster", "notes"):
        add_column("roster", "notes TEXT")

    if not has_column("roster", "role_title"):
        add_column("roster", "role_title TEXT")

    db.session.commit()


@app.before_request
def prepare_schema():
    if not app.config.get("SCHEMA_READY"):
        ensure_schema()
        app.config["SCHEMA_READY"] = True


def get_settings():
    settings = SystemSettings.query.first()
    if not settings:
        settings = SystemSettings()
        db.session.add(settings)
        db.session.commit()
    return settings


def is_week_locked(user_id, day):
    w_start, w_end = get_week_range(day)
    lock = WeekApproval.query.filter_by(
        user_id=user_id,
        week_start=w_start,
        week_end=w_end,
        locked=True
    ).first()
    return bool(lock)


def work_and_break_minutes(entry):
    break_mins = minutes(entry.lunch_start, entry.lunch_end) + minutes(entry.dinner_start, entry.dinner_end)
    work_mins = minutes(entry.clock_in, entry.clock_out) - break_mins
    if work_mins < 0:
        work_mins = 0
    return work_mins, break_mins


def daily_overtime_minutes(work_mins, settings):
    daily_threshold = int(settings.working_hours_per_day * 60)
    return max(0, work_mins - daily_threshold)


def validate_entry_time_order(entry):
    errors = []
    if entry.clock_in and entry.clock_out and entry.clock_out == entry.clock_in:
        errors.append("❌ Clock-out cannot be the same as clock-in.")
    if entry.lunch_start and entry.lunch_end and entry.lunch_end <= entry.lunch_start:
        errors.append("❌ Lunch end cannot be earlier than lunch start.")
    if entry.dinner_start and entry.dinner_end and entry.dinner_end <= entry.dinner_start:
        errors.append("❌ Dinner end cannot be earlier than dinner start.")
    return errors


def seed_demo_data():
    if not SystemSettings.query.first():
        settings = SystemSettings()
        db.session.add(settings)
        db.session.commit()

    if not User.query.first():
        users_data = [
            ("Abhi", "abhi@company.com", "abhi123", "EMP001", "Operations", "Bartender", True, True),
            ("Rutul", "rutul@company.com", "rutul123", "EMP002", "Floor", "Floor Manager", True, False),
            ("Geetika", "geetika@company.com", "geetika123", "EMP003", "Floor", "Supervisor", True, False),
            ("Palpasa", "palpasa@company.com", "palpasa123", "EMP004", "Floor", "Supervisor", True, False),
            ("Aman", "aman@company.com", "aman123", "EMP005", "Service", "Waiter", False, True),
            ("Udita", "udita@company.com", "udita123", "EMP006", "Service", "Waiter", False, True),
            ("Sneha", "sneha@company.com", "sneha123", "EMP007", "Service", "Waiter", False, True),
            ("Suraj", "suraj@company.com", "suraj123", "EMP008", "Service", "Waiter", False, True),
            ("Rohisa", "rohisa@company.com", "rohisa123", "EMP009", "Service", "Waiter", False, True),
        ]
        for name, email, pwd, emp_id, dept, position, is_admin, is_staff in users_data:
            u = User(
                name=name,
                email=email,
                password=generate_password_hash(pwd),
                employee_id=emp_id,
                department=dept,
                role='admin' if is_admin else 'employee',
                is_admin=is_admin,
                is_staff=is_staff,
                position=position,
                phone=None,
                is_active=True
            )
            db.session.add(u)
        db.session.commit()


# ---------------- ROUTES ----------------
@app.route("/init")
def init():
    """Initialize database with tables and demo data"""
    if not app.config.get("INIT_ENABLED", False):
        return "Not Found", 404

    is_admin = current_user.is_authenticated and current_user.role == "admin"
    token = request.args.get("token") or request.headers.get("X-Init-Token")
    if not is_admin:
        init_token = app.config.get("INIT_TOKEN")
        if not init_token or token != init_token:
            return "Unauthorized", 403

    db.create_all()

    seed_demo_data()

    return "✅ Database ready. Go to /login"


@app.route("/saas-mockup")
def saas_mockup():
    return render_template("saas_mockup.html")


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name_or_email = request.form["name"]
        pwd = request.form["password"]

        # Check by username or email
        user = User.query.filter(
            (User.name == name_or_email) | (User.email == name_or_email)
        ).first()
        
        if user and check_password_hash(user.password, pwd):
            if not user.is_active:
                flash("❌ Your account is deactivated. Contact admin.", "danger")
                return redirect("/login")
            
            login_user(user)
            if not User.query.filter((User.role == "admin") | (User.is_admin == True)).first():
                user.role = "admin"
                user.is_admin = True
                log_activity("ADMIN_BOOTSTRAP", f"{user.name} promoted to admin (no admins found)")
                flash("✅ Admin access restored for this account.", "success")
            user.last_login = datetime.now()
            db.session.commit()
            log_activity(f"LOGIN", f"User {user.name} logged in")
            return redirect("/dashboard")
        else:
            flash("❌ Invalid username/email or password", "danger")

    users = User.query.filter_by(is_active=True).all()
    if not users and app.config.get("AUTO_SEED_ON_EMPTY", True):
        seed_demo_data()
        users = User.query.filter_by(is_active=True).all()
        flash("✅ Demo employees restored.", "success")
    return render_template("login.html", users=users)


@app.route("/logout")
@login_required
def logout():
    log_activity("LOGOUT", f"User {current_user.name} logged out")
    logout_user()
    flash("✅ You have been logged out", "success")
    return redirect("/login")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page - change password, username, profile picture"""
    if request.method == "POST":
        action = request.form.get("action")
        
        # Change Password
        if action == "change_password":
            current_pwd = request.form.get("current_password")
            new_pwd = request.form.get("new_password")
            confirm_pwd = request.form.get("confirm_password")
            
            if not check_password_hash(current_user.password, current_pwd):
                flash("❌ Current password is incorrect", "danger")
            elif new_pwd != confirm_pwd:
                flash("❌ New passwords don't match", "danger")
            elif len(new_pwd) < 6:
                flash("❌ Password must be at least 6 characters", "danger")
            else:
                current_user.password = generate_password_hash(new_pwd)
                db.session.commit()
                flash("✅ Password changed successfully!", "success")
                return redirect("/settings")
        
        # Change Username
        elif action == "change_username":
            new_name = (request.form.get("new_username") or "").strip()
            
            if not new_name:
                flash("❌ Username cannot be empty", "danger")
            elif User.query.filter_by(name=new_name).first() and new_name != current_user.name:
                flash("❌ Username already taken", "danger")
            else:
                current_user.name = new_name
                db.session.commit()
                flash("✅ Username changed successfully!", "success")
                return redirect("/settings")
        
        # Update Email
        elif action == "update_email":
            email = request.form.get("email")
            current_user.email = email
            db.session.commit()
            flash("✅ Email updated successfully!", "success")
            return redirect("/settings")

        # Update Phone
        elif action == "update_phone":
            phone = normalize_phone(request.form.get("phone"))
            current_user.phone = phone
            db.session.commit()
            flash("✅ Phone updated successfully!", "success")
            return redirect("/settings")
        
        # Upload Profile Picture
        elif action == "upload_pic":
            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                allowed_mime = {"image/png", "image/jpeg", "image/gif"}
                file_header = file.stream.read(512)
                file.stream.seek(0)
                detected_type = detect_image_type(file_header)
                is_image_content = detected_type in {"png", "jpeg", "gif"}
                if (
                    file
                    and file.filename
                    and allowed_file(file.filename)
                    and file.mimetype in allowed_mime
                    and is_image_content
                ):
                    filename = secure_filename(f"user_{current_user.id}_{datetime.now().timestamp()}.{file.filename.rsplit('.', 1)[1].lower()}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    current_user.profile_pic = filename
                    db.session.commit()
                    flash("✅ Profile picture updated!", "success")
                    return redirect("/settings")
                else:
                    flash("❌ Invalid image file. Use a real PNG, JPG, or GIF", "danger")
    
    return render_template("settings.html", user=current_user)


@app.route("/reset-entry/<int:entry_id>", methods=["POST"])
@login_required
def reset_entry(entry_id):
    """Reset a time entry (delete all times) - Only admin or self"""
    entry = TimeEntry.query.get(entry_id)
    if entry and (entry.user_id == current_user.id or current_user.role == 'admin'):
        entry.clock_in = None
        entry.lunch_start = None
        entry.lunch_end = None
        entry.dinner_start = None
        entry.dinner_end = None
        entry.clock_out = None
        db.session.commit()
        log_activity("ENTRY_RESET", f"Entry for {entry.day} reset")
        flash("✅ Entry reset successfully!", "success")
    else:
        flash("❌ Access denied", "danger")
    
    if current_user.role == 'admin':
        return redirect("/admin")
    return redirect("/dashboard")


@app.route("/dashboard")
@login_required
def dashboard():
    entry = get_today_entry()
    settings = get_settings()

    break_minutes = (
        minutes(entry.lunch_start, entry.lunch_end)
        + minutes(entry.dinner_start, entry.dinner_end)
    )

    work_minutes = minutes(entry.clock_in, entry.clock_out) - break_minutes
    if work_minutes < 0:
        work_minutes = 0

    week_start, _ = get_week_range()
    roster = Roster.query.filter(
        Roster.user_id == current_user.id,
        (Roster.week_start == week_start) | (Roster.week_start.is_(None))
    ).all()
    day_order = {d: i for i, d in enumerate(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])}
    roster = sorted(roster, key=lambda r: day_order.get(r.day_of_week, 99))

    return render_template(
        "dashboard.html",
        entry=entry,
        work_minutes=work_minutes,
        break_minutes=break_minutes,
        format_time=format_time,
        roster=roster,
        settings=settings
    )


@app.route("/week")
@login_required
def week_view():
    w_start, w_end = get_week_range()
    
    entries = TimeEntry.query.filter(
        TimeEntry.user_id == current_user.id,
        TimeEntry.day >= w_start,
        TimeEntry.day <= w_end
    ).all()
    
    rows = []
    weekly_work = 0
    weekly_break = 0
    
    for entry in entries:
        if entry.clock_in:
            break_mins = minutes(entry.lunch_start, entry.lunch_end) + minutes(entry.dinner_start, entry.dinner_end)
            work_mins = minutes(entry.clock_in, entry.clock_out) - break_mins
            if work_mins < 0:
                work_mins = 0
            
            weekly_work += work_mins
            weekly_break += break_mins
            
            rows.append({
                'date': entry.day.strftime("%a, %d/%m"),
                'clock_in': format_time(entry.clock_in),
                'lunch': f"{format_time(entry.lunch_start)} - {format_time(entry.lunch_end)}",
                'dinner': f"{format_time(entry.dinner_start)} - {format_time(entry.dinner_end)}",
                'clock_out': format_time(entry.clock_out),
                'breaks': break_mins,
                'worked': work_mins
            })
    
    weekly_work_hours = weekly_work / 60
    remaining = max(0, 48 - weekly_work_hours)
    weekly_limit = current_user.weekly_hour_limit
    remaining_limit = None
    over_limit = False
    if weekly_limit is not None:
        remaining_limit = max(0, weekly_limit - weekly_work_hours)
        over_limit = weekly_work_hours > weekly_limit
    
    return render_template(
        "week.html",
        w_start=w_start,
        w_end=w_end,
        rows=rows,
        weekly_work=f"{weekly_work_hours:.1f}h",
        weekly_break=f"{weekly_break/60:.1f}h",
        remaining=f"{remaining:.1f}h",
        is_locked=is_week_locked(current_user.id, w_start),
        weekly_limit=weekly_limit,
        remaining_limit=remaining_limit,
        over_limit=over_limit
    )


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if current_user.role != 'admin' and not current_user.is_admin:
        return "Unauthorized", 403
    
    if request.method == "POST":
        action = request.form.get("action")
        
        # Manual time entry edit
        if action == "edit_entry":
            user_name = request.form.get("user_name")
            entry_date = request.form.get("entry_date")
            
            user = User.query.filter_by(name=user_name).first()
            if not user:
                flash("❌ User not found", "danger")
                return redirect("/admin")
            
            entry_day = datetime.strptime(entry_date, "%Y-%m-%d").date()
            if is_week_locked(user.id, entry_day):
                flash("❌ This week is locked. Unlock to edit.", "danger")
                return redirect("/admin")

            entry = TimeEntry.query.filter_by(
                user_id=user.id,
                day=entry_day
            ).first()
            
            if not entry:
                entry = TimeEntry(user_id=user.id, day=entry_day)
                db.session.add(entry)
            
            # Parse times
            if request.form.get("clock_in"):
                h, m = map(int, request.form.get("clock_in").split(":"))
                entry.clock_in = datetime.combine(entry.day, datetime.min.time()).replace(hour=h, minute=m)
            
            if request.form.get("clock_out"):
                h, m = map(int, request.form.get("clock_out").split(":"))
                entry.clock_out = datetime.combine(entry.day, datetime.min.time()).replace(hour=h, minute=m)
            
            if request.form.get("lunch_start"):
                h, m = map(int, request.form.get("lunch_start").split(":"))
                entry.lunch_start = datetime.combine(entry.day, datetime.min.time()).replace(hour=h, minute=m)
            
            if request.form.get("lunch_end"):
                h, m = map(int, request.form.get("lunch_end").split(":"))
                entry.lunch_end = datetime.combine(entry.day, datetime.min.time()).replace(hour=h, minute=m)
            
            if request.form.get("dinner_start"):
                h, m = map(int, request.form.get("dinner_start").split(":"))
                entry.dinner_start = datetime.combine(entry.day, datetime.min.time()).replace(hour=h, minute=m)
            
            if request.form.get("dinner_end"):
                h, m = map(int, request.form.get("dinner_end").split(":"))
                entry.dinner_end = datetime.combine(entry.day, datetime.min.time()).replace(hour=h, minute=m)

            errors = validate_entry_time_order(entry)
            if errors:
                db.session.rollback()
                for msg in errors:
                    flash(msg, "danger")
                return redirect("/admin")

            db.session.commit()
            log_activity("ENTRY_EDITED", f"{user.name} - {entry_day}")
            flash("✅ Entry updated successfully!", "success")
        
        # Delete user
        elif action == "delete_user":
            user_id = request.form.get("user_id")
            user = User.query.get(user_id)
            if user and (user.role != 'admin' and not user.is_admin):  # Can't delete admin
                TimeEntry.query.filter_by(user_id=user.id).delete()
                Roster.query.filter_by(user_id=user.id).delete()
                db.session.delete(user)
                db.session.commit()
                flash(f"✅ User {user.name} deleted", "success")
            elif user and (user.role == 'admin' or user.is_admin):
                flash("❌ Cannot delete admin account", "danger")
        
        # Reset user week
        elif action == "reset_week":
            user_id = request.form.get("user_id")
            w_start, w_end = get_week_range()
            TimeEntry.query.filter(
                TimeEntry.user_id == user_id,
                TimeEntry.day >= w_start,
                TimeEntry.day <= w_end
            ).delete()
            db.session.commit()
            flash("✅ Week reset for user", "success")
        
        # Set roster
        elif action == "set_roster":
            user_id = request.form.get("user_id")
            day_of_week = request.form.get("day_of_week")
            start_time = request.form.get("start_time")
            week_start, week_end = get_week_range()
            end_time = request.form.get("end_time")
            user = User.query.get(user_id)
            roster = Roster.query.filter_by(
                user_id=user_id,
                day_of_week=day_of_week,
                week_start=week_start
            ).first()
            if roster:
                roster.start_time = start_time
                roster.end_time = end_time
            else:
                roster = Roster(
                    user_id=user_id,
                    day_of_week=day_of_week,
                    start_time=start_time,
                    end_time=end_time,
                    week_start=week_start,
                    week_end=week_end
                )
                db.session.add(roster)

            roster.is_off = False
            roster.notes = None
            roster.role_title = user.position if user else None
            db.session.commit()
            flash("✅ Roster updated", "success")

        elif action == "set_roster_all":
            day_of_week = request.form.get("day_of_week")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")

            employees = User.query.filter_by(is_active=True).all()
            for emp in employees:
                roster = Roster.query.filter_by(user_id=emp.id, day_of_week=day_of_week).first()
                if roster:
                    roster.start_time = start_time
                    roster.end_time = end_time
                else:
                    roster = Roster(user_id=emp.id, day_of_week=day_of_week, start_time=start_time, end_time=end_time)
                    db.session.add(roster)
            db.session.commit()
            flash("✅ Roster updated for all employees", "success")

        elif action == "update_overtime":
            settings = get_settings()
            settings.overtime_threshold_hours = float(request.form.get("overtime_threshold", 40))
            settings.overtime_multiplier = float(request.form.get("overtime_multiplier", 1.5))
            db.session.commit()
            log_activity("OVERTIME_RULES_UPDATED", "Overtime rules updated")
            flash("✅ Overtime rules updated", "success")

        elif action == "rebuild_db":
            confirm_rebuild = request.form.get("confirm_rebuild") == "1"
            confirm_phrase = (request.form.get("confirm_phrase") or "").strip()
            if not confirm_rebuild or confirm_phrase != "REBUILD":
                flash("❌ Rebuild not confirmed. Check the box and type REBUILD.", "danger")
                return redirect("/admin")
            db.drop_all()
            db.create_all()
            seed_demo_data()
            app.config["SCHEMA_READY"] = True
            log_activity("DB_REBUILT", "Database rebuilt by admin")
            logout_user()
            flash("✅ Database rebuilt. Please log in again.", "success")
            return redirect("/login")
        
        return redirect("/admin")
    
    # Get all users' weekly summaries
    w_start, w_end = get_week_range()
    users = User.query.all()
    summaries = []
    roster_entries = Roster.query.all()
    user_map = {u.id: u for u in users}
    
    settings = get_settings()

    for user in users:
        entries = TimeEntry.query.filter(
            TimeEntry.user_id == user.id,
            TimeEntry.day >= w_start,
            TimeEntry.day <= w_end
        ).all()
        
        total_work = 0
        total_break = 0
        for entry in entries:
            if entry.clock_in:
                work, breaks = work_and_break_minutes(entry)
                total_work += work
                total_break += breaks
        
        work_hours = total_work / 60
        flag = "✓" if work_hours >= settings.weekly_target_hours else f"⚠ {settings.weekly_target_hours - work_hours:.1f}h"
        
        summaries.append({
            'id': user.id,
            'name': user.name,
            'work': f"{work_hours:.1f}h",
            'breaks': f"{total_break/60:.1f}h",
            'flag': flag,
            'locked': is_week_locked(user.id, w_start)
        })
    
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    return render_template(
        "admin.html",
        w_start=w_start,
        w_end=w_end,
        summaries=summaries,
        users=users,
        days_of_week=days_of_week,
        settings=settings,
        roster_entries=roster_entries,
        user_map=user_map
    )


@app.route("/calendar")
@login_required
def calendar():
    """Show calendar view of time entries"""
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    entries = TimeEntry.query.filter(
        TimeEntry.user_id == current_user.id,
        TimeEntry.day >= first_day,
        TimeEntry.day <= last_day
    ).all()
    
    # Create calendar dict
    calendar_data = {}
    for entry in entries:
        if entry.clock_in:
            break_mins = minutes(entry.lunch_start, entry.lunch_end) + minutes(entry.dinner_start, entry.dinner_end)
            work_mins = minutes(entry.clock_in, entry.clock_out) - break_mins
            if work_mins < 0:
                work_mins = 0
            calendar_data[entry.day.isoformat()] = {
                'work_minutes': work_mins,
                'break_minutes': break_mins,
                'status': entry.status
            }
    
    return render_template("calendar.html", 
        month=month, year=year, 
        calendar_data=calendar_data,
        today=date.today()
    )


@app.route("/roster")
@login_required
def roster_view():
    week_start, week_end = get_week_range()
    roster_entries = Roster.query.filter(
        Roster.user_id == current_user.id,
        (Roster.week_start == week_start) | (Roster.week_start.is_(None))
    ).all()
    day_order = {d: i for i, d in enumerate(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])}
    users = {u.id: u for u in User.query.all()}
    roster_entries = sorted(roster_entries, key=lambda r: day_order.get(r.day_of_week, 99))
    return render_template(
        "roster.html",
        roster_entries=roster_entries,
        users=users,
        week_start=week_start,
        week_end=week_end
    )


@app.route("/roster-admin", methods=["GET", "POST"])
@login_required
def roster_admin():
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")

    week_start = request.form.get("week_start") or request.args.get("week_start")
    if week_start:
        week_start = datetime.strptime(week_start, "%Y-%m-%d").date()
    else:
        week_start, _ = get_week_range()
    week_end = week_start + timedelta(days=6)

    staff_users = User.query.filter_by(is_staff=True, is_active=True).all()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    if request.method == "POST":
        for user in staff_users:
            for day in days:
                start_key = f"start_{user.id}_{day}"
                end_key = f"end_{user.id}_{day}"
                off_key = f"off_{user.id}_{day}"
                notes_key = f"notes_{user.id}_{day}"

                start_time = request.form.get(start_key)
                end_time = request.form.get(end_key)
                is_off = request.form.get(off_key) == "1"
                notes = request.form.get(notes_key)

                roster = Roster.query.filter_by(
                    user_id=user.id,
                    day_of_week=day,
                    week_start=week_start
                ).first()

                if not roster:
                    roster = Roster(
                        user_id=user.id,
                        day_of_week=day,
                        week_start=week_start,
                        week_end=week_end
                    )
                    db.session.add(roster)

                roster.is_off = is_off
                roster.start_time = None if is_off else start_time
                roster.end_time = None if is_off else end_time
                roster.notes = notes
                roster.role_title = user.position

        db.session.commit()
        flash("✅ Weekly roster updated", "success")
        return redirect(url_for("roster_admin", week_start=week_start.isoformat()))

    roster_entries = Roster.query.filter_by(week_start=week_start).all()
    roster_map = {(r.user_id, r.day_of_week): r for r in roster_entries}

    return render_template(
        "roster_admin.html",
        week_start=week_start,
        week_end=week_end,
        staff_users=staff_users,
        days=days,
        roster_map=roster_map
    )


@app.route("/handover", methods=["GET", "POST"])
@login_required
def handover():
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        shift_date = request.form.get("shift_date")
        if message:
            msg = HandoverMessage(
                user_id=current_user.id,
                message=message,
                shift_date=datetime.strptime(shift_date, "%Y-%m-%d").date() if shift_date else date.today()
            )
            db.session.add(msg)
            db.session.commit()
            flash("✅ Note added", "success")
        return redirect("/handover")

    messages = HandoverMessage.query.order_by(HandoverMessage.created_at.desc()).limit(200).all()
    users = {u.id: u for u in User.query.all()}
    return render_template("handover.html", messages=messages, users=users, today=date.today())


@app.route("/employee-management", methods=["GET", "POST"])
@login_required
def employee_management():
    """Admin: Manage employees"""
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add_employee":
            name = request.form.get("name")
            email = request.form.get("email")
            emp_id = request.form.get("employee_id")
            dept = request.form.get("department")
            phone = normalize_phone(request.form.get("phone"))
            position = request.form.get("position")
            visa_type = request.form.get("visa_type")
            weekly_hour_limit = request.form.get("weekly_hour_limit")
            role = request.form.get("role", "employee")
            is_staff = request.form.get("is_staff") == "1"
            
            if User.query.filter_by(name=name).first():
                flash("❌ Username already exists", "danger")
            elif email and User.query.filter_by(email=email).first():
                flash("❌ Email already exists", "danger")
            else:
                # Generate temporary password
                temp_pwd = "TempPwd@123"
                u = User(
                    name=name,
                    email=email,
                    password=generate_password_hash(temp_pwd),
                    employee_id=emp_id,
                    department=dept,
                    role=role,
                    is_admin=(role == 'admin'),
                    is_staff=is_staff,
                    phone=phone,
                    position=position,
                    visa_type=visa_type,
                    weekly_hour_limit=float(weekly_hour_limit) if weekly_hour_limit else None,
                    is_active=True
                )
                db.session.add(u)
                db.session.commit()
                log_activity(f"EMPLOYEE_ADDED", f"Added employee {name}")
                flash(f"✅ Employee {name} added. Temp password: {temp_pwd}", "success")
        
        elif action == "toggle_active":
            user_id = request.form.get("user_id")
            user = User.query.get(user_id)
            if user and (user.role != 'admin' and not user.is_admin):
                user.is_active = not user.is_active
                db.session.commit()
                status = "activated" if user.is_active else "deactivated"
                log_activity(f"EMPLOYEE_{status.upper()}", f"{user.name} {status}")
                flash(f"✅ Employee {status}", "success")
        
        elif action == "update_employee":
            user_id = request.form.get("user_id")
            user = User.query.get(user_id)
            if user:
                role = request.form.get("role", user.role)
                if (user.role == "admin" or user.is_admin) and role != "admin":
                    admin_count = User.query.filter((User.role == "admin") | (User.is_admin == True)).count()
                    if admin_count <= 1:
                        flash("❌ Cannot remove the last admin.", "danger")
                        return redirect("/employee-management")
                user.email = request.form.get("email")
                user.department = request.form.get("department")
                user.employee_id = request.form.get("employee_id")
                user.phone = normalize_phone(request.form.get("phone"))
                user.position = request.form.get("position")
                user.visa_type = request.form.get("visa_type")
                user.weekly_hour_limit = float(request.form.get("weekly_hour_limit")) if request.form.get("weekly_hour_limit") else None
                user.role = role
                user.is_admin = user.role == 'admin'
                user.is_staff = request.form.get("is_staff") == "1"
                db.session.commit()
                log_activity(f"EMPLOYEE_UPDATED", f"Updated {user.name}")
                flash("✅ Employee updated", "success")
        
        return redirect("/employee-management")
    
    employees = User.query.all()
    return render_template("employee_management.html", employees=employees)


@app.route("/approve-timesheet", methods=["GET", "POST"])
@login_required
def approve_timesheet():
    """Admin: Approve/reject timesheets"""
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")
    
    if request.method == "POST":
        entry_id = request.form.get("entry_id")
        action_type = request.form.get("action_type")  # approve or reject
        notes = request.form.get("notes", "")
        lock_week = request.form.get("lock_week") == "1"
        
        entry = TimeEntry.query.get(entry_id)
        if entry:
            entry.status = 'approved' if action_type == 'approve' else 'rejected'
            entry.approved_by = current_user.id
            entry.approved_at = datetime.now()
            entry.notes = notes
            db.session.commit()

            if lock_week and action_type == 'approve':
                w_start, w_end = get_week_range(entry.day)
                lock = WeekApproval.query.filter_by(user_id=entry.user_id, week_start=w_start, week_end=w_end).first()
                if not lock:
                    lock = WeekApproval(user_id=entry.user_id, week_start=w_start, week_end=w_end)
                    db.session.add(lock)
                lock.locked = True
                lock.approved_by = current_user.id
                lock.approved_at = datetime.now()
                db.session.commit()
                log_activity("WEEK_LOCKED", f"User {entry.user_id} week {w_start}–{w_end}")
            
            user = User.query.get(entry.user_id)
            action = "APPROVED" if action_type == 'approve' else "REJECTED"
            log_activity(f"TIMESHEET_{action}", f"Timesheet for {user.name} on {entry.day}")
            flash(f"✅ Timesheet {action_type}ed", "success")
        
        return redirect("/approve-timesheet")
    
    # Get pending timesheets
    pending_entries = TimeEntry.query.filter(
        TimeEntry.status != 'approved',
        TimeEntry.clock_in.isnot(None),
        TimeEntry.clock_out.isnot(None)
    ).all()
    settings = get_settings()
    users_map = {u.id: u for u in User.query.all()}
    
    entries_data = []
    for entry in pending_entries:
        user = users_map.get(entry.user_id)
        if entry.clock_in:
            work_mins, break_mins = work_and_break_minutes(entry)
            overtime_mins = daily_overtime_minutes(work_mins, settings)
            w_start, w_end = get_week_range(entry.day)
            entries_data.append({
                'id': entry.id,
                'user_name': user.name,
                'date': entry.day,
                'week_start': w_start,
                'week_end': w_end,
                'work_minutes': work_mins,
                'clock_in': format_time(entry.clock_in),
                'clock_out': format_time(entry.clock_out),
                'overtime_minutes': overtime_mins,
                'is_locked': is_week_locked(entry.user_id, entry.day),
                'shift_notes': entry.shift_notes,
                'audit_url': url_for('audit_log')
            })
    
    return render_template("approve_timesheet.html", entries=entries_data)


@app.route("/save-notes", methods=["POST"])
@login_required
def save_notes():
    entry = get_today_entry()
    if is_week_locked(current_user.id, entry.day):
        flash("❌ This week is locked. Notes cannot be edited.", "danger")
        return redirect("/dashboard")
    entry.shift_notes = request.form.get("shift_notes", "").strip()
    db.session.commit()
    log_activity("SHIFT_NOTES_UPDATED", f"{current_user.name} notes for {entry.day}")
    flash("✅ Notes saved", "success")
    return redirect("/dashboard")


@app.route("/request-correction", methods=["GET", "POST"])
@login_required
def request_correction():
    if request.method == "POST":
        entry_date = datetime.strptime(request.form.get("entry_date"), "%Y-%m-%d").date()
        if is_week_locked(current_user.id, entry_date):
            flash("❌ This week is locked. Corrections are not allowed.", "danger")
            return redirect("/request-correction")

        req = CorrectionRequest(
            user_id=current_user.id,
            entry_date=entry_date,
            requested_clock_in=request.form.get("clock_in"),
            requested_clock_out=request.form.get("clock_out"),
            requested_lunch_start=request.form.get("lunch_start"),
            requested_lunch_end=request.form.get("lunch_end"),
            reason=request.form.get("reason")
        )
        db.session.add(req)
        db.session.commit()
        log_activity("CORRECTION_REQUESTED", f"{current_user.name} {entry_date}")
        flash("✅ Correction request submitted", "success")
        return redirect("/request-correction")

    my_requests = CorrectionRequest.query.filter_by(user_id=current_user.id).order_by(CorrectionRequest.id.desc()).all()
    return render_template("correction_request.html", requests=my_requests)


@app.route("/approve-corrections", methods=["GET", "POST"])
@login_required
def approve_corrections():
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")

    if request.method == "POST":
        req_id = request.form.get("request_id")
        decision = request.form.get("decision")

        req = CorrectionRequest.query.get(req_id)
        if req:
            if decision == "approve" and is_week_locked(req.user_id, req.entry_date):
                flash("❌ This week is locked. Corrections cannot be applied.", "danger")
                return redirect("/approve-corrections")
            req.status = 'approved' if decision == 'approve' else 'rejected'
            req.reviewed_by = current_user.id
            req.reviewed_at = datetime.now()

            if decision == 'approve':
                entry = TimeEntry.query.filter_by(user_id=req.user_id, day=req.entry_date).first()
                if not entry:
                    entry = TimeEntry(user_id=req.user_id, day=req.entry_date)
                    db.session.add(entry)
                base_day = datetime.combine(req.entry_date, datetime.min.time())
                if req.requested_clock_in:
                    h, m = map(int, req.requested_clock_in.split(":"))
                    entry.clock_in = base_day.replace(hour=h, minute=m)
                if req.requested_clock_out:
                    h, m = map(int, req.requested_clock_out.split(":"))
                    entry.clock_out = base_day.replace(hour=h, minute=m)
                if req.requested_lunch_start:
                    h, m = map(int, req.requested_lunch_start.split(":"))
                    entry.lunch_start = base_day.replace(hour=h, minute=m)
                if req.requested_lunch_end:
                    h, m = map(int, req.requested_lunch_end.split(":"))
                    entry.lunch_end = base_day.replace(hour=h, minute=m)

                errors = validate_entry_time_order(entry)
                if errors:
                    db.session.rollback()
                    for msg in errors:
                        flash(msg, "danger")
                    return redirect("/approve-corrections")

            db.session.commit()
            log_activity("CORRECTION_REVIEWED", f"{req.user_id} {req.entry_date} {req.status}")
            flash("✅ Correction request updated", "success")

        return redirect("/approve-corrections")

    pending = CorrectionRequest.query.filter_by(status='pending').all()
    users = {u.id: u for u in User.query.all()}
    return render_template("approve_corrections.html", requests=pending, users=users)


@app.route("/leave-request", methods=["GET", "POST"])
@login_required
def leave_request():
    if request.method == "POST":
        start = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
        end = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()

        req = LeaveRequest(
            user_id=current_user.id,
            leave_type=request.form.get("leave_type"),
            start_date=start,
            end_date=end,
            reason=request.form.get("reason")
        )
        db.session.add(req)
        db.session.commit()
        log_activity("LEAVE_REQUESTED", f"{current_user.name} {start}–{end}")
        flash("✅ Leave request submitted", "success")
        return redirect("/leave-request")

    my_leaves = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.id.desc()).all()
    return render_template("leave_request.html", requests=my_leaves)


@app.route("/approve-leave", methods=["GET", "POST"])
@login_required
def approve_leave():
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")

    if request.method == "POST":
        req_id = request.form.get("request_id")
        decision = request.form.get("decision")
        req = LeaveRequest.query.get(req_id)
        if req:
            req.status = 'approved' if decision == 'approve' else 'rejected'
            req.reviewed_by = current_user.id
            req.reviewed_at = datetime.now()
            db.session.commit()
            log_activity("LEAVE_REVIEWED", f"{req.user_id} {req.start_date}–{req.end_date} {req.status}")
            flash("✅ Leave request updated", "success")

        return redirect("/approve-leave")

    pending = LeaveRequest.query.filter_by(status='pending').all()
    users = {u.id: u for u in User.query.all()}
    return render_template("approve_leave.html", requests=pending, users=users)


@app.route("/audit-log")
@login_required
def audit_log():
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")

    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(300).all()
    users = {u.id: u for u in User.query.all()}
    return render_template("audit_log.html", logs=logs, users=users)


@app.route("/export-payroll")
@login_required
def export_payroll():
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")

    export_format = request.args.get('format', 'csv')
    week_date = request.args.get('week', date.today().isoformat())
    week_date_obj = datetime.strptime(week_date, '%Y-%m-%d').date()
    w_start, w_end = get_week_range(week_date_obj)
    settings = get_settings()

    employees = User.query.filter_by(role='employee', is_active=True).all()
    rows = []

    weekly_threshold_mins = int(settings.overtime_threshold_hours * 60)
    for emp in employees:
        entries = TimeEntry.query.filter(
            TimeEntry.user_id == emp.id,
            TimeEntry.day >= w_start,
            TimeEntry.day <= w_end
        ).all()

        total_work = 0
        total_break = 0
        for entry in entries:
            if entry.clock_in:
                work, brk = work_and_break_minutes(entry)
                total_work += work
                total_break += brk

        regular_mins = min(total_work, weekly_threshold_mins)
        overtime_mins = max(0, total_work - weekly_threshold_mins)

        rows.append({
            "emp_id": emp.employee_id or "",
            "name": emp.name,
            "dept": emp.department or "",
            "week_start": w_start.isoformat(),
            "week_end": w_end.isoformat(),
            "regular_hours": round(regular_mins / 60, 2),
            "overtime_hours": round(overtime_mins / 60, 2),
            "total_hours": round(total_work / 60, 2),
            "break_hours": round(total_break / 60, 2),
        })

    if export_format == "xlsx":
        try:
            from openpyxl import Workbook # type: ignore
        except Exception:
            flash("❌ Install openpyxl to export Excel", "danger")
            return redirect("/reports")

        wb = Workbook()
        ws = wb.active
        ws.title = "Payroll"
        ws.append(["Employee ID", "Name", "Department", "Week Start", "Week End", "Regular Hours", "Overtime Hours", "Total Hours", "Break Hours"])
        for r in rows:
            ws.append([r["emp_id"], r["name"], r["dept"], r["week_start"], r["week_end"], r["regular_hours"], r["overtime_hours"], r["total_hours"], r["break_hours"]])

        mem = io.BytesIO()
        wb.save(mem)
        mem.seek(0)
        log_activity("EXPORT_XLSX", f"Payroll {w_start}–{w_end}")
        return send_file(
            mem,
            as_attachment=True,
            download_name=f'payroll_{w_start}_{w_end}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee ID", "Name", "Department", "Week Start", "Week End", "Regular Hours", "Overtime Hours", "Total Hours", "Break Hours"])
    for r in rows:
        writer.writerow([r["emp_id"], r["name"], r["dept"], r["week_start"], r["week_end"], r["regular_hours"], r["overtime_hours"], r["total_hours"], r["break_hours"]])

    output.seek(0)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    log_activity("EXPORT_CSV", f"Payroll {w_start}–{w_end}")
    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'payroll_{w_start}_{w_end}.csv'
    )


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Handle forgot password - send reset link"""
    if request.method == "POST":
        email_or_username = (request.form.get("email") or "").strip()
        user = User.query.filter(
            (User.email == email_or_username) | (User.name == email_or_username)
        ).first()

        normalized_phone = "".join(ch for ch in email_or_username if ch.isdigit() or ch == "+")
        if not user and normalized_phone:
            user = User.query.filter_by(phone=normalized_phone).first()
        
        if user:
            # Create reset token
            token = secrets.token_urlsafe(32)
            reset = PasswordReset(user_id=user.id, token=token)
            db.session.add(reset)
            db.session.commit()
            
            # Send reset link via email or phone
            reset_link = url_for('reset_password', token=token, _external=True)
            show_link = app.config.get("SHOW_RESET_LINK", False) or app.config.get("DEBUG", False)
            email_body = f"""Hello {user.name},

You requested to reset your password. Click the link below:

{reset_link}

This link expires in 24 hours.

If you didn't request this, ignore this email.

Best regards,
TimeTracker Team"""

            if user.email and ('@' in email_or_username or not email_or_username.strip().isdigit()):
                send_email(user.email, "Password Reset Request", email_body)
                flash("✅ Password reset link sent to your email!", "success")
                if show_link and (not app.config.get("MAIL_SERVER") or not (app.config.get("MAIL_FROM") or app.config.get("MAIL_USERNAME"))):
                    flash(f"🔗 Reset link: {reset_link}", "info")
            elif user.phone:
                send_sms(user.phone, f"Reset your TimeTracker password: {reset_link}")
                flash("✅ Password reset link sent to your phone!", "success")
                if show_link and not app.config.get("SMS_ENABLED", False):
                    flash(f"🔗 Reset link: {reset_link}", "info")
            else:
                flash("❌ No email or phone available for this user.", "danger")
            log_activity("FORGOT_PASSWORD_REQUEST", f"Password reset requested for {user.email}")
        else:
            flash("❌ User not found", "danger")
    
    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Reset password with token"""
    reset = PasswordReset.query.filter_by(token=token, is_used=False).first()
    
    if not reset:
        flash("❌ Invalid or expired token", "danger")
        return redirect("/login")
    
    # Check if token is expired (24 hours)
    if (datetime.now() - reset.created_at).total_seconds() > 86400:
        flash("❌ Reset link expired. Request a new one.", "danger")
        return redirect("/forgot-password")
    
    if request.method == "POST":
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        
        if len(password) < 6:
            flash("❌ Password must be at least 6 characters", "danger")
        elif password != confirm:
            flash("❌ Passwords don't match", "danger")
        else:
            user = User.query.get(reset.user_id)
            user.password = generate_password_hash(password)
            reset.is_used = True
            db.session.commit()
            
            send_email(user.email or "demo@example.com", "Password Reset Success", 
                      f"Hi {user.name}, your password has been reset successfully.")
            
            flash("✅ Password reset successful! Login with new password.", "success")
            log_activity("PASSWORD_RESET", f"Password reset completed")
            return redirect("/login")
    
    return render_template("reset_password.html", token=token)


@app.route("/export-csv")
@login_required
def export_csv():
    """Export employee data or reports to CSV"""
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")
    
    export_type = request.args.get('type', 'employees')
    
    if export_type == 'employees':
        # Export all employees
        employees = User.query.filter_by(role='employee').all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Employee ID', 'Name', 'Email', 'Department', 'Status', 'Created Date'])
        
        for emp in employees:
            writer.writerow([
                emp.employee_id or '',
                emp.name,
                emp.email or '',
                emp.department or '',
                'Active' if emp.is_active else 'Inactive',
                emp.created_at.strftime('%Y-%m-%d %H:%M') if emp.created_at else ''
            ])
        
        output.seek(0)
        mem = io.BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        
        log_activity("EXPORT_CSV", f"Exported {len(employees)} employees")
        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'employees_{date.today().isoformat()}.csv'
        )
    
    elif export_type == 'timesheets':
        # Export timesheet data
        selected_date = request.args.get('date', date.today().isoformat())
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        
        employees = User.query.filter_by(role='employee', is_active=True).all()
        users_map = {u.id: u for u in employees}
        entries = TimeEntry.query.filter_by(day=selected_date_obj).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Employee', 'Clock In', 'Clock Out', 'Work Hours', 'Break Minutes', 'Status'])
        
        for entry in entries:
            emp = users_map.get(entry.user_id)
            work_minutes = minutes(entry.clock_in, entry.clock_out)
            break_minutes = minutes(entry.lunch_start, entry.lunch_end) + minutes(entry.dinner_start, entry.dinner_end)
            work_hours = (work_minutes - break_minutes) / 60 if work_minutes > 0 else 0
            
            writer.writerow([
                entry.day.isoformat(),
                emp.name if emp else 'Unknown',
                entry.clock_in.strftime('%H:%M') if entry.clock_in else '',
                entry.clock_out.strftime('%H:%M') if entry.clock_out else '',
                f"{work_hours:.1f}",
                str(break_minutes),
                entry.status
            ])
        
        output.seek(0)
        mem = io.BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        
        log_activity("EXPORT_CSV", f"Exported timesheets for {selected_date}")
        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'timesheets_{selected_date}.csv'
        )


@app.route("/reports")
@login_required
def reports():
    """Admin: View reports"""
    if current_user.role != 'admin' and not current_user.is_admin:
        flash("❌ Access denied", "danger")
        return redirect("/dashboard")
    
    report_type = request.args.get('type', 'daily')
    selected_date = request.args.get('date', date.today().isoformat())
    
    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
    employees = User.query.filter_by(role='employee', is_active=True).all()
    
    report_data = []
    for employee in employees:
        if report_type == 'daily':
            entries = TimeEntry.query.filter_by(user_id=employee.id, day=selected_date_obj).all()
        else:  # weekly
            w_start, w_end = get_week_range(selected_date_obj)
            entries = TimeEntry.query.filter(
                TimeEntry.user_id == employee.id,
                TimeEntry.day >= w_start,
                TimeEntry.day <= w_end
            ).all()
        
        total_work = 0
        total_break = 0
        for entry in entries:
            if entry.clock_in:
                breaks = minutes(entry.lunch_start, entry.lunch_end) + minutes(entry.dinner_start, entry.dinner_end)
                work = minutes(entry.clock_in, entry.clock_out) - breaks
                if work > 0:
                    total_work += work
                total_break += breaks
        
        report_data.append({
            'name': employee.name,
            'dept': employee.department,
            'work_hours': f"{total_work/60:.1f}",
            'break_hours': f"{total_break/60:.1f}",
            'emp_id': employee.employee_id
        })
    
    return render_template("reports.html", 
        report_type=report_type,
        selected_date=selected_date,
        report_data=report_data
    )


@app.route("/action/<name>", methods=["POST"])
@login_required
def action(name):
    if is_week_locked(current_user.id, date.today()):
        flash("❌ This week is locked. Contact admin for changes.", "danger")
        return redirect("/dashboard")
    entry = get_today_entry()
    now = datetime.now()

    if name == "clock_in":
        if entry.clock_in:
            flash("❌ You are already clocked in", "danger")
            return redirect("/dashboard")
        entry.clock_in = now
        log_activity("CLOCK_IN", f"Clocked in at {now.strftime('%H:%M')}")

    elif name == "lunch_start":
        entry.lunch_start = now
        log_activity("LUNCH_START", f"Lunch started at {now.strftime('%H:%M')}")

    elif name == "lunch_end":
        if not entry.lunch_start or now <= entry.lunch_start:
            flash("❌ Lunch end cannot be earlier than lunch start", "danger")
            return redirect("/dashboard")
        entry.lunch_end = now
        log_activity("LUNCH_END", f"Lunch ended at {now.strftime('%H:%M')}")

    elif name == "dinner_start":
        entry.dinner_start = now
        log_activity("DINNER_START", f"Dinner started at {now.strftime('%H:%M')}")

    elif name == "dinner_end":
        if not entry.dinner_start or now <= entry.dinner_start:
            flash("❌ Dinner end cannot be earlier than dinner start", "danger")
            return redirect("/dashboard")
        entry.dinner_end = now
        log_activity("DINNER_END", f"Dinner ended at {now.strftime('%H:%M')}")

    elif name == "clock_out":
        if not entry.clock_in:
            flash("❌ Clock in before clocking out", "danger")
            return redirect("/dashboard")
        if now <= entry.clock_in:
            flash("❌ Clock out cannot be earlier than clock in", "danger")
            return redirect("/dashboard")
        entry.clock_out = now
        entry.status = 'pending'
        entry.approved_by = None
        entry.approved_at = None
        work_mins, break_mins = work_and_break_minutes(entry)
        if current_user.email and app.config.get("MAIL_ENABLED", True):
            subject = "Daily Work Summary"
            body = (
                f"Hi {current_user.name},\n\n"
                f"Date: {entry.day}\n"
                f"Worked: {work_mins/60:.2f}h\n"
                f"Breaks: {break_mins}m\n\n"
                "Thanks,\nTimeTracker"
            )
            if app.config.get("MAIL_ASYNC", True):
                send_email_async(current_user.email, subject, body)
            else:
                send_email(current_user.email, subject, body)
        log_activity("CLOCK_OUT", f"Clocked out at {now.strftime('%H:%M')}")

    db.session.commit()
    flash(f"✅ {name.replace('_', ' ').title()} recorded", "success")
    return redirect("/dashboard")


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
