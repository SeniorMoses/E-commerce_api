
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import close_db

from routers.user import router as user_router
from routers.products import router as product_router
from routers.cart import router as cart_router
from routers.orders import router as order_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_db()


app = FastAPI(
    title="Senior Hive E-commerce API",
    description="Asynchronous e-commerce backend API.",
    version="1.0.0",
    lifespan=lifespan,
)


# ==========================================
# REGISTER ROUTERS
# ==========================================

app.include_router(user_router)
app.include_router(product_router)
app.include_router(cart_router)
app.include_router(order_router)


# ==========================================
# ROOT ENDPOINT
# ==========================================

@app.get("/")
async def root():
    return {
        "message": "Senior Hive E-commerce API is running.",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }
