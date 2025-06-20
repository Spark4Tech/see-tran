# run.py
from app import create_app, db
from app.models import (
    # Existing models
    Agency, FunctionalArea, Vendor, Component, Function,
    IntegrationPoint, UserRole, UpdateLog, Standard, TagGroup, Tag,
    AgencyFunctionImplementation,
    # GTFS models
    GTFSAgency, GTFSStop, GTFSRoute, GTFSCalendar, GTFSCalendarDate,
    GTFSTrip, GTFSStopTime, GTFSShape, GTFSFeedInfo,
    GTFSFareMedia, GTFSRiderCategory, GTFSFareProduct, 
    GTFSTimeframe, GTFSFareLegRule, GTFSFareTransferRule
)
import os
import click

# Create the Flask app using the factory pattern
app = create_app()

# Ensure models are imported so Flask-Migrate can detect them
@app.shell_context_processor
def make_shell_context():
    return {
        'app': app,
        'db': db,
        # Existing models
        'Agency': Agency,
        'FunctionalArea': FunctionalArea,
        'Function': Function,
        'Vendor': Vendor,
        'Component': Component,
        'IntegrationPoint': IntegrationPoint,
        'UserRole': UserRole,
        'UpdateLog': UpdateLog,
        'Standard': Standard,
        'TagGroup': TagGroup,
        'Tag': Tag,
        # GTFS models
        'GTFSAgency': GTFSAgency,
        'GTFSStop': GTFSStop,
        'GTFSRoute': GTFSRoute,
        'GTFSCalendar': GTFSCalendar,
        'GTFSCalendarDate': GTFSCalendarDate,
        'GTFSTrip': GTFSTrip,
        'GTFSStopTime': GTFSStopTime,
        'GTFSShape': GTFSShape,
        'GTFSFeedInfo': GTFSFeedInfo,
        'GTFSFareMedia': GTFSFareMedia,
        'GTFSRiderCategory': GTFSRiderCategory,
        'GTFSFareProduct': GTFSFareProduct,
        'GTFSTimeframe': GTFSTimeframe,
        'GTFSFareLegRule': GTFSFareLegRule,
        'GTFSFareTransferRule': GTFSFareTransferRule,
    }

# Add CLI command for loading GTFS data
@app.cli.command()
@click.argument('gtfs_directory')
@click.option('--clear', is_flag=True, help='Clear existing GTFS data first')
def load_gtfs(gtfs_directory, clear):
    """Load GTFS data from directory"""
    from gtfs_loader import GTFSLoader
    loader = GTFSLoader(app, gtfs_directory)
    summary = loader.load_all(clear_existing=clear)
    click.echo(f"✅ Loaded {summary['total_records']} records in {summary['duration']:.2f}s")
    click.echo(f"📊 Files processed: {summary['files_processed']}")
    click.echo(f"🔄 Records affected: {summary['total_affected']}")

if __name__ == '__main__':
    app.run(debug=True)