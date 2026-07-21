# routes/followups/routes.py

from flask import render_template, session, redirect, url_for
from . import followups_bp

@followups_bp.route('/')
def index():
    """Página de follow-ups"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('followups.html')