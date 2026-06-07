from flask import Flask, render_template, request, redirect, url_for, make_response, send_from_directory
from database import init_db, SessionLocal, User, Producto, Solicitud
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR)

# Inicializar Base de Datos
init_db()

# ── Usuario admin por defecto ──────────────────────────────────────────────
def create_default_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(username="admin", email="admin@sportzone.com",
                         password="admin123", role="admin")
            db.add(admin)
            db.commit()
    finally:
        db.close()

create_default_admin()

# ── Estáticos ──────────────────────────────────────────────────────────────
@app.route('/style.css')
def get_style():
    return send_from_directory(BASE_DIR, 'style.css')

# ── Páginas públicas ───────────────────────────────────────────────────────
@app.route('/')
def index():
    db = SessionLocal()
    try:
        # Solo mostrar productos aprobados al público
        productos = db.query(Producto).filter(Producto.estado == "Aprobado").all()
        return render_template('index.html', productos=productos)
    finally:
        db.close()

# ── Auth ───────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = SessionLocal()
        try:
            user = db.query(User).filter(
                User.username == username,
                User.password == password
            ).first()
            if not user:
                return render_template('login.html', error="Credenciales inválidas")
            resp = make_response(redirect(url_for('dashboard')))
            resp.set_cookie('user_role', user.role)
            resp.set_cookie('user_name', user.username)
            resp.set_cookie('user_id', str(user.id))
            return resp
        finally:
            db.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('index')))
    resp.delete_cookie('user_role')
    resp.delete_cookie('user_name')
    resp.delete_cookie('user_id')
    return resp

@app.route('/dashboard')
def dashboard():
    role = request.cookies.get('user_role')
    if role == 'admin':
        return redirect(url_for('admin_users'))
    elif role == 'ofertante':
        return redirect(url_for('mis_productos'))
    return redirect(url_for('login'))

# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 1 — Gestión de Usuarios (Admin)
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/admin/users')
def admin_users():
    if request.cookies.get('user_role') != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return render_template('admin.html', users=users,
                                current_user=request.cookies.get('user_name'))
    finally:
        db.close()

@app.route('/admin/users/create', methods=['POST'])
def create_user():
    if request.cookies.get('user_role') != 'admin':
        return redirect(url_for('login'))
    username = request.form.get('username')
    email    = request.form.get('email')
    password = request.form.get('password')
    role     = request.form.get('role')
    db = SessionLocal()
    try:
        existe = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if not existe:
            db.add(User(username=username, email=email,
                        password=password, role=role))
            db.commit()
    finally:
        db.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if request.cookies.get('user_role') != 'admin':
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

# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 2 — HU-01: Registrar Producto (Ofertante)
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/productos/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    if request.cookies.get('user_role') != 'ofertante':
        return redirect(url_for('login'))

    errores = []
    if request.method == 'POST':
        titulo      = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        precio_raw  = request.form.get('precio', '').strip()
        categoria   = request.form.get('categoria', '').strip()
        stock_raw   = request.form.get('stock', '0').strip()
        imagen_url  = request.form.get('imagen_url', '').strip()

        if not titulo:       errores.append('El título es obligatorio.')
        if not descripcion:  errores.append('La descripción es obligatoria.')
        if not precio_raw:   errores.append('El precio es obligatorio.')
        if not categoria:    errores.append('La categoría es obligatoria.')

        try:
            precio = float(precio_raw)
            stock  = int(stock_raw)
        except ValueError:
            errores.append('Precio debe ser número decimal y stock un número entero.')
            precio, stock = 0, 0

        if not errores:
            db = SessionLocal()
            try:
                producto = Producto(
                    titulo       = titulo,
                    descripcion  = descripcion,
                    precio       = precio,
                    categoria    = categoria,
                    stock        = stock,
                    imagen_url   = imagen_url or None,
                    estado       = 'Pendiente',
                    ofertante_id = int(request.cookies.get('user_id'))
                )
                db.add(producto)
                db.commit()
                return redirect(url_for('mis_productos'))
            finally:
                db.close()

    return render_template('producto_form.html', modo='nuevo', errores=errores, producto=None)

# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 2 — HU-02: Editar / Eliminar Producto (Ofertante)
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/mis-productos')
def mis_productos():
    if request.cookies.get('user_role') != 'ofertante':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        uid = int(request.cookies.get('user_id', 0))
        productos = db.query(Producto).filter(Producto.ofertante_id == uid).all()
        return render_template('mis_productos.html', productos=productos)
    finally:
        db.close()

