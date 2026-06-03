"""
Serves the full taxonomy to the frontend.
Frontend fetches this ONCE on app load and caches it.
This eliminates the need to keep the TypeScript file in sync manually.

Cache-Control: 24h — taxonomy rarely changes.
ETag: hash of the serialized taxonomy — enables conditional requests.
"""
from __future__ import annotations
import hashlib
import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.taxonomy.registry import TAXONOMY

router = APIRouter(prefix="/taxonomy", tags=["Taxonomy"])

# Build once at startup not per-request
_TAXONOMY_PAYLOAD: dict = TAXONOMY.to_api_dict()
_TAXONOMY_JSON: str = json.dumps(
    _TAXONOMY_PAYLOAD,
    separators=(",", ":"),
    sort_keys=True,
)
_ETAG: str = f'"{hashlib.sha256(_TAXONOMY_JSON.encode()).hexdigest()}"'


@router.get(
    "",
    summary="Get full clinical taxonomy",
    description=(
        "Returns all taxonomy data: medical history items, exam fields, "
        "findings, diagnoses, and investigations. \n"
        "Frontend should fetch this once on app load and cache it. "
        "Supports ETag conditional requests."
    ),
    response_description="Full taxonomy dictionary",
)
async def get_taxonomy(request: Request) -> Response:
    # Conditional GET support — return 304 if frontend has current version
    if request.headers.get("if-none-match") == _ETAG:
        return Response(status_code=304)

    return Response(
        content=_TAXONOMY_JSON,
        media_type="application/json",
        headers={
            "Cache-Control": "public, max-age=86400",  # 24 hours
            "ETag": _ETAG,
        },
    )


@router.get(
    "/medical-history",
    summary="Medical history taxonomy only",
)
async def get_medical_history_taxonomy():
    return {
        "taxonomy": _TAXONOMY_PAYLOAD["medical_history"],
        "dental_relevant_questions": _TAXONOMY_PAYLOAD["dental_relevant_questions"],
    }


@router.get(
    "/examination",
    summary="Clinical examination taxonomy only",
)
async def get_examination_taxonomy():
    return {"taxonomy": _TAXONOMY_PAYLOAD["examination"]}


@router.get(
    "/findings",
    summary="Clinical findings (problems) taxonomy only",
)
async def get_findings_taxonomy():
    return {"taxonomy": _TAXONOMY_PAYLOAD["findings"]}


@router.get(
    "/diagnoses",
    summary="Diagnosis taxonomy only",
)
async def get_diagnoses_taxonomy():
    return {"taxonomy": _TAXONOMY_PAYLOAD["diagnoses"]}


@router.get(
    "/investigations",
    summary="Investigation taxonomy only",
)
async def get_investigations_taxonomy():
    return {"taxonomy": _TAXONOMY_PAYLOAD["investigations"]}