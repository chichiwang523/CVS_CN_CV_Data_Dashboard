"""FastAPI 数据接口入口"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.vehicles import router as vehicles_router
from api.routes.statistics import router as statistics_router

app = FastAPI(
    title="ZF 商用车公告数据 API",
    description="中国商用车公告数据查询与统计接口",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehicles_router)
app.include_router(statistics_router)


@app.get("/")
def root():
    return {"message": "ZF 商用车公告数据 API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
