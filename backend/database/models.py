# backend/database/models.py
from sqlalchemy import Column, Integer, String
from database.database import Base

class User(Base):
    """
    SQLAlchemy model for the 'users' table.
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # User Credentials
    email = Column(String, unique=True, index=True, nullable=False)
    
    # We store the hashed password, NEVER the plain text password!
    hashed_password = Column(String, nullable=False)

    # User Role for Role-Based Access Control (RBAC)
    # Defines access level: 'viewer' (Dashboard only) or 'analyst' (Full access)
    role = Column(String, default="viewer", nullable=False)

    # Note: You can easily add more columns here in the future, such as:
    # full_name = Column(String, nullable=True)
    # is_active = Column(Boolean, default=True)