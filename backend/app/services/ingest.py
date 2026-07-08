"""Turns crawler_agent job results into rows in the backend's own SQLite DB."""
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from .. import models


def ingest_solicitation_search(db: Session, source: str, result: dict[str, Any]) -> int:
    """Ingests results from any crawl job that returns the shared
    {"items": [...]} shape (dibbs_search, sam_search)."""
    inserted = 0
    for item in result.get("items", []):
        solicitation_id = item.get("solicitation_id")
        if not solicitation_id:
            continue

        existing = (
            db.query(models.Solicitation)
            .filter(
                models.Solicitation.source == source,
                models.Solicitation.solicitation_id == solicitation_id,
            )
            .first()
        )

        close_date = None
        if item.get("close_date"):
            try:
                close_date = datetime.fromisoformat(item["close_date"])
            except ValueError:
                close_date = None

        fields = dict(
            nsn=item.get("nsn"),
            title=item.get("title"),
            description=item.get("description"),
            qty=item.get("qty"),
            naics_code=item.get("naics_code"),
            set_aside_type=item.get("set_aside_type"),
            is_sdvosb=bool(item.get("is_sdvosb")),
            close_date=close_date,
            specs=item.get("specs"),
            raw_url=item.get("raw_url"),
            status="open",
        )

        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
        else:
            db.add(
                models.Solicitation(source=source, solicitation_id=solicitation_id, **fields)
            )
            inserted += 1

    db.commit()
    return inserted


def ingest_nsn_marketplace(db: Session, solicitation_id: int, result: dict[str, Any]) -> int:
    inserted = 0
    matched_nsn = result.get("nsn")
    for item in result.get("suppliers", []):
        name = item.get("name")
        if not name:
            continue

        supplier = (
            db.query(models.Supplier)
            .filter(models.Supplier.name == name, models.Supplier.url == item.get("url"))
            .first()
        )
        if not supplier:
            supplier = models.Supplier(
                name=name,
                cage_code=item.get("cage_code"),
                source_marketplace=item.get("source_marketplace"),
                contact_email=item.get("contact_email"),
                url=item.get("url"),
            )
            db.add(supplier)
            db.flush()  # get supplier.id before creating the match

        match = models.SupplierMatch(
            solicitation_id=solicitation_id,
            supplier_id=supplier.id,
            matched_nsn=matched_nsn,
            source_page_url=item.get("url"),
            scraped_price=item.get("price"),
        )
        db.add(match)
        inserted += 1

    db.commit()
    return inserted
