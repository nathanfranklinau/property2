"""
SubdivideGuide — Property Analysis Service

A FastAPI microservice that runs property analysis on-demand.
Called by the Next.js app when a property has not been analysed yet.

Routes:
    POST /analyse           Trigger analysis for a parcel (runs in background)
    GET  /analyse/{id}      Check the status of an analysis job
    POST /parse-address     Parse a raw address string into structured fields
    GET  /health            Health check

Usage:
    uvicorn service.main:app --port 8001 --reload
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .analyser import run_analysis, get_analysis_status
from .address_parser import AddressParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


_ADDRESS_MODEL_DIR = os.getenv("ADDRESS_MODEL_DIR", "training/model")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Analysis service starting...")
    model_path = Path(_ADDRESS_MODEL_DIR)
    if model_path.exists():
        app.state.address_parser = AddressParser(_ADDRESS_MODEL_DIR)
    else:
        app.state.address_parser = None
        log.warning(
            f"Address model not found at {_ADDRESS_MODEL_DIR} — "
            "POST /parse-address will return 503 until the model is trained and placed there."
        )
    yield
    log.info("Analysis service shutting down.")


app = FastAPI(
    title="SubdivideGuide Analysis Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("WEB_ORIGIN", "http://localhost:3000")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── Request / Response models ───────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    parcel_id: str          # UUID from the parcels table
    cadastre_lot: str
    cadastre_plan: str
    lat: float              # centre point of the parcel
    lon: float
    lot_area_sqm: float


class AnalysisStatusResponse(BaseModel):
    parcel_id: str
    image_status: str
    analysis_status: str
    # Populated when analysis_status = 'complete'
    main_house_size_sqm: float | None = None
    building_count: int | None = None
    available_space_sqm: float | None = None
    pool_count_detected: int | None = None
    pool_count_registered: int | None = None
    pool_area_sqm: float | None = None
    # Image paths (relative to IMAGES_DIR)
    image_markup_path: str | None = None
    image_satellite_masked_path: str | None = None
    image_mask2_path: str | None = None
    error_message: str | None = None


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyse", status_code=202)
async def trigger_analysis(req: AnalyseRequest, background_tasks: BackgroundTasks):
    """
    Start the analysis pipeline for a property parcel.

    This returns immediately with 202 Accepted. The analysis runs in the
    background and updates property_analysis in the database as it progresses.

    Poll GET /analyse/{parcel_id} to check progress.
    """
    log.info(f"Analysis requested for parcel {req.parcel_id} ({req.cadastre_lot}/{req.cadastre_plan})")
    background_tasks.add_task(
        run_analysis,
        parcel_id=req.parcel_id,
        cadastre_lot=req.cadastre_lot,
        cadastre_plan=req.cadastre_plan,
        lat=req.lat,
        lon=req.lon,
        lot_area_sqm=req.lot_area_sqm,
    )
    return {"parcel_id": req.parcel_id, "status": "accepted"}


@app.get("/analyse/{parcel_id}", response_model=AnalysisStatusResponse)
def get_status(parcel_id: str):
    """
    Return the current analysis status for a parcel.

    Statuses:
        image_status:    pending → downloading → complete | failed
        analysis_status: pending → detecting  → complete | failed
    """
    result = get_analysis_status(parcel_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No analysis found for parcel {parcel_id}")
    return result


# ─── Address parser ───────────────────────────────────────────────────────────


class ParseAddressRequest(BaseModel):
    address: str


class ParseAddressResponse(BaseModel):
    building_name: str | None = None
    unit_type: str | None = None
    unit_number: str | None = None
    level_type: str | None = None
    level_number: str | None = None
    lot_number: str | None = None
    street_number: str | None = None
    street_number_last: str | None = None
    street_name: str | None = None
    street_type: str | None = None
    street_suffix: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None


@app.post("/parse-address", response_model=ParseAddressResponse)
def parse_address(req: ParseAddressRequest):
    """
    Parse a raw Australian address string into structured fields.

    Requires the trained model to be present at ADDRESS_MODEL_DIR
    (default: training/model). Returns 503 if the model has not been trained yet.
    """
    parser: AddressParser | None = app.state.address_parser
    if parser is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Address parser model not loaded. "
                "Run prepare_iob.py then train.py to generate the model."
            ),
        )
    result = parser.parse(req.address)
    return ParseAddressResponse(**result)