@app.route('/productos/editar/<int:pid>', methods=['GET', 'POST'])
def editar_producto(pid):
    if request.cookies.get('user_role') != 'ofertante':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        uid      = int(request.cookies.get('user_id', 0))
        producto = db.query(Producto).filter(Producto.id == pid).first()
        if not producto or producto.ofertante_id != uid:
            return redirect(url_for('mis_productos'))

        errores = []
        if request.method == 'POST':
            titulo      = request.form.get('titulo', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            precio_raw  = request.form.get('precio', '').strip()
            categoria   = request.form.get('categoria', '').strip()
            stock_raw   = request.form.get('stock', '0').strip()
            imagen_url  = request.form.get('imagen_url', '').strip()

            if not titulo:      errores.append('El título es obligatorio.')
            if not descripcion: errores.append('La descripción es obligatoria.')

            if not errores:
                producto.titulo      = titulo
                producto.descripcion = descripcion
                producto.precio      = float(precio_raw)
                producto.categoria   = categoria
                producto.stock       = int(stock_raw)
                producto.imagen_url  = imagen_url or None
                producto.estado      = 'Pendiente'   # ← vuelve a Pendiente
                db.commit()
                return redirect(url_for('mis_productos'))

        return render_template('producto_form.html', modo='editar',
                               producto=producto, errores=errores)
    finally:
        db.close()

@app.route('/productos/eliminar/<int:pid>', methods=['POST'])
def eliminar_producto(pid):
    if request.cookies.get('user_role') != 'ofertante':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        uid      = int(request.cookies.get('user_id', 0))
        producto = db.query(Producto).filter(Producto.id == pid).first()
        if producto and producto.ofertante_id == uid:
            db.delete(producto)
            db.commit()
    finally:
        db.close()
    return redirect(url_for('mis_productos'))

# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 2 — HU-03: Validación por Admin
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/admin/productos')
def admin_productos():
    if request.cookies.get('user_role') != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        pendientes = db.query(Producto).filter(Producto.estado == 'Pendiente').all()
        aprobados  = db.query(Producto).filter(Producto.estado == 'Aprobado').all()
        rechazados = db.query(Producto).filter(Producto.estado == 'Rechazado').all()
        return render_template('admin_productos.html',
                               pendientes=pendientes,
                               aprobados=aprobados,
                               rechazados=rechazados)
    finally:
        db.close()

@app.route('/admin/productos/<int:pid>/aprobar', methods=['POST'])
def aprobar_producto(pid):
    if request.cookies.get('user_role') != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.estado = 'Aprobado'
            db.commit()
    finally:
        db.close()
    return redirect(url_for('admin_productos'))

@app.route('/admin/productos/<int:pid>/rechazar', methods=['POST'])
def rechazar_producto(pid):
    if request.cookies.get('user_role') != 'admin':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.estado = 'Rechazado'
            db.commit()
    finally:
        db.close()
    return redirect(url_for('admin_productos'))
# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 3 — HU-01: Búsqueda de Productos/Servicios (Demandante)
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/buscar')
def buscar_productos():
    filtro   = request.args.get('filtro', 'recientes')
    busqueda = request.args.get('q', '').strip()

    db = SessionLocal()
    try:
        query = db.query(Producto).filter(Producto.estado == 'Aprobado')

        if busqueda:
            query = query.filter(
                (Producto.titulo.ilike(f'%{busqueda}%')) |
                (Producto.descripcion.ilike(f'%{busqueda}%')) |
                (Producto.categoria.ilike(f'%{busqueda}%'))
            )

        if filtro == 'recientes':
            query = query.order_by(Producto.fecha_creacion.desc())
        elif filtro == 'mejor_calificados':
            query = query.order_by(Producto.calificacion.desc())
        elif filtro == 'mas_solicitados':
            query = query.order_by(Producto.veces_solicitado.desc())

        productos = query.all()
        return render_template('buscar.html',
                               productos=productos,
                               filtro=filtro,
                               busqueda=busqueda)
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 3 — HU-02: Solicitar Producto/Servicio (Demandante)
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/solicitar/<int:pid>', methods=['GET', 'POST'])
def solicitar_producto(pid):
    db = SessionLocal()
    try:
        producto = db.query(Producto).filter(
            Producto.id == pid,
            Producto.estado == 'Aprobado'
        ).first()

        if not producto:
            return redirect(url_for('buscar_productos'))

        errores = []
        if request.method == 'POST':
            nombre   = request.form.get('nombre', '').strip()
            email    = request.form.get('email', '').strip()
            telefono = request.form.get('telefono', '').strip()
            mensaje  = request.form.get('mensaje', '').strip()

            if not nombre:  errores.append('El nombre es obligatorio.')
            if not email:   errores.append('El email es obligatorio.')
            if '@' not in email and email:
                errores.append('El email no es válido.')

            if not errores:
                solicitud = Solicitud(
                    producto_id       = pid,
                    nombre_demandante = nombre,
                    email_demandante  = email,
                    telefono          = telefono,
                    mensaje           = mensaje,
                    estado            = 'Pendiente'
                )
                db.add(solicitud)
                # Incrementar contador
                producto.veces_solicitado += 1
                db.commit()
                return render_template('solicitar.html',
                                       producto=producto,
                                       exito=True,
                                       solicitud_id=solicitar.id,
                                       errores=[])

        return render_template('solicitar.html',
                               producto=producto,
                               exito=False,
                               errores=errores)
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 3 — HU-03: Confirmación de Solicitudes (Ofertante)
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/mis-solicitudes')
def mis_solicitudes():
    if request.cookies.get('user_role') != 'ofertante':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        uid = int(request.cookies.get('user_id', 0))
        # Traer solicitudes de los productos del ofertante
        solicitudes = db.query(Solicitud).join(Producto).filter(
            Producto.ofertante_id == uid
        ).order_by(Solicitud.fecha_solicitud.desc()).all()

        return render_template('mis_solicitudes.html', solicitudes=solicitudes)
    finally:
        db.close()

@app.route('/solicitudes/responder/<int:sid>/<accion>', methods=['POST'])
def responder_solicitud(sid, accion):
    if request.cookies.get('user_role') != 'ofertante':
        return redirect(url_for('login'))
    db = SessionLocal()
    try:
        uid = int(request.cookies.get('user_id', 0))
        solicitud = db.query(Solicitud).join(Producto).filter(
            Solicitud.id == sid,
            Producto.ofertante_id == uid
        ).first()
        if solicitud and accion in ['aceptar', 'rechazar']:
            solicitud.estado = 'Aceptado' if accion == 'aceptar' else 'Rechazado'
            db.commit()
    finally:
        db.close()
    return redirect(url_for('mis_solicitudes'))
# ══════════════════════════════════════════════════════════════════════════════
# CALIFICACIONES — Ver formulario de calificación
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/calificar/<int:sid>', methods=['GET', 'POST'])
def calificar(sid):
    db = SessionLocal()
    try:
        solicitud = db.query(Solicitud).filter(
            Solicitud.id == sid,
            Solicitud.estado == 'Aceptado'
        ).first()

        if not solicitud:
            return redirect(url_for('buscar_productos'))

        # Si ya fue calificada, no permitir de nuevo
        if solicitud.calificacion:
            return render_template('calificar.html',
                                   solicitud=solicitud,
                                   ya_calificado=True)

        errores = []
        if request.method == 'POST':
            calificacion = request.form.get('calificacion', '').strip()
            comentario   = request.form.get('comentario', '').strip()

            if not calificacion:
                errores.append('Debes seleccionar una calificación.')
            else:
                cal = int(calificacion)
                if cal < 1 or cal > 5:
                    errores.append('La calificación debe ser entre 1 y 5.')

            if not errores:
                solicitud.calificacion = cal
                solicitud.comentario   = comentario

                # Recalcular promedio del producto
                producto = solicitud.producto
                todas = db.query(Solicitud).filter(
                    Solicitud.producto_id == producto.id,
                    Solicitud.calificacion != None
                ).all()
                total = sum(s.calificacion for s in todas) + cal
                cantidad = len(todas) + 1
                producto.calificacion = round(total / cantidad, 1)

                db.commit()
                return render_template('calificar.html',
                                       solicitud=solicitud,
                                       ya_calificado=True,
                                       exito=True)

        return render_template('calificar.html',
                               solicitud=solicitud,
                               ya_calificado=False,
                               errores=errores)
    finally:
        db.close()
        # ══════════════════════════════════════════════════════════════════════════════
# UTILIDAD — Resetear base de datos (solo usar una vez)
# ══════════════════════════════════════════════════════════════════════════════
@app.route('/reset-db-ahora')
def reset_db():
    from database import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = User(
            username="admin",
            email="admin@sportzone.com",
            password="admin123",
            role="admin"
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()
    return "<h2>✅ Base de datos reseteada correctamente. <a href='/login'>Ir al login</a></h2>"

if __name__ == '__main__':
    app.run(port=8000, debug=True)
