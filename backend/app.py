from fastapi import FastAPI
from routes import dataset_routes
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.staticfiles import StaticFiles
# from routes.preview_route import router as preview_router

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# use "uvicorn app:app --reload" for auto reload

