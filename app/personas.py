import psycopg2
from psycopg2.extras import RealDictCursor

class Persona:
    def __init__(self, name, description, system_instructions):
        self.name = name
        self.description = description
        self.system_instructions = system_instructions

def get_personas_from_db():
    # Database configuration
    conn_params = {
        "dbname": "postgres",
        "user": "postgres",
        "password": "12345",
        "host": "localhost",
        "port": "5433"
    }
    
    loaded_personas = []
    
    try:
        # Connect to your postgres DB
        conn = psycopg2.connect(**conn_params)
        
        # Use RealDictCursor to map column names to dictionary keys
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT name, description, system_instructions FROM PERSONAS;")
            rows = cur.fetchall()
            
            # Map each database row to a Persona object
            for row in rows:
                new_persona = Persona(
                    name=row['name'],
                    description=row['description'],
                    system_instructions=row['system_instructions']
                )
                loaded_personas.append(new_persona)
                
        conn.close()
    except Exception as e:
        print(f"Critical Error: Could not load personas from database: {e}")
        # Optional: return a default persona or empty list so the app doesn't crash
    
    return loaded_personas

# This now replaces your hardcoded list
PERSONAS = get_personas_from_db()

# Example: Verify they are loaded as objects
if __name__ == "__main__":
    for p in PERSONAS:
        print(f"Loaded Object: {p.name}")