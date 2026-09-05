"""
Stage 6 — minimal REST API exposing the latest index values.

Run with:
    uvicorn api:app --reload --port 8000

Then:
    curl http://localhost:8000/index/latest
or open http://localhost:8000/docs for the interactive Swagger UI --
useful in a demo since a judge can hit "Try it out" themselves.

No auth layer. This is a documented non-goal for the hackathon prototype
(see docs/PRD_hackathon_prototype.md §5) -- a real MoSPI integration
would need one before touching production data.
"""
from datetime import datetime

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text

from db import get_engine

app = FastAPI(
    title="AirPrice India — Index API (prototype)",
    description="SIH26056 internal hackathon prototype. Not production-hardened.",
)


class IndexPoint(BaseModel):
    origin: str
    destination: str
    base_period: str
    index_value: float
    n_observations: int
    computed_at_utc: datetime


@app.get("/index/latest", response_model=list[IndexPoint])
def latest_index():
    engine = get_engine()
    df = pd.read_sql(
        text(
            """
            SELECT origin, destination, base_period, index_value,
                n_observations, computed_at_utc
            FROM airfare_index
            ORDER BY origin, destination, computed_at_utc DESC
            """
        ),
        engine,
    )
    if df.empty:
        return []
    df = df.drop_duplicates(subset=["origin", "destination"], keep="first")
    if df.empty:
        return []
    df["base_period"] = df["base_period"].astype(str)
    return df.to_dict(orient="records")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/mock-airline/search")
def mock_airline_search(origin: str, destination: str, date: str):
    """
    Returns a complex, deeply nested JSON response simulating a real airline's internal API.
    """
    import random
    
    # Generate somewhat realistic, random fares based on route
    base_fare = 5000 if origin == "BOM" or destination == "BOM" else 7000
    base_fare += random.randint(-1000, 2000)
    
    # Simulating a complex JSON payload typical of airline backends (e.g. Navitaire / Amadeus)
    return {
        "status": "success",
        "data": {
            "searchCriteria": {
                "origin": origin,
                "destination": destination,
                "departureDate": date
            },
            "flightResults": {
                "journeys": [
                    {
                        "journeyId": f"JNY-{random.randint(1000,9999)}",
                        "segments": [
                            {
                                "flightDesignator": {
                                    "carrierCode": "6E",
                                    "flightNumber": f"{random.randint(100, 999)}"
                                },
                                "origin": origin,
                                "destination": destination,
                                "departureTime": f"{date}T08:00:00",
                                "arrivalTime": f"{date}T10:30:00"
                            }
                        ],
                        "fares": {
                            "ECONOMY": {
                                "totalAmount": base_fare,
                                "currency": "INR",
                                "taxBreakdown": {
                                    "base": base_fare * 0.8,
                                    "taxes": base_fare * 0.2
                                }
                            },
                            "BUSINESS": {
                                "totalAmount": base_fare * 3.5,
                                "currency": "INR",
                                "taxBreakdown": {
                                    "base": base_fare * 3.5 * 0.8,
                                    "taxes": base_fare * 3.5 * 0.2
                                }
                            }
                        }
                    },
                    {
                        "journeyId": f"JNY-{random.randint(1000,9999)}",
                        "segments": [
                            {
                                "flightDesignator": {
                                    "carrierCode": "6E",
                                    "flightNumber": f"{random.randint(100, 999)}"
                                },
                                "origin": origin,
                                "destination": destination,
                                "departureTime": f"{date}T15:00:00",
                                "arrivalTime": f"{date}T17:30:00"
                            }
                        ],
                        "fares": {
                            "ECONOMY": {
                                "totalAmount": base_fare + 450,
                                "currency": "INR",
                                "taxBreakdown": {
                                    "base": (base_fare + 450) * 0.8,
                                    "taxes": (base_fare + 450) * 0.2
                                }
                            }
                        }
                    }
                ]
            }
        }
    }
