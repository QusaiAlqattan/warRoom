import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql

DB_PARAMS = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": "5433"
}

class Persona:
    def __init__(self, name, description):
        self.name = name
        self.description = description

def get_personas_from_db():
    loaded_personas = []
    
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT name, description FROM PERSONAS;")
            rows = cur.fetchall()
            
            for row in rows:
                new_persona = Persona(
                    name=row['name'],
                    description=row['description']
                )
                loaded_personas.append(new_persona)
                
        conn.close()
    except Exception as e:
        print(f"Critical Error: Could not load personas from database: {e}")
    
    return loaded_personas

def insert_persona_to_db(name, description):
    conn = psycopg2.connect(**DB_PARAMS)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO PERSONAS (name, description) VALUES (%s, %s);",
                (name, description)
            )
        conn.commit()
    finally:
        conn.close()

def delete_persona_from_db(name):
    conn = psycopg2.connect(**DB_PARAMS)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM PERSONAS WHERE name = %s;", (name,))
        conn.commit()
    finally:
        conn.close()

# This now replaces your hardcoded list
PERSONAS = get_personas_from_db()

# Example: Verify they are loaded as objects
if __name__ == "__main__":
    for p in PERSONAS:
        print(f"Loaded Object: {p.name}")