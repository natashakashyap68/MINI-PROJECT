import io
import unittest
from app import app, db, User, VivaSession

class VivaBotTestCase(unittest.TestCase):
    def setUp(self):
        # Configure test client with an in-memory SQLite database
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def register_user(self, username="testuser", email="test@example.com", password="password123"):
        return self.client.post("/register", data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password
        }, follow_redirects=True)

    def login_user(self, identifier="testuser", password="password123"):
        return self.client.post("/login", data={
            "identifier": identifier,
            "password": password
        }, follow_redirects=True)

    def logout_user(self):
        return self.client.get("/logout", follow_redirects=True)

    # ----------------------------------------------------
    # 1. Authentication Tests
    # ----------------------------------------------------
    def test_registration_and_login(self):
        # Test Registration
        response = self.register_user("alice", "alice@test.com", "secure123")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome to AI Viva Prep", response.data)

        # Verify user in database
        with app.app_context():
            user = User.query.filter_by(username="alice").first()
            self.assertIsNotNone(user)
            self.assertTrue(user.check_password("secure123"))

        # Test Logout
        logout_resp = self.logout_user()
        self.assertIn(b"You have been signed out safely", logout_resp.data)

        # Test Login
        login_resp = self.login_user("alice", "secure123")
        self.assertIn(b"Welcome back, alice", login_resp.data)

    def test_duplicate_registration_prevented(self):
        self.register_user("bob", "bob@test.com", "password123")
        self.logout_user()
        # Duplicate username
        resp1 = self.register_user("bob", "other@test.com", "password123")
        self.assertIn(b"Username is already taken", resp1.data)
        # Duplicate email
        resp2 = self.register_user("otherbob", "bob@test.com", "password123")
        self.assertIn(b"account with this email already exists", resp2.data)

    # ----------------------------------------------------
    # 2. Viva Generation & Hint API Tests
    # ----------------------------------------------------
    def test_practice_question_generation(self):
        self.register_user("charlie", "charlie@test.com", "password123")
        response = self.client.post("/practice", data={
            "subject": "Operating Systems",
            "difficulty": "Intermediate",
            "timed_mode": "on",
            "time_limit": "90"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Operating Systems", response.data)
        self.assertIn(b"Viva Examiner's Question", response.data)
        self.assertIn(b"Time Remaining", response.data)

    def test_progressive_hints_api(self):
        self.client.post("/practice", data={"subject": "Data Structures", "difficulty": "Intermediate"})
        # Request Hint 1
        hint1_resp = self.client.post("/api/hint", json={"hint_index": 0})
        self.assertEqual(hint1_resp.status_code, 200)
        data1 = hint1_resp.get_json()
        self.assertTrue(data1["success"])
        self.assertEqual(data1["hint_number"], 1)
        self.assertTrue(len(data1["hint"]) > 0)

        # Request Hint 2
        hint2_resp = self.client.post("/api/hint", json={"hint_index": 1})
        self.assertEqual(hint2_resp.status_code, 200)
        data2 = hint2_resp.get_json()
        self.assertTrue(data2["success"])
        self.assertEqual(data2["hint_number"], 2)

    # ----------------------------------------------------
    # 3. Answer Evaluation & Follow-up Questions
    # ----------------------------------------------------
    def test_submit_viva_answer_evaluation(self):
        self.register_user("diana", "diana@test.com", "password123")
        response = self.client.post("/submit", data={
            "subject": "Operating Systems",
            "topic": "Processes & Threads",
            "difficulty": "Intermediate",
            "question": "What is the difference between a process and a thread?",
            "user_answer": "A process is an execution unit with its own address space, whereas threads share the memory space of their parent process.",
            "time_taken_seconds": "45",
            "hints_used": "1"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Oral Viva Assessment & Feedback", response.data)
        self.assertIn(b"AI Examiner Evaluation", response.data)
        self.assertIn(b"Exemplary Model Viva Answer", response.data)
        self.assertIn(b"Examiner's Follow-Up Question", response.data)

        # Check that session is stored in DB with user_id
        with app.app_context():
            user = User.query.filter_by(username="diana").first()
            session_rec = VivaSession.query.filter_by(user_id=user.id).first()
            self.assertIsNotNone(session_rec)
            self.assertEqual(session_rec.subject, "Operating Systems")
            self.assertEqual(session_rec.time_taken_seconds, 45)
            self.assertEqual(session_rec.hints_used, 1)

    # ----------------------------------------------------
    # 4. User Scoping & History Isolation
    # ----------------------------------------------------
    def test_history_user_isolation(self):
        # Register User A and submit answer
        self.register_user("user_a", "a@test.com", "password123")
        self.client.post("/submit", data={
            "subject": "Data Structures",
            "topic": "Hash Maps",
            "difficulty": "Advanced",
            "question": "Explain Separate Chaining vs Open Addressing.",
            "user_answer": "Separate chaining stores collisions in linked lists.",
            "time_taken_seconds": "30",
            "hints_used": "0"
        })
        self.logout_user()

        # Register User B and verify they do not see User A's session
        self.register_user("user_b", "b@test.com", "password123")
        b_history = self.client.get("/history")
        self.assertNotIn(b"Separate Chaining vs Open Addressing", b_history.data)
        self.assertIn(b"No Viva Sessions Recorded Yet", b_history.data)

    # ----------------------------------------------------
    # 5. Dashboard, Weak Topic Detector & PDF Report
    # ----------------------------------------------------
    def test_dashboard_and_weak_topic_detection(self):
        self.register_user("evan", "evan@test.com", "password123")
        
        # Evan scores high in OS (10/10) and low in ML (3/10)
        with app.app_context():
            user = User.query.filter_by(username="evan").first()
            os_session = VivaSession(
                user_id=user.id,
                subject="Operating Systems",
                topic="Processes",
                difficulty="Intermediate",
                question="Processes vs Threads?",
                user_answer="Detailed correct answer...",
                feedback="Excellent",
                score=10,
                total=10
            )
            ml_session = VivaSession(
                user_id=user.id,
                subject="Machine Learning",
                topic="Overfitting",
                difficulty="Intermediate",
                question="What is overfitting?",
                user_answer="Poor answer",
                feedback="Incomplete",
                score=3,
                total=10
            )
            db.session.add_all([os_session, ml_session])
            db.session.commit()

        # Access Dashboard
        dash_resp = self.client.get("/dashboard")
        self.assertEqual(dash_resp.status_code, 200)
        # Weakest subject should be detected as Machine Learning
        self.assertIn(b"Machine Learning", dash_resp.data)
        self.assertIn(b"Target Focus Area", dash_resp.data)

        # Test PDF Performance Report Generation
        pdf_resp = self.client.get("/download-report")
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp.mimetype, "application/pdf")
        self.assertTrue(len(pdf_resp.data) > 1000)
        self.assertTrue(pdf_resp.data.startswith(b"%PDF"))

    # ----------------------------------------------------
    # 6. Compatibility Route Aliases
    # ----------------------------------------------------
    def test_route_aliases(self):
        # /viva alias
        viva_resp = self.client.get("/viva")
        self.assertEqual(viva_resp.status_code, 200)

        # /performance alias redirects to /dashboard
        self.register_user("fiona", "fiona@test.com", "password123")
        perf_resp = self.client.get("/performance")
        self.assertEqual(perf_resp.status_code, 302)
        self.assertIn("/dashboard", perf_resp.headers["Location"])

        # /subjects view
        sub_resp = self.client.get("/subjects")
        self.assertEqual(sub_resp.status_code, 302)

if __name__ == "__main__":
    unittest.main()

