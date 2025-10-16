from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app_routes import ocr_routes
import nest_asyncio
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan router
app.include_router(ocr_routes.router)

if __name__ == "__main__":
    nest_asyncio.apply()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
