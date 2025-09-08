import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clavepor_defecto")
    DEBUG = True

    SERVER = 'DESKTOP-L7LIPFD'
    DATABASE = 'Almacen_Castores'

    # ¡ATENCIÓN! Codificamos el nombre del driver correctamente
    DRIVER = 'ODBC+Driver+17+for+SQL+Server'

    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pyodbc://@{SERVER}/{DATABASE}"
        f"?driver={DRIVER}&trusted_connection=yes"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
