from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from config import Config
from models import db, Usuario, Rol, Producto, Movimiento
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError


app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'implicit_returning': False}
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]
db.init_app(app)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if 'rol' not in session:
                return redirect(url_for('login'))
            if session['rol'] not in roles:
                flash("No tienes permisos para esta acción.", "warning")
                return redirect(url_for('inicio'))
            return view(*args, **kwargs)
        return wrapper
    return decorator

def current_user_id():
    return session.get('user_id')


# Rutas públicas

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = (request.form.get('correo') or '').strip().lower()
        password = request.form.get('password') or ''
        usuario = Usuario.query.filter_by(correo=correo, estatus=True).first()

        if usuario and check_password_hash(usuario.contrasena, password):
            session.clear()
            session['user_id'] = usuario.idUsuario
            session['user']    = usuario.nombre
            session['rol']     = usuario.rol.nombre
            return redirect(url_for('inicio'))
        flash("Usuario o contraseña incorrectos", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/inicio')
@login_required
def inicio():
    return render_template('inicio.html')


# Usuarios (solo Administrador)

@app.route('/usuarios', endpoint='usuarios_list')
@login_required
@role_required('Administrador')
def usuarios_list():
    usuarios = Usuario.query.order_by(Usuario.idUsuario.desc()).all()
    return render_template('usuarios_list.html', usuarios=usuarios)

@app.route('/usuarios/nuevo', methods=['GET','POST'], endpoint='usuarios_nuevo')
@login_required
@role_required('Administrador')
def usuarios_nuevo():
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        correo = (request.form.get('correo') or '').strip().lower()
        pw     = request.form.get('password') or ''
        rol_id = int(request.form.get('idRol') or 0)
        activo = True if request.form.get('estatus') == 'on' else False

        if not (nombre and correo and pw and rol_id):
            flash("Completa todos los campos.", "warning")
            return redirect(url_for('usuarios_nuevo'))

        try:
            u = Usuario(
                nombre=nombre,
                correo=correo,
                contrasena=generate_password_hash(pw),
                idRol=rol_id,
                estatus=activo
            )
            db.session.add(u)
            db.session.commit()
            flash("Usuario creado correctamente.", "success")
            return redirect(url_for('usuarios_list'))
        except IntegrityError:
            db.session.rollback()
            flash("Ese correo ya existe.", "danger")
            return redirect(url_for('usuarios_nuevo'))

    roles = Rol.query.order_by(Rol.nombre).all()
    return render_template('usuarios_nuevo.html', roles=roles)

@app.route('/usuarios/<int:id>/editar', methods=['GET','POST'])
@login_required
@role_required('Administrador')
def usuarios_editar(id):
    u = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        u.nombre  = (request.form.get('nombre') or '').strip()
        u.correo  = (request.form.get('correo') or '').strip().lower()
        pw        = request.form.get('password') or ''
        if pw.strip():
            u.contrasena = generate_password_hash(pw)
        u.idRol   = int(request.form.get('idRol') or u.idRol)
        u.estatus = True if request.form.get('estatus') == 'on' else False
        try:
            db.session.commit()
            flash("Usuario actualizado.", "success")
            return redirect(url_for('usuarios_list'))
        except IntegrityError:
            db.session.rollback()
            flash("Ese correo ya existe.", "danger")
            return redirect(url_for('usuarios_editar', id=id))

    roles = Rol.query.order_by(Rol.nombre).all()
    return render_template('usuarios_editar.html', u=u, roles=roles)

@app.route('/usuarios/<int:id>/activar', methods=['POST'])
@login_required
@role_required('Administrador')
def usuarios_activar(id):
    u = Usuario.query.get_or_404(id)
    u.estatus = True
    db.session.commit()
    flash("Usuario activado.", "success")
    return redirect(url_for('usuarios_list'))

@app.route('/usuarios/<int:id>/desactivar', methods=['POST'])
@login_required
@role_required('Administrador')
def usuarios_desactivar(id):
    u = Usuario.query.get_or_404(id)
    if u.idUsuario == session.get('user_id'):
        flash("No puedes desactivar tu propio usuario.", "warning")
    else:
        u.estatus = False
        db.session.commit()
        flash("Usuario desactivado.", "success")
    return redirect(url_for('usuarios_list'))

@app.route('/usuarios/<int:id>/eliminar', methods=['POST'])
@login_required
@role_required('Administrador')
def usuarios_eliminar(id):
    u = Usuario.query.get_or_404(id)
    if u.idUsuario == session.get('user_id'):
        flash("No puedes eliminar tu propio usuario.", "warning")
        return redirect(url_for('usuarios_list'))
    db.session.delete(u)
    db.session.commit()
    flash("Usuario eliminado.", "success")
    return redirect(url_for('usuarios_list'))

# =========================
# Inventario
# =========================
@app.route('/inventario', methods=['GET'])
@login_required
def inventario_list():
    estatus = request.args.get('estatus', 'todos')
    q = Producto.query
    if estatus == 'activo':
        q = q.filter(Producto.estatus == True)
    elif estatus == 'inactivo':
        q = q.filter(Producto.estatus == False)
    productos = q.order_by(Producto.idProducto.desc()).all()

    ids_con_historial = {pid for (pid,) in db.session.query(Movimiento.idProducto).distinct().all()}
    return render_template('inventario_list.html', productos=productos, ids_con_historial=ids_con_historial)




@app.route('/inventario/agregar', methods=['POST'])
@login_required
@role_required('Administrador')
def inventario_agregar():
    nombre  = (request.form.get('nombre') or '').strip()
    precio  = request.form.get('precio') or '0'
    estatus = True if (request.form.get('estatus') == '1') else False

    if not nombre:
        flash("Nombre requerido.", "warning")
        return redirect(url_for('inventario_list'))

    try:
        p = Producto(nombre=nombre, precio=precio, cantidad=0, estatus=estatus)
        db.session.add(p)
        db.session.commit()
        flash("Producto creado (cantidad inicial 0).", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un producto con ese nombre.", "danger")
    except Exception:
        db.session.rollback()
        flash("No se pudo crear el producto.", "danger")

    return redirect(url_for('inventario_list'))

# ENTRADA: SOLO Administrador
@app.route('/inventario/<int:id>/entrada', methods=['POST'])
@login_required
@role_required('Administrador')
def inventario_entrada(id):
    p = Producto.query.get_or_404(id)
    try:
        # admite "cant" o "cantidad" según el formulario
        cant = int(request.form.get('cant') or request.form.get('cantidad') or 0)
    except ValueError:
        cant = 0

    if cant <= 0:
        flash("La cantidad debe ser mayor a 0.", "warning")
        return redirect(url_for('inventario_list'))

    # actualizar stock
    p.cantidad = (p.cantidad or 0) + cant

    # registrar movimiento de ENTRADA
    m = Movimiento(
        idProducto=p.idProducto,
        idUsuario=current_user_id(),
        tipo='E',  # entrada
        cantidad=cant,
        fecha_hora=datetime.utcnow(),
    )
    db.session.add(m)
    db.session.commit()

    flash(f"Entrada registrada (+{cant}).", "success")
    return redirect(url_for('inventario_list'))

@app.route('/inventario/<int:id>/baja', methods=['POST'])
@login_required
@role_required('Administrador')
def inventario_baja(id):
    p = Producto.query.get_or_404(id)
    p.estatus = False
    db.session.commit()
    flash("Producto dado de baja.", "success")
    return redirect(url_for('inventario_list'))

@app.route('/inventario/<int:id>/reactivar', methods=['POST'])
@login_required
@role_required('Administrador')
def inventario_reactivar(id):
    p = Producto.query.get_or_404(id)
    p.estatus = True
    db.session.commit()
    flash("Producto reactivado.", "success")
    return redirect(url_for('inventario_list'))

@app.route('/inventario/<int:id>/eliminar', methods=['POST'])
@login_required
@role_required('Administrador')
def inventario_eliminar(id):
    p = Producto.query.get_or_404(id)

    # 1) No borrar si tiene existencias
    if (p.cantidad or 0) > 0:
        flash("No puedes eliminar un producto con existencias.", "warning")
        return redirect(url_for('inventario_list'))

    # 2) No borrar si tiene movimientos históricos
    from models import Movimiento  # import local para evitar ciclos
    tiene_historial = (
        db.session.query(Movimiento.idMovimiento)
        .filter(Movimiento.idProducto == p.idProducto)
        .limit(1)
        .first()
    )
    if tiene_historial:
        flash("No puedes eliminar un producto con historial de movimientos. .", "warning")
        return redirect(url_for('inventario_list'))

    # 3) Eliminar si pasa las validaciones
    try:
        db.session.delete(p)
        db.session.commit()
        flash("Producto eliminado.", "success")
    except Exception:
        db.session.rollback()
        flash("No se pudo eliminar el producto.", "danger")

    return redirect(url_for('inventario_list'))

# SALIDA: SOLO Almacenista
@app.route('/salida', methods=['GET', 'POST'])
@login_required
@role_required('Almacenista')
def salida():
    if request.method == 'POST':
        # 1) Datos del formulario
        try:
            id_producto = int(request.form.get('idProducto') or 0)
            cantidad    = int(request.form.get('cantidad') or 0)
        except ValueError:
            flash('Cantidad inválida.', 'warning')
            return redirect(url_for('salida'))

        if not id_producto:
            flash('Selecciona un producto.', 'warning')
            return redirect(url_for('salida'))
        if cantidad <= 0:
            flash('La cantidad debe ser mayor que 0.', 'warning')
            return redirect(url_for('salida'))

        # 2) Transacción: primero registrar el movimiento, luego descontar stock
        try:
            with db.session.begin():
                # Bloqueo de fila para evitar carreras
                p = (Producto.query
                        .filter_by(idProducto=id_producto, estatus=True)
                        .with_for_update()
                        .first())

                if not p:
                    raise ValueError('Producto no válido o inactivo.')

                # Validación de stock (permitimos llegar a 0, no a negativo)
                if cantidad > (p.cantidad or 0):
                    raise ValueError('No puedes sacar más de lo disponible en inventario.')

                # 2.1 Registrar movimiento (dispara validaciones/trigger con stock original)
                mv = Movimiento(
                    idProducto=p.idProducto,
                    idUsuario=session.get('user_id'),
                    tipo='S',
                    cantidad=cantidad,
                    fecha_hora=datetime.utcnow(),
                )
                db.session.add(mv)

                # 2.2 Descontar del producto
                p.cantidad = (p.cantidad or 0) - cantidad

            flash('Salida registrada.', 'success')
            return redirect(url_for('salida'))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'warning')
            return redirect(url_for('salida'))

        except (ProgrammingError, IntegrityError) as e:
            # Mensaje textual generado por la BD/trigger
            db.session.rollback()
            raw = str(getattr(e, 'orig', e))
            low = raw.lower()
            msg = raw
            if 'inactivo' in low:
                msg = 'No puedes registrar salida de un producto inactivo.'
            elif 'sin stock' in low or 'suficiente' in low or 'stock' in low:
                msg = 'No hay suficiente inventario para la salida solicitada.'
            flash(msg, 'danger')
            return redirect(url_for('salida'))

        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error en la base de datos: {str(getattr(e, "orig", e))}', 'danger')
            return redirect(url_for('salida'))

    # GET: solo productos activos con stock > 0 (para que desaparezcan al llegar a cero)
    productos = (Producto.query
                    .filter(Producto.estatus == True)
                    .filter(Producto.cantidad > 0)
                    .order_by(Producto.nombre.asc())
                    .all())
    return render_template('salida.html', productos=productos)




# Histórico

@app.route('/historico', methods=['GET'])
@login_required
@role_required('Administrador')
def historico():
    tipo_param  = (request.args.get('tipo') or '').strip().lower()  # '', 'entrada'/'salida'/'e'/'s'
    f_ini = (request.args.get('f_ini') or '').strip()
    f_fin = (request.args.get('f_fin') or '').strip()

    q = (Movimiento.query
         .join(Producto, Movimiento.idProducto == Producto.idProducto)
         .join(Usuario,  Movimiento.idUsuario  == Usuario.idUsuario))

    if tipo_param in ('entrada', 'e'):
        q = q.filter(Movimiento.tipo == 'E')
    elif tipo_param in ('salida', 's'):
        q = q.filter(Movimiento.tipo == 'S')

    try:
        if f_ini:
            q = q.filter(Movimiento.fecha_hora >= datetime.strptime(f_ini, '%Y-%m-%d'))
        if f_fin:
            q = q.filter(Movimiento.fecha_hora <  datetime.strptime(f_fin, '%Y-%m-%d') + timedelta(days=1))
    except Exception:
        pass

    movimientos = q.order_by(Movimiento.idMovimiento.desc()).all()
    return render_template('historico.html', movimientos=movimientos,
                           tipo=tipo_param, f_ini=f_ini, f_fin=f_fin)

if __name__ == '__main__':
    with app.app_context():
        db.session.execute(text("SELECT 1"))  # prueba de conexión
    app.run(debug=True)
