



#!/usr/bin/env python3


import sqlite3
import hashlib
import secrets
import json
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

# =============================================================================
# DATABASE SETUP
# =============================================================================

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect('skillconnect.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with all tables and seed data"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop tables if they exist (for clean start)
    cursor.executescript('''
        DROP TABLE IF EXISTS chat_messages;
        DROP TABLE IF EXISTS saved_internships;
        DROP TABLE IF EXISTS applications;
        DROP TABLE IF EXISTS internship_skills;
        DROP TABLE IF EXISTS internships;
        DROP TABLE IF EXISTS student_skills;
        DROP TABLE IF EXISTS skills;
        DROP TABLE IF EXISTS companies;
        DROP TABLE IF EXISTS users;
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            college_tier TEXT,
            college_name TEXT,
            year INTEGER,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create companies table
    cursor.execute('''
        CREATE TABLE companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            industry TEXT,
            website TEXT,
            location TEXT,
            logo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create skills table
    cursor.execute('''
        CREATE TABLE skills (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create internships table
    cursor.execute('''
        CREATE TABLE internships (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            type TEXT NOT NULL,
            duration INTEGER NOT NULL,
            stipend INTEGER,
            posted_by_id TEXT NOT NULL,
            company_id TEXT,
            status TEXT DEFAULT 'ACTIVE',
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by_id) REFERENCES users(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    ''')

    # Create internship_skills table (many-to-many)
    cursor.execute('''
        CREATE TABLE internship_skills (
            id TEXT PRIMARY KEY,
            internship_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (internship_id) REFERENCES internships(id),
            FOREIGN KEY (skill_id) REFERENCES skills(id),
            UNIQUE(internship_id, skill_id)
        )
    ''')

    # Create applications table
    cursor.execute('''
        CREATE TABLE applications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            internship_id TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            cover_letter TEXT,
            resume_url TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (internship_id) REFERENCES internships(id),
            UNIQUE(user_id, internship_id)
        )
    ''')

    # Create student_skills table (many-to-many)
    cursor.execute('''
        CREATE TABLE student_skills (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            proficiency INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (skill_id) REFERENCES skills(id),
            UNIQUE(user_id, skill_id)
        )
    ''')

    # Create saved_internships table
    cursor.execute('''
        CREATE TABLE saved_internships (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            internship_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (internship_id) REFERENCES internships(id),
            UNIQUE(user_id, internship_id)
        )
    ''')

    # Create chat_messages table
    cursor.execute('''
        CREATE TABLE chat_messages (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            is_user BOOLEAN DEFAULT 1,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Seed data
    # Create companies
    companies = [
        ('c1', 'TechStart Solutions', 'A dynamic startup focused on building innovative software solutions for small businesses.', 'Technology', 'https://techstart.example.com', 'Bangalore', None),
        ('c2', 'Digital Innovations Inc', 'Leading digital transformation company helping businesses go digital.', 'Technology', 'https://digitalinnovations.example.com', 'Hyderabad', None),
        ('c3', 'CloudTech Systems', 'Cloud infrastructure and services provider for enterprise clients.', 'Cloud Computing', 'https://cloudtech.example.com', 'Remote', None),
    ]
    cursor.executemany('INSERT INTO companies (id, name, description, industry, website, location, logo) VALUES (?, ?, ?, ?, ?, ?, ?)', companies)

    # Create skills
    skills = [
        ('s1', 'JavaScript', 'Technical'),
        ('s2', 'Python', 'Technical'),
        ('s3', 'React', 'Technical'),
        ('s4', 'Node.js', 'Technical'),
        ('s5', 'SQL', 'Technical'),
        ('s6', 'Machine Learning', 'Technical'),
        ('s7', 'Data Analysis', 'Technical'),
        ('s8', 'Problem Solving', 'Soft Skills'),
        ('s9', 'Communication', 'Soft Skills'),
        ('s10', 'Teamwork', 'Soft Skills'),
        ('s11', 'HTML/CSS', 'Technical'),
        ('s12', 'TypeScript', 'Technical'),
    ]
    cursor.executemany('INSERT INTO skills (id, name, category) VALUES (?, ?, ?)', skills)

    # Create recruiter user
    recruiter_id = 'u1'
    recruiter_password = hash_password('password123')
    cursor.execute('''
        INSERT INTO users (id, email, password, name, role, bio)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (recruiter_id, 'recruiter@techstart.com', recruiter_password, 'Priya Sharma', 'RECRUITER', 'Recruiter at TechStart, passionate about finding diverse talent.'))

    # Create internships
    internships = [
        ('i1', 'Frontend Developer Intern', 'We are looking for a passionate Frontend Developer Intern to join our team. You will work on building user-friendly interfaces using React and modern web technologies. This is a great opportunity to learn from experienced developers and work on real-world projects.', 'Remote', 'REMOTE', 3, 15000, recruiter_id, 'c1'),
        ('i2', 'Python Backend Developer Intern', 'Join our backend team and work on building scalable APIs and services. You will gain hands-on experience with Python, Django, and database management. Ideal for students who love server-side development and want to build robust applications.', 'Bangalore', 'HYBRID', 6, 20000, recruiter_id, 'c1'),
        ('i3', 'Data Science Intern', 'Exciting opportunity for students interested in Data Science and Machine Learning. Work on real datasets, build predictive models, and help businesses make data-driven decisions. Strong foundation in Python and mathematics required.', 'Remote', 'REMOTE', 4, 18000, recruiter_id, 'c2'),
        ('i4', 'Full Stack Developer Intern', 'Looking for enthusiastic developers to work on full-stack web applications. You will get exposure to both frontend and backend technologies, including React, Node.js, and databases. Perfect opportunity to become a well-rounded developer.', 'Hyderabad', 'FULL_TIME', 6, 22000, recruiter_id, 'c2'),
        ('i5', 'Cloud Computing Intern', 'Join our cloud team and learn about cloud infrastructure, deployment, and DevOps practices. Work with AWS services, containerization, and CI/CD pipelines. Great for students interested in cloud technologies and DevOps.', 'Remote', 'REMOTE', 3, 17000, recruiter_id, 'c3'),
        ('i6', 'Junior Developer Intern - Web', 'Entry-level position for motivated students to learn web development. No prior experience required - just passion for coding and willingness to learn. We provide mentorship and training. Start your career with us!', 'Bangalore', 'FULL_TIME', 4, 12000, recruiter_id, 'c1'),
        ('i7', 'ML Research Intern', 'Work on cutting-edge machine learning research projects. Collaborate with senior researchers, implement algorithms, and contribute to publications. Strong math and Python background preferred.', 'Remote', 'REMOTE', 6, 25000, recruiter_id, 'c3'),
        ('i8', 'Mobile App Development Intern', 'Develop mobile applications using modern frameworks. Work on both iOS and Android platforms. Learn about mobile UI/UX, app deployment, and app store optimization.', 'Hyderabad', 'HYBRID', 3, 16000, recruiter_id, 'c2'),
    ]
    cursor.executemany('''
        INSERT INTO internships (id, title, description, location, type, duration, stipend, posted_by_id, company_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', internships)

    # Link skills to internships
    internship_skills = [
        ('is1', 'i1', 's1'), ('is2', 'i1', 's3'), ('is3', 'i1', 's11'), ('is4', 'i1', 's12'),
        ('is5', 'i2', 's2'), ('is6', 'i2', 's5'), ('is7', 'i2', 's8'),
        ('is8', 'i3', 's2'), ('is9', 'i3', 's6'), ('is10', 'i3', 's7'), ('is11', 'i3', 's5'),
        ('is12', 'i4', 's1'), ('is13', 'i4', 's3'), ('is14', 'i4', 's4'), ('is15', 'i4', 's5'),
        ('is16', 'i5', 's8'), ('is17', 'i5', 's10'), ('is18', 'i5', 's9'),
        ('is19', 'i6', 's8'), ('is20', 'i6', 's9'), ('is21', 'i6', 's10'), ('is22', 'i6', 's11'),
        ('is23', 'i7', 's2'), ('is24', 'i7', 's6'), ('is25', 'i7', 's8'),
        ('is26', 'i8', 's1'), ('is27', 'i8', 's8'), ('is28', 'i8', 's10'),
    ]
    cursor.executemany('INSERT INTO internship_skills (id, internship_id, skill_id) VALUES (?, ?, ?)', internship_skills)

    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_id():
    """Generate unique ID"""
    return secrets.token_hex(16)

# =============================================================================
# AUTHENTICATION DECORATORS
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
           return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# AI CHATBOT KNOWLEDGE BASE
# =============================================================================

CHAT_KNOWLEDGE = {
    'resume': [
        "Keep your resume concise - ideally 1-2 pages",
        "Use action verbs like 'developed', 'implemented', 'achieved'",
        "Quantify your achievements with numbers where possible",
        "Tailor your resume to each job description",
        "Include relevant projects and internships",
        "Use a clean, professional format",
        "Proofread multiple times for errors",
        "Include your technical skills prominently",
    ],
    'interview': [
        "Research the company thoroughly before the interview",
        "Practice common interview questions out loud",
        "Prepare examples using the STAR method (Situation, Task, Action, Result)",
        "Ask thoughtful questions to the interviewer",
        "Dress professionally even for video interviews",
        "Test your technology beforehand for remote interviews",
        "Be authentic and honest about your skills",
        "Follow up with a thank you email within 24 hours",
    ],
    'skills': [
        "Focus on in-demand skills like Python, JavaScript, React, Node.js",
        "Build personal projects to demonstrate your skills",
        "Contribute to open-source projects",
        "Practice coding problems on platforms like LeetCode",
        "Learn cloud platforms like AWS or Azure",
        "Understand database fundamentals",
        "Develop soft skills like communication and teamwork",
        "Stay updated with industry trends",
    ],
    'internship': [
        "Start applying early - 2-3 months before you want to start",
        "Apply to 10-15 internships for best results",
        "Network with alumni and professionals",
        "Attend career fairs and company events",
        "Use your college career center resources",
        "Follow up on applications after 1-2 weeks",
        "Don't get discouraged by rejections",
        "Learn from each interview experience",
    ],
    'tier23': [
        "Your skills matter more than your college tier",
        "Many companies actively seek diverse talent from all colleges",
        "Build a strong portfolio of projects",
        "Get certifications to validate your skills",
        "Participate in hackathons and coding competitions",
        "Leverage LinkedIn to connect with professionals",
        "Consider starting with smaller companies for experience",
        "Remote opportunities have opened more doors",
    ],
}

def get_chatbot_response(message, history):
    """Get response from AI chatbot based on local knowledge base"""
    message_lower = message.lower()

    # Determine relevant context
    context = None
    if any(word in message_lower for word in ['resume', 'cv', 'curriculum']):
        context = 'resume'
    elif any(word in message_lower for word in ['interview', 'interviewing', 'question']):
        context = 'interview'
    elif any(word in message_lower for word in ['skill', 'learn', 'technology', 'programming', 'coding']):
        context = 'skills'
    elif any(word in message_lower for word in ['internship', 'apply', 'application', 'job']):
        context = 'internship'
    elif any(word in message_lower for word in ['tier', 'college', 'location', 'college tier']):
        context = 'tier23'

    # Build response based on context
    if context:
        tips = CHAT_KNOWLEDGE[context]
        selected_tips = tips[:3] if len(tips) > 3 else tips
        response = f"Based on your question about {context}, here are some tips:\n\n"
        response += "\n".join(f"• {tip}" for tip in selected_tips)
        response += "\n\nIs there anything specific you'd like to know more about?"
    else:
        response = ("I'm here to help you with your career journey! You can ask me about:\n\n"
                   "• Resume writing tips\n"
                   "• Interview preparation\n"
                   "• Skill development\n"
                   "• Internship advice\n"
                   "• Tips for Tier-2 and Tier-3 college students\n\n"
                   "What would you like to know more about?")

    return response

# =============================================================================
# HTML TEMPLATES
# =============================================================================

BASE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkillConnect - Internship Matching Platform</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary: #8b5cf6;
            --primary-dark: #7c3aed;
            --secondary: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #1f2937;
            --light: #f9fafb;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f5f3ff 0%, #ffffff 50%, #eff6ff 100%);
            min-height: 100vh;
        }

        .navbar {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 1000;
        }

        .navbar-brand {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .btn-primary {
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            border: none;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        }

        .card {
            border: none;
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            transition: all 0.3s ease;
            overflow: hidden;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }

        .card-header {
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            color: white;
            border: none;
        }

        .badge {
            padding: 0.35rem 0.75rem;
            border-radius: 0.5rem;
            font-weight: 500;
        }

        .badge-primary { background: var(--primary); color: white; }
        .badge-secondary { background: var(--secondary); color: white; }
        .badge-success { background: var(--success); color: white; }
        .badge-outline { border: 2px solid var(--primary); color: var(--primary); }

        .hero-section {
            padding: 4rem 1rem;
            text-align: center;
        }

        .hero-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 50%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .feature-card {
            padding: 2rem;
            text-align: center;
            height: 100%;
        }

        .feature-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            color: var(--primary);
        }

        .internship-card {
            border: 2px solid #e5e7eb;
        }

        .internship-card:hover {
            border-color: var(--primary);
        }

        .skill-badge {
            background: #f3f4f6;
            color: #4b5563;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.875rem;
            margin: 0.25rem;
            display: inline-block;
        }

        .stat-card {
            padding: 1.5rem;
            text-align: center;
            border-radius: 1rem;
            background: white;
            border: 2px solid #e5e7eb;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

/* Chatbot Styles */
        .chatbot-toggle {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 3.5rem;
            height: 3.5rem;
            border-radius: 50%;
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
            z-index: 1001;
            font-size: 1.5rem;
            transition: all 0.3s ease;
        }

        .chatbot-toggle:hover {
            transform: scale(1.1);
        }

        .chatbot-window {
            position: fixed;
            bottom: 7rem;
            right: 2rem;
            width: 400px;
            height: 500px;
            background: white;
            border-radius: 1rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            z-index: 1000;
            display: none;
            flex-direction: column;
        }

        .chatbot-window.active {
            display: flex;
        }

        .chatbot-header {
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            color: white;
            padding: 1rem;
            border-radius: 1rem 1rem 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chatbot-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            background: #f9fafb;
        }

        .chat-message {
            margin-bottom: 1rem;
            display: flex;
        }

        .chat-message.user {
            justify-content: flex-end;
        }

        .chat-message.bot {
            justify-content: flex-start;
        }

        .chat-bubble {
            max-width: 80%;
            padding: 0.75rem 1rem;
            border-radius: 1rem;
            font-size: 0.875rem;
            line-height: 1.5;
        }

        .chat-message.user .chat-bubble {
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            color: white;
            border-radius: 1rem 0 1rem 1rem;
        }

        .chat-message.bot .chat-bubble {
            background: #e5e7eb;
            color: #1f2937;
            border-radius: 0 1rem 1rem 1rem;
        }

        .chatbot-input {
            padding: 1rem;
            border-top: 1px solid #e5e7eb;
            display: flex;
            gap: 0.5rem;
        }

        .chatbot-input input {
            flex: 1;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            outline: none;
        }

        .chatbot-input input:focus {
            border-color: var(--primary);
        }

        .chatbot-input button {
            background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
            color: white;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 0.5rem;
            cursor: pointer;
        }

        footer {
            background: #1f2937;
            color: white;
            padding: 3rem 1rem;
            text-align: center;
        }

        @media (max-width: 768px) {
            .hero-title { font-size: 1.8rem; }
            .chatbot-window { width: 90%; right: 5%; }
        }

        .loading-spinner {
            border: 3px solid #f3f4f6;
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center">
                <a href="/" class="navbar-brand text-decoration-none">
                    <i class="fas fa-graduation-cap me-2"></i>SkillConnect
                </a>
                {% if session.get('user_id') %}
                    <div class="d-flex align-items-center gap-3">
                        <a href="/profile" class="nav-link text-dark fw-bold">My Profile</a>
                        <span class="badge badge-secondary">{{ session.get('role') }}</span>
                        <a href="/logout" class="btn btn-outline-dark btn-sm">Logout</a>
                    </div>
                {% else %}
                    <span class="badge badge-secondary d-none d-md-block">Open Source & Free</span>
                {% endif %}
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main>
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer>
        <div class="container">
            <p class="mb-0">
                <i class="fas fa-graduation-cap me-2"></i>
                SkillConnect • Open Source • Free • Empowering Students
            </p>
        </div>
    </footer>

    <!-- Chatbot Toggle -->
    <button class="chatbot-toggle" onclick="toggleChatbot()">
        <i class="fas fa-comment-dots"></i>
    </button>

    <!-- Chatbot Window -->
    <div class="chatbot-window" id="chatbotWindow">
        <div class="chatbot-header">
            <h5 class="mb-0"><i class="fas fa-robot me-2"></i>AI Career Assistant</h5>
            <button class="btn-close btn-close-white" onclick="toggleChatbot()"></button>
        </div>
        <div class="chatbot-messages" id="chatMessages">
            <div class="text-center py-4">
                <i class="fas fa-robot fa-3x mb-3" style="color: var(--primary);"></i>
                <p class="text-muted">Hi! I'm your AI Career Assistant.</p>
                <p class="small text-muted">Ask me about resume tips, interview prep, career advice...</p>
            </div>
        </div>
        <div class="chatbot-input">
            <input type="text" id="chatInput" placeholder="Type your question..." onkeypress="handleChatKeyPress(event)">
            <button onclick="sendMessage()"><i class="fas fa-paper-plane"></i></button>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function toggleChatbot() {
            const chatbot = document.getElementById('chatbotWindow');
            chatbot.classList.toggle('active');
        }

        function handleChatKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if (!message) return;

            const messagesDiv = document.getElementById('chatMessages');

            // Add user message
            const userMsg = document.createElement('div');
            userMsg.className = 'chat-message user';
            userMsg.innerHTML = `<div class="chat-bubble">${message}</div>`;
            messagesDiv.appendChild(userMsg);

            input.value = '';

            // Show loading
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'chat-message bot';
            loadingMsg.id = 'loadingMsg';
            loadingMsg.innerHTML = `<div class="chat-bubble"><div class="loading-spinner"></div></div>`;
            messagesDiv.appendChild(loadingMsg);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();

                // Remove loading and add bot response
                document.getElementById('loadingMsg').remove();
                const botMsg = document.createElement('div');
                botMsg.className = 'chat-message bot';
                botMsg.innerHTML = `<div class="chat-bubble" style="white-space: pre-line;">${data.response}</div>`;
                messagesDiv.appendChild(botMsg);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;

            } catch (error) {
                document.getElementById('loadingMsg').remove();
                const errorMsg = document.createElement('div');
                errorMsg.className = 'chat-message bot';
                errorMsg.innerHTML = `<div class="chat-bubble">Sorry, I encountered an error. Please try again.</div>`;
                messagesDiv.appendChild(errorMsg);
            }
        }

        function applyToInternship(internshipId) {
            fetch('/api/apply', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ internship_id: internshipId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Application submitted successfully!');
                    location.reload();
                } else {
                    alert(data.error || 'Failed to apply');
                }
            })
            .catch(error => alert('Something went wrong'));
        }
    </script>
</body>
</html>
'''

HOME_TEMPLATE = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <section class="hero-section">
        <div class="container">
            <span class="badge badge-secondary mb-3">🎓 Bridging Education & Industry</span>
            <h1 class="hero-title mb-4">Internships for Every Student</h1>
            <p class="lead mb-4" style="max-width: 800px; margin: 0 auto;">
                Skill-based matching platform that connects talented Tier-2 & Tier-3 college students
                with quality internship opportunities. No more location barriers!
            </p>
            <div class="d-flex flex-wrap justify-content-center gap-3 mb-5">
                <span class="badge badge-primary"><i class="fas fa-check me-2"></i>Free to Use</span>
                <span class="badge badge-secondary"><i class="fas fa-check me-2"></i>Open Source</span>
                <span class="badge badge-success"><i class="fas fa-check me-2"></i>Works Offline</span>
            </div>
        </div>
    </section>

    <section class="py-5">
        <div class="container">
            <div class="row g-4 justify-content-center">
                <div class="col-md-6 col-lg-3">
                    <div class="card feature-card">
                        <i class="fas fa-brain feature-icon"></i>
                        <h4>AI Career Assistant</h4>
                        <p class="text-muted">24/7 AI chatbot for resume tips, interview prep, and career guidance</p>
                    </div>
                </div>
                <div class="col-md-6 col-lg-3">
                    <div class="card feature-card">
                        <i class="fas fa-shield-alt feature-icon" style="color: var(--secondary);"></i>
                        <h4>Skill-Based Matching</h4>
                        <p class="text-muted">Get matched based on your skills, not your college location</p>
                    </div>
                </div>
                <div class="col-md-6 col-lg-3">
                    <div class="card feature-card">
                        <i class="fas fa-globe feature-icon" style="color: var(--success);"></i>
                        <h4>Remote Opportunities</h4>
                        <p class="text-muted">Access to remote internships from companies worldwide</p>
                    </div>
                </div>
                <div class="col-md-6 col-lg-3">
                    <div class="card feature-card">
                        <i class="fas fa-users feature-icon" style="color: var(--warning);"></i>
                        <h4>Equal Opportunity</h4>
                        <p class="text-muted">Breaking barriers for Tier-2 & Tier-3 college students</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section class="py-5">
        <div class="container" style="max-width: 500px;">
            <div class="card shadow-lg border-2">
                <div class="card-header">
                    <h4 class="mb-0 text-center">Welcome to SkillConnect</h4>
                    <p class="mb-0 text-center opacity-75">Your gateway to internship opportunities</p>
                </div>
                <div class="card-body">
                    <ul class="nav nav-pills mb-4 justify-content-center" id="authTabs" role="tablist">
                        <li class="nav-item">
                            <button class="nav-link active" data-bs-toggle="pill" data-bs-target="#login" type="button">Login</button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" data-bs-toggle="pill" data-bs-target="#signup" type="button">Sign Up</button>
                        </li>
                    </ul>


                    <div class="tab-content" id="authTabContent">
                        <!-- Login Form -->
                        <div class="tab-pane fade show active" id="login">
                            <form action="/login" method="POST">
                                <div class="mb-3">
                                    <label class="form-label">Email</label>
                                    <input type="email" name="email" class="form-control" placeholder="your.email@example.com" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Password</label>
                                    <input type="password" name="password" class="form-control" placeholder="••••••••" required>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Login</button>
                            </form>
                        </div>

                        <!-- Signup Form -->
                        <div class="tab-pane fade" id="signup">
                            <form action="/signup" method="POST">
                                <div class="mb-3">
                                    <label class="form-label">Full Name</label>
                                    <input type="text" name="name" class="form-control" placeholder="John Doe" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Email</label>
                                    <input type="email" name="email" class="form-control" placeholder="your.email@example.com" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Password</label>
                                    <input type="password" name="password" class="form-control" placeholder="••••••••" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">I am a</label>
                                    <select name="role" class="form-select" onchange="toggleStudentFields(this.value)">
                                        <option value="STUDENT">Student</option>
                                        <option value="RECRUITER">Recruiter</option>
                                    </select>
                                </div>
                                <div id="studentFields">
                                    <div class="mb-3">
                                        <label class="form-label">College Tier</label>
                                        <select name="college_tier" class="form-select">
                                            <option value="TIER_1">Tier 1</option>
                                            <option value="TIER_2" selected>Tier 2</option>
                                            <option value="TIER_3">Tier 3</option>
                                            <option value="OTHER">Other</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">College Name</label>
                                        <input type="text" name="college_name" class="form-control" placeholder="Your College Name">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Current Year</label>
                                        <select name="year" class="form-select">
                                            <option value="1">1st Year</option>
                                            <option value="2">2nd Year</option>
                                            <option value="3" selected>3rd Year</option>
                                            <option value="4">4th Year</option>
                                        </select>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Create Account</button>
                            </form>
                        </div>
                    </div>
                </div>
                <div class="card-footer text-center text-muted small">
                    By continuing, you agree to our Terms of Service and Privacy Policy
                </div>
            </div>
        </div>
    </section>

    <section class="py-5 bg-white">
        <div class="container">
            <h2 class="text-center mb-5">How It Works</h2>
            <div class="row g-4">
                <div class="col-md-4">
                    <div class="card text-center border-2">
                        <div class="card-body">
                            <div class="display-6 fw-bold mb-3" style="color: var(--primary);">1</div>
                            <h5>Create Your Profile</h5>
                            <p class="text-muted">Sign up, add your skills, and build your profile</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center border-2">
                        <div class="card-body">
                            <div class="display-6 fw-bold mb-3" style="color: var(--secondary);">2</div>
                            <h5>Get Matched</h5>
                            <p class="text-muted">Our AI recommends internships based on your skills</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center border-2">
                        <div class="card-body">
                            <div class="display-6 fw-bold mb-3" style="color: var(--success);">3</div>
                            <h5>Apply & Grow</h5>
                            <p class="text-muted">Apply to opportunities and kickstart your career</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <script>
        function toggleStudentFields(role) {
            const studentFields = document.getElementById('studentFields');
            studentFields.style.display = role === 'STUDENT' ? 'block' : 'none';
        }

        // Initialize student fields visibility
        document.addEventListener('DOMContentLoaded', function() {
            const roleSelect = document.querySelector('select[name="role"]');
            if (roleSelect) {
                toggleStudentFields(roleSelect.value);
            }
        });
  </script>
''')

DASHBOARD_TEMPLATE = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <section class="py-5">
        <div class="container">
            <h1 class="mb-2">Welcome back, {{ user.name }}! 👋</h1>
            <p class="text-muted mb-4">
                {% if user.role == 'STUDENT' %}
                    Explore internships matched to your skills
                {% else %}
                    Manage your internship postings
                {% endif %}
            </p>

            <!-- Stats -->
            <div class="row g-4 mb-5">
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.internships }}</div>
                        <h5 class="mb-0">Available Internships</h5>
                        <small class="text-muted"><i class="fas fa-briefcase me-1"></i>Total</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.remote }}</div>
                        <h5 class="mb-0">Remote</h5>
                        <small class="text-muted"><i class="fas fa-globe me-1"></i>Opportunities</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.skills }}</div>
                        <h5 class="mb-0">Skills</h5>
                        <small class="text-muted"><i class="fas fa-bolt me-1"></i>Required</small>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.companies }}</div>
                        <h5 class="mb-0">Companies</h5>
                        <small class="text-muted"><i class="fas fa-building me-1"></i>Hiring</small>
                    </div>
                </div>
            </div>

            <!-- Search and Filters -->
            <div class="card mb-4 border-2">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-search me-2"></i>Find Your Perfect Internship</h5>
            </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-5">
                            <label class="form-label">Search</label>
                            <input type="text" id="searchInput" class="form-control" placeholder="Search by title or description..." oninput="filterInternships()">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Type</label>
                            <select id="typeFilter" class="form-select" onchange="filterInternships()">
                                <option value="all">All Types</option>
                                <option value="REMOTE">Remote</option>
                                <option value="FULL_TIME">Full Time</option>
                                <option value="PART_TIME">Part Time</option>
                                <option value="HYBRID">Hybrid</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Location</label>
                            <select id="locationFilter" class="form-select" onchange="filterInternships()">
                                <option value="all">All Locations</option>
                                <option value="Remote">Remote</option>
                                <option value="Bangalore">Bangalore</option>
                                <option value="Hyderabad">Hyderabad</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Internship Listings -->
            <h2 class="mb-4">Available Internships</h2>
            <div id="internshipList">
                {% if internships %}
                    {% for internship in internships %}
                    <div class="card mb-3 internship-card" data-title="{{ internship.title|lower }}" data-description="{{ internship.description|lower }}" data-type="{{ internship.type }}" data-location="{{ internship.location }}">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-3">
                                <div>
                                    <h5 class="mb-1">{{ internship.title }}</h5>
                                    <p class="text-muted mb-0"><strong>{{ internship.company_name }}</strong></p>
                                </div>
                                <span class="badge badge-primary">{{ internship.type }}</span>
                            </div>
                            <p class="text-muted mb-3">{{ internship.description[:200] }}...</p>
                            <div class="d-flex flex-wrap gap-4 mb-3">
                                <span class="text-muted small"><i class="fas fa-map-marker-alt me-1"></i>{{ internship.location }}</span>
                                <span class="text-muted small"><i class="fas fa-clock me-1"></i>{{ internship.duration }} months</span>
                                {% if internship.stipend %}
                                    <span class="text-muted small"><i class="fas fa-rupee-sign me-1"></i>{{ internship.stipend }} /month</span>
                                {% endif %}
                            </div>
                            <div class="mb-3">
                                {% for skill in internship.skills %}
                                    <span class="skill-badge">{{ skill.name }}</span>
                                {% endfor %}
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-muted small">{{ internship.applications }} applicants</span>
                                {% if user.role == 'STUDENT' %}
                                    <button class="btn btn-primary" onclick="applyToInternship('{{ internship.id }}')">
                                        Apply Now <i class="fas fa-arrow-right ms-2"></i>
                                    </button>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="card text-center py-5">
                        <i class="fas fa-briefcase fa-4x text-muted mb-3"></i>
                        <p class="text-muted">No internships found matching your criteria.</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </section>

    <script>
        const internshipsData = {{ internships|tojson }};
        let filteredInternships = internshipsData;

        function filterInternships() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            const type = document.getElementById('typeFilter').value;
            const location = document.getElementById('locationFilter').value;

            filteredInternships = internshipsData.filter(internship => {
                const matchesSearch = !search ||
                    internship.title.toLowerCase().includes(search) ||
                    internship.description.toLowerCase().includes(search);
                const matchesType = type === 'all' || internship.type === type;
                const matchesLocation = location === 'all' || internship.location === location;

                return matchesSearch && matchesType && matchesLocation;
            });

            renderInternships();
        }

        function renderInternships() {
            const container = document.getElementById('internshipList');

            if (filteredInternships.length === 0) {
                container.innerHTML = `
                    <div class="card text-center py-5">
                        <i class="fas fa-briefcase fa-4x text-muted mb-3"></i>
                        <p class="text-muted">No internships found matching your criteria.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = filteredInternships.map(internship => `
                <div class="card mb-3 internship-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <div>
                                <h5 class="mb-1">${internship.title}</h5>
                                <p class="text-muted mb-0"><strong>${internship.company_name}</strong></p>
                            </div>
                            <span class="badge badge-primary">${internship.type}</span>
                        </div>
                        <p class="text-muted mb-3">${internship.description.substring(0, 200)}...</p>
                        <div class="d-flex flex-wrap gap-4 mb-3">
                            <span class="text-muted small"><i class="fas fa-map-marker-alt me-1"></i>${internship.location}</span>
                            <span class="text-muted small"><i class="fas fa-clock me-1"></i>${internship.duration} months</span>
                            ${internship.stipend ? `<span class="text-muted small"><i class="fas fa-rupee-sign me-1"></i>${internship.stipend} /month</span>` : ''}
                        </div>
                        <div class="mb-3">
                            ${internship.skills.map(skill => `<span class="skill-badge">${skill.name}</span>`).join('')}
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-muted small">${internship.applications} applicants</span>
                            <button class="btn btn-primary" onclick="applyToInternship('${internship.id}')">
                                Apply Now <i class="fas fa-arrow-right ms-2"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    </script>
''')

# PROFILE TEMPLATE ADDED HERE
PROFILE_TEMPLATE = BASE_HTML.replace('{% block content %}{% endblock %}', '''
    <section class="py-5">
        <div class="container">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1>My Profile</h1>
                <a href="/dashboard" class="btn btn-outline-primary">
                    <i class="fas fa-arrow-left me-2"></i>Back to Dashboard
                </a>
            </div>

            <div class="row g-4">
                <!-- User Details Card -->
                <div class="col-lg-4">
                    <div class="card shadow-sm h-100">
                        <div class="card-header bg-white border-bottom-0 pt-4 text-center">
                            <div class="mb-3 rounded-circle d-inline-flex align-items-center justify-content-center" 
                                 style="width: 100px; height: 100px; background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%); color: white; font-size: 2.5rem; font-weight: bold;">
                                {{ user.name[0]|upper }}
                            </div>
                            <h4 class="mb-1">{{ user.name }}</h4>
                            <span class="badge badge-primary mb-3">{{ user.role }}</span>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="text-muted small fw-bold text-uppercase">Email Address</label>
                                <p class="mb-0">{{ user.email }}</p>
                            </div>
                            <hr>
                            {% if user.role == 'STUDENT' %}
                            <div class="mb-3">
                                <label class="text-muted small fw-bold text-uppercase">College Tier</label>
                                <p class="mb-0">
                                    {% if user.college_tier %}{{ user.college_tier }}{% else %}N/A{% endif %}
                                </p>
                            </div>
                            <div class="mb-3">
                                <label class="text-muted small fw-bold text-uppercase">College Name</label>
                                <p class="mb-0">
                                    {% if user.college_name %}{{ user.college_name }}{% else %}N/A{% endif %}
                                </p>
                            </div>
                            <div class="mb-3">
                                <label class="text-muted small fw-bold text-uppercase">Current Year</label>
                                <p class="mb-0">
                                    {% if user.year %}Year {{ user.year }}{% else %}N/A{% endif %}
                                </p>
                            </div>
                            {% endif %}
                            
                            <div class="mt-4 p-3 bg-light rounded text-center">
                                <h2 class="fw-bold mb-0" style="color: var(--primary);">{{ applied_count }}</h2>
                                <small class="text-muted">Applications Submitted</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Application History -->
                <div class="col-lg-8">
                    <div class="card shadow-sm h-100">
                        <div class="card-header bg-white">
                            <h5 class="mb-0"><i class="fas fa-history me-2"></i>Application History</h5>
                        </div>
                        <div class="card-body">
                            {% if applications %}
                                <div class="table-responsive">
                                    <table class="table table-hover align-middle">
                                        <thead class="table-light">
                                            <tr>
                                                <th>Company</th>
                                                <th>Role</th>
                                                <th>Date Applied</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for app in applications %}
                                            <tr>
                                                <td class="fw-bold text-primary">{{ app.company_name }}</td>
                                                <td>{{ app.title }}</td>
                                                <td class="text-muted small">{{ app.applied_at[:10] }}</td>
                                                <td>
                                                    <span class="badge 
                                                        {% if app.status == 'PENDING' %}bg-warning text-dark
                                                        {% elif app.status == 'ACCEPTED' %}bg-success
                                                        {% elif app.status == 'REJECTED' %}bg-danger
                                                        {% else %}bg-secondary
                                                        {% endif %}">
                                                        {{ app.status }}
                                                    </span>
                                                </td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            {% else %}
                                <div class="text-center py-5">
                                    <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
                                    <h5 class="text-muted">No Applications Yet</h5>
                                    <p class="text-muted">Start exploring internships and apply to your dream jobs!</p>
                                    <a href="/dashboard" class="btn btn-primary mt-2">Browse Internships</a>
                                </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
''')

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def home():
    """Home page with login/signup"""
    return render_template_string(HOME_TEMPLATE)

@app.route('/signup', methods=['POST'])
def signup():
    """Handle user signup"""
    try:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            flash('Email already registered', 'error')
            return redirect(url_for('home'))

        # Create user
        user_id = generate_id()
        hashed_password = hash_password(password)

        if role == 'STUDENT':
            college_tier = request.form.get('college_tier')
            college_name = request.form.get('college_name')
            year = request.form.get('year')

            cursor.execute('''
                INSERT INTO users (id, email, password, name, role, college_tier, college_name, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, email, hashed_password, name, role, college_tier, college_name, year))
        else:
            cursor.execute('''
                INSERT INTO users (id, email, password, name, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, email, hashed_password, name, role))

        conn.commit()
        conn.close()

        session['user_id'] = user_id
        session['name'] = name
        session['role'] = role

        flash('Account created successfully! Welcome aboard.', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'Error creating account: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            flash('Invalid credentials', 'error')
            return redirect(url_for('home'))

        hashed_password = hash_password(password)
        if user['password'] != hashed_password:
            flash('Invalid credentials', 'error')
            return redirect(url_for('home'))

        session['user_id'] = user['id']
        session['name'] = user['name']
        session['role'] = user['role']

        flash('Welcome back! You are now logged in.', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f'Login error: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with internship listings"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get internships with company info
    cursor.execute('''
        SELECT i.*, c.name as company_name,
               (SELECT COUNT(*) FROM applications a WHERE a.internship_id = i.id) as applications
        FROM internships i
        LEFT JOIN companies c ON i.company_id = c.id
        WHERE i.status = 'ACTIVE'
        ORDER BY i.created_at DESC
    ''')
    raw_rows = cursor.fetchall()

    # Initialize list for final data
    internships_list = []

    for row in raw_rows:
        # FIX: Convert read-only Row to dict so we can add 'skills' key
        internship = dict(row)

        # Get skills for this internship
        cursor.execute('''
            SELECT s.* FROM skills s
            INNER JOIN internship_skills isk ON s.id = isk.skill_id
            WHERE isk.internship_id = ?
        ''', (internship['id'],))
        
        # Convert skills to dicts as well and attach to internship
        internship['skills'] = [dict(skill) for skill in cursor.fetchall()]

        # Increment views
        cursor.execute('UPDATE internships SET views = views + 1 WHERE id = ?', (internship['id'],))

        # Add to list
        internships_list.append(internship)

    conn.commit()
    conn.close()

    # Get stats
    stats = {
        'internships': len(internships_list),
        'remote': len([i for i in internships_list if i['location'] == 'Remote']),
        'skills': 12,
        'companies': 3
    }

    # Get user info
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = dict(cursor.fetchone())
    conn.close()

    return render_template_string(DASHBOARD_TEMPLATE, user=user, internships=internships_list, stats=stats)

# PROFILE ROUTE ADDED HERE
@app.route('/profile')
@login_required
def profile():
    """User profile page with application history"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get user details
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = dict(cursor.fetchone())

    # Get application history with internship and company details
    cursor.execute('''
        SELECT a.status, a.applied_at, i.title, c.name as company_name
        FROM applications a
        JOIN internships i ON a.internship_id = i.id
        JOIN companies c ON i.company_id = c.id
        WHERE a.user_id = ?
        ORDER BY a.applied_at DESC
    ''', (session['user_id'],))
    
    applications = [dict(row) for row in cursor.fetchall()]
    applied_count = len(applications)

    conn.close()

    return render_template_string(PROFILE_TEMPLATE, user=user, applications=applications, applied_count=applied_count)

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI Chatbot API"""
    try:
        data = request.json
        message = data.get('message', '')

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Get response from chatbot
        response = get_chatbot_response(message, [])

        # Save to database if user is logged in
        if 'user_id' in session:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Save user message
            cursor.execute('''
                INSERT INTO chat_messages (id, user_id, message, is_user)
                VALUES (?, ?, ?, ?)
            ''', (generate_id(), session['user_id'], message, 1))

            # Save bot response
            cursor.execute('''
                INSERT INTO chat_messages (id, user_id, message, is_user)
                VALUES (?, ?, ?, ?)
            ''', (generate_id(), session['user_id'], response, 0))

            conn.commit()
            conn.close()

        return jsonify({'response': response})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/apply', methods=['POST'])
@login_required
def apply():
    """Apply to an internship"""
    try:
        data = request.json
        internship_id = data.get('internship_id')
        user_id = session['user_id']

        if not internship_id:
            return jsonify({'success': False, 'error': 'Internship ID is required'})

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if already applied
        cursor.execute('''
            SELECT id FROM applications WHERE user_id = ? AND internship_id = ?
        ''', (user_id, internship_id))

        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'You have already applied to this internship'})

        # Create application
        cursor.execute('''
            INSERT INTO applications (id, user_id, internship_id, status)
            VALUES (?, ?, ?, ?)
        ''', (generate_id(), user_id, internship_id, 'PENDING'))

        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Initialize database
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")

    # Run the application
    print("\n" + "="*60)
    print("SkillConnect - Internship Matching Platform")
    print("="*60)
    print("\n🚀 Server starting...")
    print("📱 Open your browser to: http://localhost:5000")
    print("\nDemo Credentials:")
    print("  Recruiter: recruiter@techstart.com / password123")
    print("\nFeatures:")
    print("  ✅ User Authentication")
    print("  ✅ Internship Listings")
    print("  ✅ Skill-Based Matching")
    print("  ✅ Application System")
    print("  ✅ AI Chatbot (No API Keys Required)")
    print("  ✅ User Profile & Application History")
    print("  ✅ Responsive Design")
    print("  ✅ Works Offline")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
