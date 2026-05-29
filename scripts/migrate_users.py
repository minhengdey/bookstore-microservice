import os
import psycopg2
from psycopg2.extras import DictCursor

def migrate_users():
    db_host = os.environ.get("DB_HOST", "localhost")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASSWORD", "postgres")
    
    print(f"Connecting to auth_db at {db_host}...")
    conn_auth = psycopg2.connect(dbname="auth_db", user=db_user, password=db_pass, host=db_host)
    
    print(f"Connecting to user_db at {db_host}...")
    conn_user = psycopg2.connect(dbname="user_db", user=db_user, password=db_pass, host=db_host)
    
    cur_auth = conn_auth.cursor(cursor_factory=DictCursor)
    cur_user = conn_user.cursor()
    conn_user.autocommit = True
    
    print("Fetching AuthUsers...")
    cur_auth.execute("SELECT id, username, email, password, phone, role, entity_role, is_active, created_at FROM auth_users")
    auth_users = cur_auth.fetchall()
    
    for u in auth_users:
        try:
            # 1. Idempotent Insert into users
            cur_user.execute("""
                INSERT INTO users (id, username, email, password, phone, role, is_active, created_date) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    username = EXCLUDED.username,
                    email = EXCLUDED.email,
                    password = EXCLUDED.password,
                    role = EXCLUDED.role;
            """, (u['id'], u['username'], u['email'], u['password'], u['phone'], u['role'], u['is_active'], u['created_at']))
            
            # 2. Insert Profile
            if u['role'] == 'customer':
                cur_user.execute("""
                    INSERT INTO customer_profiles (user_id, loyalty_points) 
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO NOTHING;
                """, (u['id'], 0)) # Default 0 loyalty points since we decouple from old DB
                print(f"Migrated Customer: {u['username']} (ID: {u['id']})")
                
            elif u['role'] in ['staff', 'admin']:
                # Both staff and admin use StaffProfile
                cur_user.execute("""
                    INSERT INTO staff_profiles (user_id, storage_code, department, position) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING;
                """, (u['id'], f"STORE-{u['id']}", 'Migrated', u['entity_role'] or u['role']))
                print(f"Migrated Staff/Manager: {u['username']} (ID: {u['id']})")
                
        except Exception as e:
            print(f"Error migrating {u['username']}: {e}")

    cur_auth.close()
    conn_auth.close()
    cur_user.close()
    conn_user.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate_users()
