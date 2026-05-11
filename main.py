from flask import Flask, render_template, request, redirect, url_for, make_response, send_from_directory
from database import init_db, SessionLocal, User
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR)

# Inicializar Base de Datos
init_db()

# Crear un usuario administrador por defecto
def create_default_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(username="admin", email="admin@sportzone.com", password="admin123", role="admin")
            db.add(admin)
            db.commit()
    finally:
        db.close()

create_default_admin()

@app.route('/style.css')
def get_style():
    return send_from_directory(BASE_DIR, 'style.css')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username, User.password == password).first()
            if not user:
                return render_template('login.html', error="Credenciales inválidas")
            
            # Login básico con cookies
            resp = make_response(redirect(url_for('admin_users')))
            resp.set_cookie('user_role', user.role)
            resp.set_cookie('user_name', user.username)
            return resp
        finally:
            db.close()
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('index')))
    resp.delete_cookie('user_role')
    resp.delete_cookie('user_name')
    return resp

# Panel de Gestión (CRUD)
@app.route('/admin/users')
def admin_users():
    role = request.cookies.get('user_role')
    if role != 'admin':
        return redirect(url_for('login'))
        
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return render_template('admin.html', users=users, current_user=request.cookies.get('user_name'))
    finally:
        db.close()

@app.route('/admin/users/create', methods=['POST'])
def create_user():
    role_cookie = request.cookies.get('user_role')
    if role_cookie != 'admin':
        return redirect(url_for('login'))
        
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
        if not existing_user:
            new_user = User(username=username, email=email, password=password, role=role)
            db.add(new_user)
            db.commit()
    finally:
        db.close()
        
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    role_cookie = request.cookies.get('user_role')
    if role_cookie != 'admin':
        return redirect(url_for('login'))
        
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()
        
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run(port=8000, debug=True)
