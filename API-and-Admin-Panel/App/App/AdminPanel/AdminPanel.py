"""
Admin Panel blueprint for the Transportation Management System.

Provides login, dashboard, logout, and password-change routes for
administrators. Templates are served from the local ``templates/`` folder
and static assets from ``static/``.
"""

from flask import Blueprint, render_template, request, redirect, session, make_response, jsonify
from ..extensions import mysql
import json

admin_panel = Blueprint('admin_panel', __name__, template_folder='templates', static_folder='static')


@admin_panel.route("/", methods=['GET', 'POST'])
def loginPage():
    """Admin login page - GET shows form, POST validates credentials."""
    if request.method == 'GET':
        if 'username' in session:
            return redirect("main")
        else:
            return render_template('login.html', error_message='')
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = mysql.connection
        cur = conn.cursor()
        cur.execute("SELECT * FROM Admins WHERE Username=%s AND Password=%s", (username, password))
        if cur.rowcount == 0:
            error_message = 'Invalid username or password'
            return render_template('login.html', error_message=error_message)
        else:
            session['username'] = username
            cur.execute("UPDATE Admins SET LastConnected=NOW() WHERE Username=%s", (session['username'],))
            conn.commit()
            return redirect("main")


@admin_panel.route("/main")
def mainPage():
    """Admin dashboard main page."""
    if 'username' in session:
        return render_template('main.html', user_name=session['username'])
    else:
        return redirect("../admin")


@admin_panel.route('/logout')
def logout():
    """Log out the current admin user."""
    session.pop('username', None)
    return redirect("../admin")


@admin_panel.route('/changepassword', methods=['PUT'])
def changePassword():
    """Change the admin user's password."""
    if 'username' in session:
        if request.method == 'PUT':
            _req = request.args
            oldPas = _req['oldPassowrd']
            newPas = _req['newPassword']
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("SELECT * FROM Admins WHERE Username=%s AND Password=%s", (session['username'], oldPas))
            if cur.rowcount == 0:
                resp = make_response(jsonify({"Status": "Error", "Message": "Old password invalid"}))
                return resp
            else:
                cur.execute("UPDATE Admins SET Password=%s WHERE Username=%s", (newPas, session['username']))
                conn.commit()
                resp = make_response(jsonify({"Status": "Success", "Message": "Password changed!"}))
                return resp
    else:
        return redirect("../admin")
