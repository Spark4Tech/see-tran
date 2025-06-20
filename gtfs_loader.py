#!/usr/bin/env python3
"""
GTFS Data Loader - Idempotent loader for GTFS static data into PostgreSQL

Usage:
    python gtfs_loader.py /path/to/gtfs/files
    
Or as a module:
    from gtfs_loader import GTFSLoader
    loader = GTFSLoader(app, '/path/to/gtfs/files')
    loader.load_all()
"""

import os
import csv
import sys
from pathlib import Path
from datetime import datetime, date, time
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from app import create_app, db
from app.models import (
    GTFSAgency, GTFSStop, GTFSRoute, GTFSCalendar, GTFSCalendarDate, GTFSTrip, 
    GTFSStopTime, GTFSShape, GTFSFeedInfo, GTFSFareMedia, GTFSRiderCategory, 
    GTFSFareProduct, GTFSTimeframe, GTFSFareLegRule, GTFSFareTransferRule
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GTFSLoader:
    """Idempotent GTFS data loader with upsert capabilities"""
    
    def __init__(self, app, gtfs_directory: str):
        self.app = app
        self.gtfs_directory = Path(gtfs_directory)
        self.stats = {}
        
        # File mapping: filename -> (model_class, required)
        self.file_mapping = {
            'agency.txt': (GTFSAgency, True),
            'stops.txt': (GTFSStop, True),
            'routes.txt': (GTFSRoute, True),
            'calendar.txt': (GTFSCalendar, True),
            'calendar_dates.txt': (GTFSCalendarDate, False),
            'trips.txt': (GTFSTrip, True),
            'stop_times.txt': (GTFSStopTime, True),
            'shapes.txt': (GTFSShape, False),
            'feed_info.txt': (GTFSFeedInfo, False),
            'fare_media.txt': (GTFSFareMedia, False),
            'rider_categories.txt': (GTFSRiderCategory, False),
            'fare_products.txt': (GTFSFareProduct, False),
            'timeframes.txt': (GTFSTimeframe, False),
            'fare_leg_rules.txt': (GTFSFareLegRule, False),
            'fare_transfer_rules.txt': (GTFSFareTransferRule, False),
        }
    
    def validate_files(self) -> bool:
        """Validate that required GTFS files exist"""
        missing_required = []
        
        for filename, (model_class, required) in self.file_mapping.items():
            file_path = self.gtfs_directory / filename
            if required and not file_path.exists():
                missing_required.append(filename)
        
        if missing_required:
            logger.error(f"Missing required GTFS files: {missing_required}")
            return False
        
        logger.info(f"GTFS directory validation passed: {self.gtfs_directory}")
        return True
    
    def parse_gtfs_date(self, date_str: str) -> Optional[date]:
        """Parse GTFS date format YYYYMMDD"""
        if not date_str or date_str.strip() == '':
            return None
        try:
            return datetime.strptime(date_str.strip(), '%Y%m%d').date()
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            return None
    
    def parse_gtfs_time(self, time_str: str) -> Optional[time]:
        """Parse GTFS time format HH:MM:SS (can be > 24 hours)"""
        if not time_str or time_str.strip() == '':
            return None
        
        try:
            time_str = time_str.strip()
            parts = time_str.split(':')
            if len(parts) != 3:
                return None
            
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            
            # Handle times >= 24:00:00 by wrapping to next day
            if hours >= 24:
                hours = hours % 24
            
            return time(hours, minutes, seconds)
        except (ValueError, IndexError):
            logger.warning(f"Invalid time format: {time_str}")
            return None
    
    def clean_field_value(self, value: Any, field_name: str, model_class) -> Any:
        """Clean and convert field values based on model field types"""
        if value == '' or value is None:
            return None
        
        # Get field type from model
        if hasattr(model_class, '__table__'):
            column = model_class.__table__.columns.get(field_name)
            if column is not None:
                column_type = str(column.type)
                
                # Handle different data types
                if 'INTEGER' in column_type:
                    try:
                        return int(float(value)) if value != '' else None
                    except (ValueError, TypeError):
                        return None
                elif 'DECIMAL' in column_type or 'NUMERIC' in column_type:
                    try:
                        return Decimal(str(value)) if value != '' else None
                    except (ValueError, TypeError):
                        return None
                elif 'FLOAT' in column_type or 'REAL' in column_type:
                    try:
                        return float(value) if value != '' else None
                    except (ValueError, TypeError):
                        return None
                elif 'DATE' in column_type:
                    return self.parse_gtfs_date(str(value))
                elif 'TIME' in column_type:
                    return self.parse_gtfs_time(str(value))
        
        # Default: return as string, stripped
        return str(value).strip() if value is not None else None
    
    def read_gtfs_file(self, filename: str, model_class) -> List[Dict[str, Any]]:
        """Read and parse a GTFS CSV file"""
        file_path = self.gtfs_directory / filename
        
        if not file_path.exists():
            logger.info(f"Optional file {filename} not found, skipping")
            return []
        
        records = []
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    # Clean field names (remove BOM, strip whitespace)
                    cleaned_row = {}
                    for key, value in row.items():
                        clean_key = key.strip().replace('\ufeff', '') if key else key
                        cleaned_value = self.clean_field_value(value, clean_key, model_class)
                        if clean_key:  # Only add non-empty keys
                            cleaned_row[clean_key] = cleaned_value
                    
                    if cleaned_row:  # Only add non-empty rows
                        records.append(cleaned_row)
                
                logger.info(f"Read {len(records)} records from {filename}")
                
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            raise
        
        return records
    
    def upsert_records(self, model_class, records: List[Dict[str, Any]]) -> int:
        """Upsert records using PostgreSQL ON CONFLICT"""
        if not records:
            return 0
        
        table = model_class.__table__
        primary_key_cols = [col.name for col in table.primary_key.columns]
        
        try:
            # Use PostgreSQL's INSERT ... ON CONFLICT ... DO UPDATE
            stmt = insert(table).values(records)
            
            # Create update dict for all non-primary key columns
            update_dict = {
                col.name: stmt.excluded[col.name] 
                for col in table.columns 
                if col.name not in primary_key_cols
            }
            
            if update_dict:  # Only if there are columns to update
                stmt = stmt.on_conflict_do_update(
                    index_elements=primary_key_cols,
                    set_=update_dict
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=primary_key_cols)
            
            result = db.session.execute(stmt)
            affected_rows = result.rowcount
            
            logger.info(f"Upserted {affected_rows} records into {table.name}")
            return affected_rows
            
        except Exception as e:
            logger.error(f"Error upserting {table.name}: {e}")
            db.session.rollback()
            raise
    
    def load_file(self, filename: str, model_class) -> int:
        """Load a single GTFS file"""
        logger.info(f"Loading {filename}...")
        
        records = self.read_gtfs_file(filename, model_class)
        if not records:
            return 0
        
        # Filter records to only include fields that exist in the model
        table_columns = {col.name for col in model_class.__table__.columns}
        filtered_records = []
        
        for record in records:
            filtered_record = {
                key: value for key, value in record.items() 
                if key in table_columns
            }
            if filtered_record:
                filtered_records.append(filtered_record)
        
        affected_rows = self.upsert_records(model_class, filtered_records)
        self.stats[filename] = {
            'records_processed': len(filtered_records),
            'records_affected': affected_rows
        }
        
        return affected_rows
    
    def clear_existing_data(self):
        """Clear existing GTFS data in dependency order"""
        logger.info("Clearing existing GTFS data...")
        
        # Order matters due to foreign key constraints
        clear_order = [
            GTFSFareTransferRule, GTFSFareLegRule, GTFSStopTime, GTFSTrip, 
            GTFSCalendarDate, GTFSCalendar, GTFSRoute, GTFSStop, GTFSShape,
            GTFSFareProduct, GTFSTimeframe, GTFSRiderCategory, GTFSFareMedia,
            GTFSAgency, GTFSFeedInfo
        ] 
            CalendarDate, Calendar, Route, Stop, Shape,
            FareProduct, Timeframe, RiderCategory, FareMedia,
            Agency, FeedInfo
        ]
        
        for model_class in clear_order:
            try:
                count = db.session.query(model_class).count()
                if count > 0:
                    db.session.query(model_class).delete()
                    logger.info(f"Cleared {count} records from {model_class.__tablename__}")
            except Exception as e:
                logger.error(f"Error clearing {model_class.__tablename__}: {e}")
                db.session.rollback()
                raise
        
        db.session.commit()
    
    def load_all(self, clear_existing: bool = False) -> Dict[str, Any]:
        """Load all GTFS files in the correct order"""
        start_time = datetime.now()
        
        if not self.validate_files():
            raise ValueError("GTFS file validation failed")
        
        with self.app.app_context():
            try:
                if clear_existing:
                    self.clear_existing_data()
                
                # Load in dependency order
                load_order = [
                    'feed_info.txt', 'agency.txt', 'stops.txt', 'shapes.txt',
                    'routes.txt', 'calendar.txt', 'calendar_dates.txt', 'trips.txt',
                    'stop_times.txt', 'fare_media.txt', 'rider_categories.txt',
                    'fare_products.txt', 'timeframes.txt', 'fare_leg_rules.txt',
                    'fare_transfer_rules.txt'
                ]
                
                for filename in load_order:
                    if filename in self.file_mapping:
                        model_class, required = self.file_mapping[filename]
                        self.load_file(filename, model_class)
                
                db.session.commit()
                
                end_time = datetime.now()
                duration = end_time - start_time
                
                summary = {
                    'success': True,
                    'duration': duration.total_seconds(),
                    'files_processed': len(self.stats),
                    'total_records': sum(s['records_processed'] for s in self.stats.values()),
                    'total_affected': sum(s['records_affected'] for s in self.stats.values()),
                    'file_stats': self.stats,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat()
                }
                
                logger.info(f"GTFS load completed successfully in {duration}")
                logger.info(f"Total records processed: {summary['total_records']}")
                logger.info(f"Total records affected: {summary['total_affected']}")
                
                return summary
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"GTFS load failed: {e}")
                raise


def main():
    """CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: python gtfs_loader.py /path/to/gtfs/files")
        sys.exit(1)
    
    gtfs_directory = sys.argv[1]
    
    if not os.path.exists(gtfs_directory):
        print(f"Error: Directory {gtfs_directory} does not exist")
        sys.exit(1)
    
    # Create Flask app
    app = create_app()
    
    # Load GTFS data
    loader = GTFSLoader(app, gtfs_directory)
    
    try:
        # Ask if user wants to clear existing data
        clear_existing = input("Clear existing GTFS data before loading? (y/N): ").lower().startswith('y')
        
        summary = loader.load_all(clear_existing=clear_existing)
        
        print("\n=== GTFS Load Summary ===")
        print(f"Duration: {summary['duration']:.2f} seconds")
        print(f"Files processed: {summary['files_processed']}")
        print(f"Records processed: {summary['total_records']}")
        print(f"Records affected: {summary['total_affected']}")
        
        print("\n=== File Details ===")
        for filename, stats in summary['file_stats'].items():
            print(f"{filename}: {stats['records_processed']} processed, {stats['records_affected']} affected")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()