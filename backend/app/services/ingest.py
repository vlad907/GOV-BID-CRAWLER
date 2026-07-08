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

        # One DIBBS solicitation can cover many NSNs - keep a row per
        # (solicitation, NSN) pair rather than collapsing them.
        existing = (
            db.query(models.Solicitation)
            .filter(
                models.Solicitation.source == source,
                models.Solicitation.solicitation_id == solicitation_id,
                models.Solicitation.nsn == item.get("nsn"),
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


def _upsert_supplier_matches(
    db: Session, solicitation_id: int, matched_nsn: str | None, suppliers: list[dict[str, Any]]
) -> int:
    inserted = 0
    for item in suppliers:
        name = item.get("name")
        if not name:
            continue

        # Prefer matching on CAGE code (a stable company identifier); fall
        # back to name so suppliers without a CAGE still dedupe.
        supplier_query = db.query(models.Supplier)
        if item.get("cage_code"):
            supplier = supplier_query.filter(
                models.Supplier.cage_code == item.get("cage_code")
            ).first()
        else:
            supplier = supplier_query.filter(models.Supplier.name == name).first()

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

        # Skip if this exact solicitation/supplier pair already exists.
        exists = (
            db.query(models.SupplierMatch)
            .filter(
                models.SupplierMatch.solicitation_id == solicitation_id,
                models.SupplierMatch.supplier_id == supplier.id,
            )
            .first()
        )
        if exists:
            continue

        db.add(
            models.SupplierMatch(
                solicitation_id=solicitation_id,
                supplier_id=supplier.id,
                matched_nsn=matched_nsn,
                source_page_url=item.get("url"),
                scraped_price=item.get("price"),
            )
        )
        inserted += 1

    return inserted


def ingest_nsn_marketplace(db: Session, solicitation_id: int, result: dict[str, Any]) -> int:
    inserted = _upsert_supplier_matches(
        db, solicitation_id, result.get("nsn"), result.get("suppliers", [])
    )
    db.commit()
    return inserted


def ingest_nsn_marketplace_bulk(db: Session, result: dict[str, Any]) -> int:
    """Ingests a bulk supplier lookup - each entry carries its own
    solicitation_id, so one job fans matches out to many solicitations."""
    inserted = 0
    for entry in result.get("bulk", []):
        solicitation_id = entry.get("solicitation_id")
        if solicitation_id is None:
            continue
        inserted += _upsert_supplier_matches(
            db, solicitation_id, entry.get("nsn"), entry.get("suppliers", [])
        )
    db.commit()
    return inserted
