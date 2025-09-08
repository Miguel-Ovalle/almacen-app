from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Rol(db.Model):
    __tablename__ = 'roles'
    idRol   = db.Column(db.Integer, primary_key=True)
    nombre  = db.Column(db.String(50), nullable=False, unique=True)
    usuarios = db.relationship('Usuario', backref='rol', lazy=True)

class Usuario(db.Model):
    __tablename__ = 'usuarios'           
    idUsuario   = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(100), nullable=False)
    correo      = db.Column(db.String(50),  nullable=False, unique=True)
    contrasena  = db.Column(db.String(255), nullable=False)
    idRol       = db.Column(db.Integer, db.ForeignKey('roles.idRol'), nullable=False)
    estatus     = db.Column(db.Boolean, nullable=False, default=True)

class Producto(db.Model):
    __tablename__ = 'productos'
    idProducto = db.Column(db.Integer, primary_key=True)
    nombre     = db.Column(db.String(150), nullable=False, unique=True)
    precio     = db.Column(db.Numeric(10,2), nullable=False, default=0)
    cantidad   = db.Column(db.Integer, nullable=False, default=0)
    estatus    = db.Column(db.Boolean, nullable=False, default=True)  # activo/inactivo
    movimientos = db.relationship('Movimiento', backref='producto', lazy=True)

class Movimiento(db.Model):
    __tablename__ = 'movimientos'
    __table_args__ = {'implicit_returning': False}

    idMovimiento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idProducto   = db.Column(db.Integer, db.ForeignKey('productos.idProducto'), nullable=False)
    idUsuario    = db.Column(db.Integer, db.ForeignKey('usuarios.idUsuario'),  nullable=False)

    tipo         = db.Column(db.String(1), nullable=False)      
    cantidad     = db.Column(db.Integer, nullable=False)
    fecha_hora   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    usuario  = db.relationship('Usuario', lazy=True)
