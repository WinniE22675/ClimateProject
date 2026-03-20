# backend/database/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Define the SQLite database URL
# The file 'climate_app.db' will be created in the root of your backend folder
SQLALCHEMY_DATABASE_URL = "sqlite:///./climate_app.db"

# 2. Create the SQLAlchemy Engine
# connect_args={"check_same_thread": False} is required ONLY for SQLite in FastAPI 
# because FastAPI can handle multiple requests (threads) simultaneously.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Create a SessionLocal class
# Each instance of this class will be a temporary database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# autocommit=False means that if we add data (Add), it won't be saved to the database immediately until we call db.commit().
# autoflush=False: Prevents automatic data updates to the database before we commit.

# 4. Create a Base class
# All of our database models (in models.py) will inherit from this class
Base = declarative_base()
# Any class that uses `Base` as a template will automatically use that class to create a table in the database.

# 5. Dependency generator function
# We will use this in our routes to get a database connection per request
def get_db():
    db = SessionLocal()
    try:
        yield db # Use this session first. will wait here. (Passing a .db variable to the API Route for use.)
    finally:
        db.close() # Always close the connection after the request is done