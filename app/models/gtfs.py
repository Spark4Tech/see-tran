# app/models/gtfs.py
from sqlalchemy import String, Integer, Float, Date, Time, Boolean, Text, ForeignKey, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import date, time
from app import db

# GTFS Models with prefix to avoid naming conflicts
class GTFSAgency(db.Model):
    __tablename__ = "gtfs_agency"
    
    agency_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agency_url: Mapped[str] = mapped_column(String(500), nullable=False)
    agency_timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    agency_lang: Mapped[Optional[str]] = mapped_column(String(10))
    agency_phone: Mapped[Optional[str]] = mapped_column(String(50))
    agency_fare_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Relationships
    routes: Mapped[list["GTFSRoute"]] = relationship(back_populates="agency")


class GTFSStop(db.Model):
    __tablename__ = "gtfs_stops"
    
    stop_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    stop_code: Mapped[Optional[str]] = mapped_column(String(50))
    stop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stop_desc: Mapped[Optional[str]] = mapped_column(Text)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    zone_id: Mapped[Optional[str]] = mapped_column(String(50))
    stop_url: Mapped[Optional[str]] = mapped_column(String(500))
    location_type: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    parent_station: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("gtfs_stops.stop_id"))
    stop_timezone: Mapped[Optional[str]] = mapped_column(String(50))
    wheelchair_boarding: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Self-referential relationship for parent station
    child_stops: Mapped[list["GTFSStop"]] = relationship(remote_side=[stop_id])
    
    # Relationships
    stop_times: Mapped[list["GTFSStopTime"]] = relationship(back_populates="stop")


class GTFSRoute(db.Model):
    __tablename__ = "gtfs_routes"
    
    route_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(50), ForeignKey("gtfs_agency.agency_id"), nullable=False)
    route_short_name: Mapped[Optional[str]] = mapped_column(String(50))
    route_long_name: Mapped[str] = mapped_column(String(255), nullable=False)
    route_desc: Mapped[Optional[str]] = mapped_column(Text)
    route_type: Mapped[int] = mapped_column(Integer, nullable=False)
    route_url: Mapped[Optional[str]] = mapped_column(String(500))
    route_color: Mapped[Optional[str]] = mapped_column(String(6), default="FFFFFF")
    route_text_color: Mapped[Optional[str]] = mapped_column(String(6), default="000000")
    route_sort_order: Mapped[Optional[int]] = mapped_column(Integer)
    network_id: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Relationships
    agency: Mapped["GTFSAgency"] = relationship(back_populates="routes")
    trips: Mapped[list["GTFSTrip"]] = relationship(back_populates="route")


class GTFSCalendar(db.Model):
    __tablename__ = "gtfs_calendar"
    
    service_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    monday: Mapped[int] = mapped_column(Integer, nullable=False)
    tuesday: Mapped[int] = mapped_column(Integer, nullable=False)
    wednesday: Mapped[int] = mapped_column(Integer, nullable=False)
    thursday: Mapped[int] = mapped_column(Integer, nullable=False)
    friday: Mapped[int] = mapped_column(Integer, nullable=False)
    saturday: Mapped[int] = mapped_column(Integer, nullable=False)
    sunday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Relationships
    trips: Mapped[list["GTFSTrip"]] = relationship(back_populates="calendar")
    calendar_dates: Mapped[list["GTFSCalendarDate"]] = relationship(back_populates="calendar")


class GTFSCalendarDate(db.Model):
    __tablename__ = "gtfs_calendar_dates"
    
    service_id: Mapped[str] = mapped_column(String(50), ForeignKey("gtfs_calendar.service_id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    exception_type: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Relationships
    calendar: Mapped["GTFSCalendar"] = relationship(back_populates="calendar_dates")


class GTFSTrip(db.Model):
    __tablename__ = "gtfs_trips"
    
    trip_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(50), ForeignKey("gtfs_routes.route_id"), nullable=False)
    service_id: Mapped[str] = mapped_column(String(50), ForeignKey("gtfs_calendar.service_id"), nullable=False)
    trip_headsign: Mapped[Optional[str]] = mapped_column(String(255))
    trip_short_name: Mapped[Optional[str]] = mapped_column(String(50))
    direction_id: Mapped[Optional[int]] = mapped_column(Integer)
    block_id: Mapped[Optional[str]] = mapped_column(String(50))
    shape_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("gtfs_shapes.shape_id"))
    wheelchair_accessible: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    bikes_allowed: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Relationships
    route: Mapped["GTFSRoute"] = relationship(back_populates="trips")
    calendar: Mapped["GTFSCalendar"] = relationship(back_populates="trips")
    shape: Mapped[Optional["GTFSShape"]] = relationship(back_populates="trips")
    stop_times: Mapped[list["GTFSStopTime"]] = relationship(back_populates="trip")


class GTFSStopTime(db.Model):
    __tablename__ = "gtfs_stop_times"
    
    trip_id: Mapped[str] = mapped_column(String(100), ForeignKey("gtfs_trips.trip_id"), primary_key=True)
    arrival_time: Mapped[time] = mapped_column(Time, nullable=False)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)
    stop_id: Mapped[str] = mapped_column(String(50), ForeignKey("gtfs_stops.stop_id"), nullable=False)
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_headsign: Mapped[Optional[str]] = mapped_column(String(255))
    pickup_type: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    drop_off_type: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    shape_dist_traveled: Mapped[Optional[float]] = mapped_column(Float)
    timepoint: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    
    # Relationships
    trip: Mapped["GTFSTrip"] = relationship(back_populates="stop_times")
    stop: Mapped["GTFSStop"] = relationship(back_populates="stop_times")


