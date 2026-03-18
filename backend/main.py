from fastapi import FastAPI
from routes import dataset_routes, auth_routes
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.staticfiles import StaticFiles
# from routes.preview_route import router as preview_router

from database.database import engine, Base
from database import models

# Create all tables in the database (e.g., 'users' table)
# If the tables already exist, this command will safely do nothing.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Climate Indices API")

app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

origins = [
    "http://localhost:5173",  # URL of React dev server
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware, # allow website React (dev server run on localhost) can call API from web browser
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)

# include router
# app.include_router(indices_routes.router, prefix="/api")

# app.include_router(preview_router, prefix="/api")

app.include_router(dataset_routes.router, prefix="/api")

app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# use "uvicorn main:app --reload" for auto reload

