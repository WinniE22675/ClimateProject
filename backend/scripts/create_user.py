# # create_user.py
# import sys
# import os

# # Ensure the script can find your 'database' module if run from the root backend folder
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from database.database import SessionLocal
# from database.models import User

# # Standard FastAPI password hashing library
# # Note: You may need to install this if you haven't: pip install passlib[bcrypt]
# from passlib.context import CryptContext 

# # Setup password hashing (using bcrypt)
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def get_password_hash(password: str) -> str:
#     """
#     Hash the plain text password before saving it to the database.
#     """
#     return pwd_context.hash(password)

# def create_user(email: str, password: str, role: str):
#     """
#     Function to insert a new user into the database securely.
#     """
#     db = SessionLocal()
#     try:
#         # 1. Check if user already exists
#         existing_user = db.query(User).filter(User.email == email).first()
#         if existing_user:
#             print(f"[-] Error: User with email '{email}' already exists in the database.")
#             return

#         # 2. Hash the password
#         hashed_password = get_password_hash(password)
        
#         # 3. Create new User instance
#         new_user = User(
#             email=email,
#             hashed_password=hashed_password,
#             role=role
#         )
        
#         # 4. Save to database
#         db.add(new_user)
#         db.commit()
#         db.refresh(new_user)
        
#         print(f"[+] Success: User '{email}' created successfully with role '{role}'.")
        
#     except Exception as e:
#         db.rollback() # Cancel the transaction if there is an error
#         print(f"[-] Database Error: {e}")
#     finally:
#         db.close() # Always close the session

# if __name__ == "__main__":
#     # ==========================================
#     # CHANGE THESE VARIABLES TO ADD A NEW USER
#     # ==========================================
#     NEW_EMAIL = "analyst1@climate.com"
#     NEW_PASSWORD = "securepassword123"
#     NEW_ROLE = "analyst"  # Choose either 'viewer' or 'analyst'
    
#     print("Starting user creation process...")
#     create_user(NEW_EMAIL, NEW_PASSWORD, NEW_ROLE)

# scripts/create_user.py
import sys
import os
import getpass  # Library for secure, hidden password input

# Ensure the script can find your 'database' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal
from database.models import User
from passlib.context import CryptContext 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash the plain text password before saving it to the database."""
    return pwd_context.hash(password)

def create_user(email: str, password: str, role: str):
    """Function to insert a new user into the database securely."""
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"\n[-] Error: User with email '{email}' already exists.")
            return

        # Hash password and create user
        hashed_password = get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            role=role
        )
        
        db.add(new_user)
        db.commit()
        
        print(f"\n[+] Success: User '{email}' created successfully with role '{role}'.")
        
    except Exception as e:
        db.rollback()
        print(f"\n[-] Database Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "="*40)
    print("   Create New User (Production Safe)")
    print("="*40)
    
    try:
        # 1. Get Email
        email_input = input("Enter email: ").strip()
        if not email_input:
            print("Email cannot be empty. Exiting.")
            sys.exit(1)
            
        # 2. Get Password securely (hidden input)
        password_input = getpass.getpass("Enter password (hidden): ")
        if not password_input:
            print("Password cannot be empty. Exiting.")
            sys.exit(1)
            
        # 3. Get Role with default fallback
        valid_roles = ["viewer", "analyst"]
        role_input = input("Enter role (viewer/analyst) [default: viewer]: ").strip().lower()
        
        if not role_input:
            role_input = "viewer"
        elif role_input not in valid_roles:
            print(f"Invalid role. Defaulting to 'viewer'.")
            role_input = "viewer"
            
        # 4. Execute
        create_user(email_input, password_input, role_input)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)