class GTFSShape(db.Model):
    __tablename__ = "gtfs_shapes"
    
    shape_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    shape_pt_lat: Mapped[float] = mapped_column(Float, primary_key=True)
    shape_pt_lon: Mapped[float] = mapped_column(Float, primary_key=True)
    shape_pt_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    shape_dist_traveled: Mapped[Optional[float]] = mapped_column(Float)
    
    # Relationships
    trips: Mapped[list["GTFSTrip"]] = relationship(back_populates="shape")


class GTFSFeedInfo(db.Model):
    __tablename__ = "gtfs_feed_info"
    
    feed_publisher_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    feed_publisher_url: Mapped[str] = mapped_column(String(500), nullable=False)
    feed_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    feed_start_date: Mapped[Optional[date]] = mapped_column(Date)
    feed_end_date: Mapped[Optional[date]] = mapped_column(Date)
    feed_version: Mapped[Optional[str]] = mapped_column(String(50))
    feed_contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    feed_contact_url: Mapped[Optional[str]] = mapped_column(String(500))


# GTFS-Fares v2 Tables
class GTFSFareMedia(db.Model):
    __tablename__ = "gtfs_fare_media"
    
    fare_media_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    fare_media_name: Mapped[Optional[str]] = mapped_column(String(255))
    fare_media_type: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Relationships
    fare_products: Mapped[list["GTFSFareProduct"]] = relationship(back_populates="fare_media")


class GTFSRiderCategory(db.Model):
    __tablename__ = "gtfs_rider_categories"
    
    rider_category_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    rider_category_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_default_fare_category: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    min_age: Mapped[Optional[int]] = mapped_column(Integer)
    max_age: Mapped[Optional[int]] = mapped_column(Integer)
    eligibility_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Relationships
    fare_products: Mapped[list["GTFSFareProduct"]] = relationship(back_populates="rider_category")


class GTFSFareProduct(db.Model):
    __tablename__ = "gtfs_fare_products"
    
    fare_product_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    fare_product_name: Mapped[Optional[str]] = mapped_column(String(255))
    rider_category_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("gtfs_rider_categories.rider_category_id"))
    fare_media_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("gtfs_fare_media.fare_media_id"))
    amount: Mapped[DECIMAL] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    
    # Relationships
    rider_category: Mapped[Optional["GTFSRiderCategory"]] = relationship(back_populates="fare_products")
    fare_media: Mapped[Optional["GTFSFareMedia"]] = relationship(back_populates="fare_products")
    fare_leg_rules: Mapped[list["GTFSFareLegRule"]] = relationship(back_populates="fare_product")
    fare_transfer_rules: Mapped[list["GTFSFareTransferRule"]] = relationship(back_populates="fare_product")


class GTFSTimeframe(db.Model):
    __tablename__ = "gtfs_timeframes"
    
    timeframe_group_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    start_time: Mapped[time] = mapped_column(Time, primary_key=True)
    end_time: Mapped[time] = mapped_column(Time, primary_key=True)
    service_id: Mapped[str] = mapped_column(String(50), ForeignKey("gtfs_calendar.service_id"), nullable=False)
    
    fare_leg_rules_from: Mapped[list["GTFSFareLegRule"]] = relationship(
        back_populates="from_timeframe",
        cascade="all, delete-orphan",
        foreign_keys="GTFSFareLegRule.from_timeframe_group_id"
    )
    fare_leg_rules_to: Mapped[list["GTFSFareLegRule"]] = relationship(
        back_populates="to_timeframe",
        cascade="all, delete-orphan",
        foreign_keys="GTFSFareLegRule.to_timeframe_group_id"
    )


class GTFSFareLegRule(db.Model):
    __tablename__ = "gtfs_fare_leg_rules"
    
    leg_group_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    network_id: Mapped[Optional[str]] = mapped_column(String(50))
    fare_product_id: Mapped[str] = mapped_column(String(50), ForeignKey("gtfs_fare_products.fare_product_id"), primary_key=True)
    from_timeframe_group_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("gtfs_timeframes.timeframe_group_id"),
        primary_key=True
    )
    to_timeframe_group_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("gtfs_timeframes.timeframe_group_id")
    )
    
    # Relationships
    fare_product: Mapped["GTFSFareProduct"] = relationship(back_populates="fare_leg_rules")

    from_timeframe: Mapped[Optional["GTFSTimeframe"]] = relationship(
        back_populates="fare_leg_rules_from",
        foreign_keys=[from_timeframe_group_id]
    )
    to_timeframe: Mapped[Optional["GTFSTimeframe"]] = relationship(
        back_populates="fare_leg_rules_to",
        foreign_keys=[to_timeframe_group_id]
    )


class GTFSFareTransferRule(db.Model):
    __tablename__ = "gtfs_fare_transfer_rules"
    
    from_leg_group_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    to_leg_group_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    fare_product_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("gtfs_fare_products.fare_product_id"))
    transfer_count: Mapped[Optional[int]] = mapped_column(Integer)
    duration_limit: Mapped[Optional[int]] = mapped_column(Integer)
    duration_limit_type: Mapped[Optional[int]] = mapped_column(Integer)
    fare_transfer_type: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Relationships
    fare_product: Mapped[Optional["GTFSFareProduct"]] = relationship(back_populates="fare_transfer_rules")