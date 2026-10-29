import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, send_file
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from services.ai_service import AIService
from services.pdf_service import generate_pdf_report

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

# Initialize AI Service
ai_service = AIService(
    api_key=app.config.get("GEMINI_API_KEY"),
    model_name=app.config.get("GEMINI_MODEL", "gemini-2.5-flash")
)

# --- Database Models ---

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationship to VivaSession
    sessions = db.relationship("VivaSession", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class VivaSession(db.Model):
    __tablename__ = "viva_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(150), nullable=False, default="General")
    difficulty = db.Column(db.String(50), nullable=False, default="Intermediate")
    question = db.Column(db.Text, nullable=False)
    user_answer = db.Column(db.Text, nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    improved_answer = db.Column(db.Text, nullable=True)
    followup_question = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, nullable=False)  # Earned score out of 10
    total = db.Column(db.Integer, nullable=False, default=10)
    time_taken_seconds = db.Column(db.Integer, default=0)
    hints_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


# --- Context Processor & Auth Decorators ---

@app.context_processor
def inject_user():
    user_id = session.get("user_id")
    if user_id:
        current_user = db.session.get(User, user_id)
        return dict(current_user=current_user)
    return dict(current_user=None)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in or create an account to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# --- Analytics & Weak Topic Analysis ---

def analyze_user_weak_topics(user_id: int):
    """Aggregate total score and max score per subject specifically for the logged-in user."""
    results = db.session.query(
        VivaSession.subject,
        func.sum(VivaSession.score).label("total_earned"),
        func.sum(VivaSession.total).label("total_possible"),
        func.count(VivaSession.id).label("session_count")
    ).filter(VivaSession.user_id == user_id).group_by(VivaSession.subject).all()

    if not results:
        return {}, None

    analytics = {}
    for row in results:
        percentage = round((row.total_earned / row.total_possible) * 100, 1) if row.total_possible > 0 else 0
        analytics[row.subject] = percentage

    # Fetch recent sessions for contextual study plan analysis
    recent_sessions = VivaSession.query.filter_by(user_id=user_id).order_by(VivaSession.created_at.desc()).limit(10).all()
    sessions_summary = [
        {"subject": s.subject, "topic": s.topic, "score": s.score, "total": s.total}
        for s in recent_sessions
    ]

    study_plan = ai_service.generate_study_plan(analytics, sessions_summary)
    return analytics, study_plan


# --- Authentication Routes ---

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        # Check existing user
        if User.query.filter_by(username=username).first():
            flash("Username is already taken. Please choose another.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("register.html")

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        flash(f"Welcome to AI Viva Prep, {new_user.username}! Your account has been created.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter((User.username == identifier) | (User.email == identifier.lower())).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("index"))


# --- Core Viva Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/practice", methods=["GET", "POST"])
def practice():
    if request.method == "POST":
        subject = request.form.get("subject", "Operating Systems")
        difficulty = request.form.get("difficulty", "Intermediate")
        topic = request.form.get("topic", "").strip() or None
        timed_mode = request.form.get("timed_mode") == "on"
        time_limit = int(request.form.get("time_limit", "90"))
    else:
        subject = request.args.get("subject", "Operating Systems")
        difficulty = request.args.get("difficulty", "Intermediate")
        topic = request.args.get("topic", "").strip() or None
        timed_mode = request.args.get("timed_mode") == "true"
        time_limit = int(request.args.get("time_limit", "90"))

    # Generate dynamic question via Gemini AI (or intelligent fallback)
    question_data = ai_service.generate_question(subject=subject, difficulty=difficulty, topic=topic)
    
    # Cache hints in session for progressive revealing
    session["current_viva_hints"] = question_data.get("hints", [])

    return render_template(
        "practice.html",
        subject=subject,
        difficulty=difficulty,
        topic=question_data.get("topic", "Core Concepts"),
        question=question_data.get("question"),
        timed_mode=timed_mode,
        time_limit=time_limit,
        hints=question_data.get("hints", [])
    )


@app.route("/api/hint", methods=["POST"])
def get_hint():
    data = request.get_json() or {}
    hint_index = int(data.get("hint_index", 0))
    cached_hints = session.get("current_viva_hints", [])

    if 0 <= hint_index < len(cached_hints):
        return jsonify({"success": True, "hint": cached_hints[hint_index], "hint_number": hint_index + 1})
    
    # Generic fallback hint if index out of bounds
    generic_hints = [
        "Focus on defining the fundamental concept clearly before expanding.",
        "Consider the underlying data structures, hardware interactions, or algorithms involved.",
        "Conclude with key practical trade-offs (space vs time, safety vs performance)."
    ]
    selected_hint = generic_hints[min(hint_index, len(generic_hints) - 1)]
    return jsonify({"success": True, "hint": selected_hint, "hint_number": hint_index + 1})


@app.route("/submit", methods=["POST"])
def submit_answer():
    subject = request.form.get("subject", "General")
    topic = request.form.get("topic", "General")
    difficulty = request.form.get("difficulty", "Intermediate")
    question = request.form.get("question", "")
    user_answer = request.form.get("user_answer", "").strip()
    time_taken_seconds = int(request.form.get("time_taken_seconds", 0))
    hints_used = int(request.form.get("hints_used", 0))

    # Evaluate response via Gemini AI
    eval_result = ai_service.evaluate_answer(
        question=question,
        user_answer=user_answer,
        subject=subject,
        topic=topic,
        difficulty=difficulty
    )

    earned_score = eval_result["score"]
    max_score = 10
    feedback = eval_result["feedback"]
    improved_answer = eval_result["improved_answer"]
    followup_question = eval_result["followup_question"]

    # Associate with logged-in user if authenticated
    user_id = session.get("user_id")

    # Save to SQLite Database
    new_session = VivaSession(
        user_id=user_id,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        question=question,
        user_answer=user_answer,
        feedback=feedback,
        improved_answer=improved_answer,
        followup_question=followup_question,
        score=earned_score,
        total=max_score,
        time_taken_seconds=time_taken_seconds,
        hints_used=hints_used
    )
    db.session.add(new_session)
    db.session.commit()

    return render_template(
        "result.html",
        score=f"{earned_score}/{max_score}",
        raw_score=earned_score,
        total=max_score,
        feedback=feedback,
        improved_answer=improved_answer,
        followup_question=followup_question,
        question=question,
        answer=user_answer,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        time_taken_seconds=time_taken_seconds,
        hints_used=hints_used
    )


@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    sessions = VivaSession.query.filter_by(user_id=user_id).order_by(VivaSession.created_at.desc()).all()
    return render_template("history.html", sessions=sessions)


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    analytics, recommendation = analyze_user_weak_topics(user_id)
    recent_sessions = VivaSession.query.filter_by(user_id=user_id).order_by(VivaSession.created_at.desc()).limit(5).all()
    
    total_sessions = VivaSession.query.filter_by(user_id=user_id).count()
    avg_score = 0
    if total_sessions > 0:
        total_score = db.session.query(func.sum(VivaSession.score)).filter_by(user_id=user_id).scalar() or 0
        avg_score = round(total_score / total_sessions, 1)

    return render_template(
        "dashboard.html",
        analytics=analytics,
        recommendation=recommendation,
        recent_sessions=recent_sessions,
        total_sessions=total_sessions,
        avg_score=avg_score
    )


@app.route("/download-report")
@login_required
def download_report():
    user_id = session["user_id"]
    user = db.session.get(User, user_id)
    sessions = VivaSession.query.filter_by(user_id=user_id).order_by(VivaSession.created_at.desc()).all()
    analytics, study_plan = analyze_user_weak_topics(user_id)

    pdf_buffer = generate_pdf_report(user, sessions, analytics, study_plan)
    
    filename = f"viva_performance_report_{user.username}.pdf"
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


# --- Aliases & Conflict Compatibility Routes ---

@app.route("/viva", methods=["GET", "POST"])
def viva_alias():
    """Alias for practice route to satisfy ChatGPT/Gemini conflicting links."""
    return practice()

@app.route("/feedback")
def feedback_alias():
    """Alias for feedback/history route."""
    if "user_id" in session:
        return redirect(url_for("history"))
    return redirect(url_for("index"))

@app.route("/performance")
def performance_alias():
    """Alias for performance/dashboard route."""
    return redirect(url_for("dashboard"))

@app.route("/subjects")
def subjects_alias():
    """Alias for subjects selection view."""
    return redirect(url_for("index"))


# --- App Startup ---

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
