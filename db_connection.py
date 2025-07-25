import os
import pymysql
from pymysql import Error
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def create_connection():
    """
    Crea y retorna una conexión a la base de datos MySQL usando PyMySQL.
    
    Returns:
        connection: Objeto de conexión a la base de datos o None si hay un error
    """
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            charset="utf8mb4",
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor,
            ssl={'ssl': {'ssl-mode': 'REQUIRED'}}
        )
        return connection
            
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None

def check_connection():
    """
    Verifica la conexión a la base de datos e imprime información del servidor.
    """
    connection = create_connection()
    
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                # Obtener información de la base de datos
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()
                print(f"Conectado a la base de datos: {db_name['DATABASE()']}")
                
                # Obtener versión de MySQL
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"Versión de MySQL: {version['VERSION()']}")
                
                # Listar tablas
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                print(f"\nTablas disponibles: {len(tables)}")
                for table in tables:
                    print(f"- {list(table.values())[0]}")
                
        except Error as e:
            print(f"Error al verificar la conexión: {e}")
            
        finally:
            if connection.open:
                connection.close()
                print("\nConexión a MySQL cerrada")
    else:
        print("No se pudo establecer conexión con la base de datos")

# Si se ejecuta este archivo directamente, verificar la conexión
if __name__ == "__main__":
    print("=== Probando conexión a la base de datos MySQL Aiven con PyMySQL ===")
    check_connection()
