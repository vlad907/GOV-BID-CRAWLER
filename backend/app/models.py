from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Solicitation(Base):
    __tablename__ = "solicitations"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)  # "sam" | "dibbs"
    solicitation_id = Column(String, nullable=False, index=True)
    nsn = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    qty = Column(Integer)
    naics_code = Column(String)
    set_aside_type = Column(String)
    is_sdvosb = Column(Boolean, default=False)
    close_date = Column(DateTime, nullable=True)
    specs = Column(JSON, nullable=True)  # dimensions/specs blob
    raw_url = Column(String, nullable=True)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier_matches = relationship(
        "SupplierMatch", back_populates="solicitation", cascade="all, delete-orphan"
    )
    bid_drafts = relationship(
        "BidDraft", back_populates="solicitation", cascade="all, delete-orphan"
    )


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    cage_code = Column(String, index=True, nullable=True)
    source_marketplace = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    matches = relationship("SupplierMatch", back_populates="supplier")


class SupplierMatch(Base):
    __tablename__ = "supplier_matches"

    id = Column(Integer, primary_key=True)
    solicitation_id = Column(Integer, ForeignKey("solicitations.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    matched_nsn = Column(String, nullable=True)
    source_page_url = Column(String, nullable=True)
    scraped_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    solicitation = relationship("Solicitation", back_populates="supplier_matches")
    supplier = relationship("Supplier", back_populates="matches")
    outreach_drafts = relationship(
        "OutreachDraft", back_populates="supplier_match", cascade="all, delete-orphan"
    )


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id = Column(Integer, primary_key=True)
    supplier_match_id = Column(Integer, ForeignKey("supplier_matches.id"), nullable=False)
    draft_subject = Column(String)
    draft_body = Column(Text)
    status = Column(String, default="draft")  # draft | sent | replied
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier_match = relationship("SupplierMatch", back_populates="outreach_drafts")


class BidDraft(Base):
    __tablename__ = "bid_drafts"

    id = Column(Integer, primary_key=True)
    solicitation_id = Column(Integer, ForeignKey("solicitations.id"), nullable=False)
    cost_basis = Column(Float, nullable=True)
    suggested_markup_pct = Column(Float, nullable=True)
    suggested_price = Column(Float, nullable=True)
    benchmark_award_price = Column(Float, nullable=True)
    status = Column(String, default="draft")  # draft | submitted
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    solicitation = relationship("Solicitation", back_populates="bid_drafts")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, index=True)
    type = Column(String)
    params = Column(JSON, nullable=True)
    status = Column(String, default="pending")  # pending | running | done | error
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
