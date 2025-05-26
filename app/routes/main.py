# app/routes/main.py - Enhanced version
from flask import Blueprint, render_template, jsonify, request
from app import db
from app.models.tran import (
    TransitSystem, FunctionalArea, System, Vendor, IntegrationPoint, 
    UpdateLog, Category, Function, Standard, Tag, TagGroup, UserRole
)
from app.auth import login_required, get_updated_by
from app.utils.errors import (
    json_error_response, json_success_response, 
    html_error_fragment, html_success_fragment
)
from sqlalchemy import func, case
from datetime import datetime, timedelta

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/systems")
def systems_page():
    """Systems management page"""
    return render_template("systems.html")

@main.route("/vendors")
def vendors_page():
    """Vendors management page"""
    return render_template("vendors.html")

# Health and utility endpoints
@main.route("/api/health")
def health_check():
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            "status": "ok", 
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        })
    except Exception as e:
        return json_error_response(f"Health check failed: {str(e)}", 500)

# Count endpoints for dashboard metrics
@main.route("/api/count/transit-systems")
def count_transit_systems():
    try:
        count = TransitSystem.query.count()
        return str(count)
    except Exception as e:
        return "0"

@main.route("/api/count/functional-areas")
def count_functional_areas():
    try:
        count = FunctionalArea.query.count()
        return str(count)
    except Exception as e:
        return "0"

@main.route("/api/count/systems")
def count_systems():
    try:
        count = System.query.count()
        return str(count)
    except Exception as e:
        return "0"

@main.route("/api/count/integration-points")
def count_integration_points():
    try:
        count = IntegrationPoint.query.count()
        return str(count)
    except Exception as e:
        return "0"

@main.route("/api/count/vendors")
def count_vendors():
    try:
        count = Vendor.query.count()
        return str(count)
    except Exception as e:
        return "0"

# Systems endpoints (keeping existing functionality)
@main.route("/api/systems/list")
def systems_list():
    """Get all systems with filtering"""
    try:
        functional_area = request.args.get('functional_area')
        vendor = request.args.get('vendor')
        status = request.args.get('status')
        
        query = System.query.join(FunctionalArea).join(TransitSystem)
        
        # Apply filters
        if functional_area:
            query = query.filter(FunctionalArea.name == functional_area)
        if vendor:
            query = query.join(Vendor).filter(Vendor.name == vendor)
        if status:
            if status == 'issues':
                query = query.filter(System.known_issues.isnot(None))
            elif status == 'no_issues':
                query = query.filter(System.known_issues.is_(None))
        
        systems = query.all()
        
        html = ""
        for system in systems:
            status_indicator = "red" if system.known_issues else "green"
            vendor_name = system.vendor.name if system.vendor else "No Vendor"
            
            html += f'''
            <div class="system-card bg-slate-800/50 rounded-lg border border-slate-700/30 p-4 hover:bg-slate-800/70 transition-all cursor-pointer"
                 hx-get="/api/systems/{system.id}/details" hx-target="#system-details" hx-swap="innerHTML">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center space-x-3 mb-2">
                            <div class="w-3 h-3 bg-{status_indicator}-500 rounded-full"></div>
                            <h3 class="font-semibold text-white text-lg">{system.name}</h3>
                        </div>
                        <p class="text-slate-300 text-sm mb-2">{system.functional_area.name}</p>
                        <div class="flex items-center space-x-4 text-xs text-slate-400">
                            <span>📍 {system.functional_area.name}</span>
                            <span>🏢 {vendor_name}</span>
                            <span>📅 {system.deployment_date.strftime('%Y-%m-%d') if system.deployment_date else 'No Date'}</span>
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="bg-slate-700 px-2 py-1 rounded text-xs text-slate-300 mb-2">
                            v{system.version or 'Unknown'}
                        </div>
                        <div class="text-xs text-slate-500">
                            {system.update_frequency or 'Unknown'}
                        </div>
                    </div>
                </div>
                {f'<div class="mt-3 p-2 bg-red-900/20 border border-red-700/30 rounded text-xs text-red-300"><strong>Issues:</strong> {system.known_issues}</div>' if system.known_issues else ''}
            </div>
            '''
        
        if not html:
            html = '''
            <div class="text-center py-12">
                <div class="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <h3 class="text-lg font-medium text-slate-400 mb-2">No Systems Found</h3>
                <p class="text-slate-500">Try adjusting your filters or add new systems.</p>
            </div>
            '''
        
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading systems: {str(e)}")

@main.route("/api/systems/<int:system_id>/details")
def system_details(system_id):
    """Get detailed information about a specific system"""
    try:
        system = System.query.get_or_404(system_id)
        
        # Integration points
        integrations = ""
        if system.integration_points:
            integrations = "<h4 class='font-medium text-white mb-2'>Integration Points:</h4><ul class='space-y-1'>"
            for ip in system.integration_points:
                integrations += f'<li class="text-sm text-slate-300">• {ip.name} ({ip.description or "No description"})</li>'
            integrations += "</ul>"
        
        # User roles
        roles = ""
        if system.user_roles:
            roles = "<h4 class='font-medium text-white mb-2 mt-4'>User Roles:</h4><ul class='space-y-1'>"
            for role in system.user_roles:
                roles += f'<li class="text-sm text-slate-300">• {role.role_name}: {role.description or "No description"}</li>'
            roles += "</ul>"
        
        # Additional metadata
        metadata = ""
        if system.additional_metadata:
            metadata = "<h4 class='font-medium text-white mb-2 mt-4'>Additional Information:</h4><ul class='space-y-1'>"
            for key, value in system.additional_metadata.items():
                metadata += f'<li class="text-sm text-slate-300">• {key.replace("_", " ").title()}: {value}</li>'
            metadata += "</ul>"
        
        vendor_info = ""
        if system.vendor:
            website_link = f'<a href="{system.vendor.website}" target="_blank" class="text-blue-400 hover:text-blue-300">{system.vendor.website}</a>' if system.vendor.website else "No website"
            vendor_info = f'''
            <h4 class='font-medium text-white mb-2 mt-4'>Vendor Information:</h4>
            <div class="bg-slate-700/30 p-3 rounded">
                <p class="text-sm text-slate-300 mb-1"><strong>Name:</strong> {system.vendor.name}</p>
                <p class="text-sm text-slate-300 mb-1"><strong>Website:</strong> {website_link}</p>
                <p class="text-sm text-slate-300 mb-1"><strong>Contact:</strong> {system.vendor.contact_email or system.vendor.contact_name or "No contact info"}</p>
                <p class="text-sm text-slate-300"><strong>Description:</strong> {system.vendor.description or "No description"}</p>
            </div>
            '''
        
        html = f'''
        <div class="glass-effect rounded-xl p-6 border border-slate-700/50">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-2xl font-bold text-white">{system.name}</h2>
                <button class="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors" 
                        onclick="document.getElementById('system-details').innerHTML = `
                        <div class='glass-effect rounded-xl p-6 border border-slate-700/50 text-center'>
                            <div class='w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4'>
                                <svg class='w-8 h-8 text-slate-500' fill='currentColor' viewBox='0 0 20 20'>
                                    <path d='M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z'/>
                                </svg>
                            </div>
                            <h3 class='text-lg font-medium text-slate-400 mb-2'>System Details</h3>
                            <p class='text-slate-500 text-sm'>Click on a system to view detailed information, vendor details, and integration points.</p>
                        </div>`">
                    ✕ Close
                </button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                    <h3 class="font-medium text-white mb-3">System Information</h3>
                    <div class="space-y-2 text-sm">
                        <p class="text-slate-300"><strong>Version:</strong> {system.version or "Unknown"}</p>
                        <p class="text-slate-300"><strong>Deployment Date:</strong> {system.deployment_date.strftime('%B %d, %Y') if system.deployment_date else "Unknown"}</p>
                        <p class="text-slate-300"><strong>Update Frequency:</strong> {system.update_frequency or "Unknown"}</p>
                        <p class="text-slate-300"><strong>Functional Area:</strong> {system.functional_area.name}</p>
                        <p class="text-slate-300"><strong>Transit System:</strong> {system.functional_area.transit_system.name}</p>
                    </div>
                    
                    {vendor_info}
                </div>
                
                <div>
                    {f'<div class="bg-red-900/20 border border-red-700/30 rounded p-3 mb-4"><h4 class="font-medium text-red-300 mb-2">Known Issues:</h4><p class="text-sm text-red-200">{system.known_issues}</p></div>' if system.known_issues else '<div class="bg-green-900/20 border border-green-700/30 rounded p-3 mb-4"><h4 class="font-medium text-green-300 mb-2">Status:</h4><p class="text-sm text-green-200">No known issues</p></div>'}
                    
                    {integrations}
                    {roles}
                    {metadata}
                </div>
            </div>
        </div>
        '''
        
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading system details: {str(e)}")

# Vendors endpoints (keeping existing functionality)
@main.route("/api/vendors/list")
def vendors_list():
    """Get all vendors with filtering and system counts"""
    try:
        search = request.args.get('search', '').lower()
        sort_by = request.args.get('sort', 'name')
        
        query = db.session.query(
            Vendor,
            func.count(System.id).label('system_count')
        ).outerjoin(System).group_by(Vendor.id)
        
        if search:
            query = query.filter(Vendor.name.ilike(f'%{search}%'))
        
        if sort_by == 'systems':
            query = query.order_by(func.count(System.id).desc())
        elif sort_by == 'recent':
            subquery = db.session.query(
                System.vendor_id,
                func.max(System.deployment_date).label('latest_deployment')
            ).group_by(System.vendor_id).subquery()
            
            query = query.outerjoin(subquery, Vendor.id == subquery.c.vendor_id)\
                         .order_by(subquery.c.latest_deployment.desc().nullslast())
        else:
            query = query.order_by(Vendor.name)
        
        vendors_with_counts = query.all()
        
        html = ""
        for vendor, system_count in vendors_with_counts:
            functional_areas = db.session.query(FunctionalArea.name)\
                .join(System).filter(System.vendor_id == vendor.id)\
                .distinct().all()
            
            fa_names = [fa.name for fa in functional_areas]
            fa_display = ", ".join(fa_names[:2])
            if len(fa_names) > 2:
                fa_display += f" +{len(fa_names) - 2} more"
            
            latest_system = System.query.filter_by(vendor_id=vendor.id)\
                .order_by(System.deployment_date.desc().nullslast()).first()
            
            latest_deployment = "No deployments"
            if latest_system and latest_system.deployment_date:
                latest_deployment = latest_system.deployment_date.strftime('%Y-%m-%d')
            
            website_display = ""
            if vendor.website:
                domain = vendor.website.replace('https://', '').replace('http://', '').split('/')[0]
                website_display = f'<a href="{vendor.website}" target="_blank" class="text-blue-400 hover:text-blue-300 text-xs">{domain}</a>'
            
            html += f'''
            <div class="vendor-card bg-slate-800/50 rounded-lg border border-slate-700/30 p-6 hover:bg-slate-800/70 transition-all cursor-pointer"
                 hx-get="/api/vendors/{vendor.id}/details" hx-target="#vendor-details" hx-swap="innerHTML">
                <div class="flex items-start justify-between mb-4">
                    <div class="flex-1">
                        <h3 class="font-semibold text-white text-xl mb-2">{vendor.name}</h3>
                        <p class="text-slate-300 text-sm mb-3">{vendor.description or 'No description available'}</p>
                        <div class="flex items-center space-x-4 text-xs text-slate-400">
                            <span>🏢 {system_count} systems</span>
                            <span>📍 {fa_display if fa_names else 'No systems'}</span>
                            <span>📅 Latest: {latest_deployment}</span>
                        </div>
                    </div>
                    <div class="text-right">
                        <div class="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mb-2">
                            <span class="text-lg font-bold text-white">{system_count}</span>
                        </div>
                        <div class="text-xs text-slate-500 text-center">Systems</div>
                    </div>
                </div>
                
                <div class="flex items-center justify-between pt-3 border-t border-slate-700/30">
                    <div class="flex items-center space-x-3">
                        {website_display}
                        {f'<span class="text-xs text-slate-500">• {vendor.contact_email or vendor.contact_name}</span>' if vendor.contact_email or vendor.contact_name else ''}
                    </div>
                    <div class="flex items-center space-x-2">
                        <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span class="text-xs text-slate-400">Active</span>
                    </div>
                </div>
            </div>
            '''
        
        if not html:
            html = '''
            <div class="text-center py-12">
                <div class="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                    </svg>
                </div>
                <h3 class="text-lg font-medium text-slate-400 mb-2">No Vendors Found</h3>
                <p class="text-slate-500">Try adjusting your search or add new vendors.</p>
            </div>
            '''
        
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading vendors: {str(e)}")

@main.route("/api/vendors/<int:vendor_id>/details")
def vendor_details(vendor_id):
    """Get detailed information about a specific vendor"""
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        
        systems_by_area = {}
        systems = System.query.filter_by(vendor_id=vendor.id).join(FunctionalArea).all()
        
        for system in systems:
            area_name = system.functional_area.name
            if area_name not in systems_by_area:
                systems_by_area[area_name] = []
            systems_by_area[area_name].append(system)
        
        systems_html = ""
        if systems_by_area:
            systems_html = "<h4 class='font-medium text-white mb-3'>Systems Portfolio:</h4>"
            for area_name, area_systems in systems_by_area.items():
                systems_html += f'''
                <div class="mb-4">
                    <h5 class="text-sm font-medium text-blue-400 mb-2">{area_name}</h5>
                    <div class="space-y-2 ml-3">
                '''
                for system in area_systems:
                    status_color = "red" if system.known_issues else "green"
                    systems_html += f'''
                    <div class="flex items-center justify-between p-2 bg-slate-700/30 rounded">
                        <div class="flex items-center space-x-2">
                            <div class="w-2 h-2 bg-{status_color}-500 rounded-full"></div>
                            <span class="text-sm text-slate-300">{system.name}</span>
                        </div>
                        <span class="text-xs text-slate-500">v{system.version or 'Unknown'}</span>
                    </div>
                    '''
                systems_html += "</div></div>"
        else:
            systems_html = "<p class='text-slate-400 text-sm'>No systems found for this vendor.</p>"
        
        total_systems = len(systems)
        systems_with_issues = len([s for s in systems if s.known_issues])
        recent_deployments = len([s for s in systems if s.deployment_date and 
                                 (datetime.now().date() - s.deployment_date).days <= 365])
        
        integration_points = set()
        for system in systems:
            for ip in system.integration_points:
                integration_points.add(ip.name)
        
        integrations_html = ""
        if integration_points:
            integrations_html = f'''
            <h4 class='font-medium text-white mb-2 mt-4'>Integration Standards:</h4>
            <div class="flex flex-wrap gap-2">
                {' '.join([f'<span class="px-2 py-1 bg-cyan-600/20 border border-cyan-600/30 rounded text-xs text-cyan-300">{ip}</span>' for ip in integration_points])}
            </div>
            '''
        
        html = f'''
        <div class="glass-effect rounded-xl p-6 border border-slate-700/50">
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center space-x-4">
                    <div class="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                        <span class="text-2xl font-bold text-white">{vendor.name[0].upper()}</span>
                    </div>
                    <div>
                        <h2 class="text-2xl font-bold text-white">{vendor.name}</h2>
                        <p class="text-slate-400">{vendor.description or 'No description available'}</p>
                    </div>
                </div>
                <button class="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors" 
                        onclick="document.getElementById('vendor-details').innerHTML = `
                        <div class='glass-effect rounded-xl p-6 border border-slate-700/50 text-center'>
                            <div class='w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4'>
                                <svg class='w-8 h-8 text-slate-500' fill='currentColor' viewBox='0 0 20 20'>
                                    <path d='M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z'/>
                                </svg>
                            </div>
                            <h3 class='text-lg font-medium text-slate-400 mb-2'>Vendor Details</h3>
                            <p class='text-slate-500 text-sm'>Click on a vendor to view detailed information, system portfolio, and contact details.</p>
                        </div>`">
                    ✕ Close
                </button>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                <div class="bg-blue-600/20 border border-blue-600/30 rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-blue-300">{total_systems}</div>
                    <div class="text-sm text-blue-200">Total Systems</div>
                </div>
                <div class="bg-green-600/20 border border-green-600/30 rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-green-300">{total_systems - systems_with_issues}</div>
                    <div class="text-sm text-green-200">Healthy Systems</div>
                </div>
                <div class="bg-purple-600/20 border border-purple-600/30 rounded-lg p-4 text-center">
                    <div class="text-2xl font-bold text-purple-300">{recent_deployments}</div>
                    <div class="text-sm text-purple-200">Recent Deployments</div>
                </div>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                    <h3 class="font-medium text-white mb-3">Contact Information</h3>
                    <div class="space-y-2 text-sm">
                        <p class="text-slate-300">
                            <strong>Website:</strong> 
                            {f'<a href="{vendor.website}" target="_blank" class="text-blue-400 hover:text-blue-300 ml-2">{vendor.website}</a>' if vendor.website else '<span class="text-slate-500 ml-2">Not provided</span>'}
                        </p>
                        <p class="text-slate-300">
                            <strong>Contact:</strong> 
                            <span class="ml-2">{vendor.contact_email or vendor.contact_name or 'Not provided'}</span>
                        </p>
                        <p class="text-slate-300">
                            <strong>Phone:</strong> 
                            <span class="ml-2">{vendor.contact_phone or vendor.vendor_phone or 'Not provided'}</span>
                        </p>
                    </div>
                    
                    {integrations_html}
                </div>
                
                <div>
                    {systems_html}
                </div>
            </div>
        </div>
        '''
        
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading vendor details: {str(e)}")

# Additional existing endpoints with error handling
@main.route("/api/vendors/stats")
def vendors_stats():
    """Get vendor statistics for dashboard"""
    try:
        stats = {
            'total_vendors': Vendor.query.count(),
            'active_vendors': db.session.query(Vendor).join(System).distinct().count(),
            'top_vendor': None,
            'avg_systems_per_vendor': 0
        }
        
        top_vendor_query = db.session.query(
            Vendor.name,
            func.count(System.id).label('system_count')
        ).join(System).group_by(Vendor.id, Vendor.name)\
         .order_by(func.count(System.id).desc()).first()
        
        if top_vendor_query:
            stats['top_vendor'] = {
                'name': top_vendor_query.name,
                'system_count': top_vendor_query.system_count
            }
        
        if stats['active_vendors'] > 0:
            total_systems = System.query.filter(System.vendor_id.isnot(None)).count()
            stats['avg_systems_per_vendor'] = round(total_systems / stats['active_vendors'], 1)
        
        return jsonify(stats)
    except Exception as e:
        return json_error_response(f"Error getting vendor stats: {str(e)}")

@main.route("/api/integration/standards")
def integration_standards():
    """Get most common integration standards"""
    try:
        # Get standards from the Standards table
        standards = db.session.query(
            Standard.name,
            func.count(IntegrationPoint.id).label('usage_count')
        ).join(Standard.integration_points)\
         .group_by(Standard.name)\
         .order_by(func.count(IntegrationPoint.id).desc())\
         .limit(5).all()
        
        html = ""
        for standard, count in standards:
            html += f'''
            <div class="flex items-center justify-between p-2 bg-cyan-600/10 border border-cyan-600/20 rounded">
                <span class="text-sm text-cyan-300">{standard}</span>
                <span class="text-xs text-cyan-400">{count} uses</span>
            </div>
            '''
        
        if not html:
            html = '<div class="text-center text-slate-500 text-sm py-4">No integration standards found</div>'
        
        return html
    except Exception as e:
        return f'<div class="text-center text-slate-500 text-sm py-4">Error loading standards</div>'

@main.route("/api/vendors/performance")
def vendor_performance():
    """Get vendor performance insights"""
    try:
        reliable_vendor = db.session.query(
            Vendor.name,
            func.count(System.id).label('total_systems'),
            func.sum(case((System.known_issues.isnot(None), 1), else_=0)).label('issues_count')
        ).join(System).group_by(Vendor.id, Vendor.name)\
         .having(func.count(System.id) > 0)\
         .order_by((func.sum(case((System.known_issues.isnot(None), 1), else_=0)) / func.count(System.id)).asc())\
         .first()
        
        newest_vendor = db.session.query(
            Vendor.name,
            func.min(System.deployment_date).label('first_deployment')
        ).join(System).group_by(Vendor.id, Vendor.name)\
         .order_by(func.min(System.deployment_date).desc())\
         .first()
        
        largest_vendor = db.session.query(
            Vendor.name,
            func.count(System.id).label('system_count')
        ).join(System).group_by(Vendor.id, Vendor.name)\
         .order_by(func.count(System.id).desc())\
         .first()
        
        return jsonify({
            'most_reliable': reliable_vendor.name if reliable_vendor else 'N/A',
            'newest': newest_vendor.name if newest_vendor else 'N/A',
            'largest': largest_vendor.name if largest_vendor else 'N/A'
        })
    except Exception as e:
        return json_error_response(f"Error getting vendor performance: {str(e)}")

# Keep remaining existing endpoints
@main.route("/api/systems/overview")
def systems_overview():
    try:
        systems = System.query.join(FunctionalArea).join(Vendor).limit(10).all()
        
        html = ""
        for system in systems:
            status_color = "green" if system.known_issues is None else "yellow"
            html += f"""
            <div class="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700/30 hover:bg-slate-800/70 transition-colors">
                <div class="flex items-center space-x-4">
                    <div class="w-3 h-3 bg-{status_color}-500 rounded-full"></div>
                    <div>
                        <h4 class="font-medium text-white">{system.name}</h4>
                        <p class="text-sm text-slate-400">{system.functional_area.name} • {system.vendor.name if system.vendor else 'No Vendor'}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-sm text-slate-300">{system.version or 'No Version'}</p>
                    <p class="text-xs text-slate-500">{system.deployment_date.strftime('%Y-%m-%d') if system.deployment_date else 'No Date'}</p>
                </div>
            </div>
            """
        
        if not html:
            html = """
            <div class="text-center py-12">
                <svg class="w-12 h-12 text-slate-600 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <h3 class="text-lg font-medium text-slate-400 mb-2">No Systems Found</h3>
                <p class="text-slate-500 mb-4">Add your first transit system to get started.</p>
                <button class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
                    Add System
                </button>
            </div>
            """
        
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading systems overview: {str(e)}")

@main.route("/api/vendors/top")
def top_vendors():
    try:
        vendors = db.session.query(Vendor, func.count(System.id).label('system_count'))\
            .join(System).group_by(Vendor.id).order_by(func.count(System.id).desc()).limit(5).all()
        
        html = ""
        for vendor, count in vendors:
            html += f"""
            <div class="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                <div>
                    <p class="font-medium text-white text-sm">{vendor.name}</p>
                    <p class="text-xs text-slate-400">{count} systems</p>
                </div>
                <div class="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                    <span class="text-xs font-bold text-white">{count}</span>
                </div>
            </div>
            """
        
        if not html:
            html = """
            <div class="text-center py-6 text-slate-500">
                <p class="text-sm">No vendor data available</p>
            </div>
            """
        
        return html
    except Exception as e:
        return f'<div class="text-center py-6 text-slate-500"><p class="text-sm">Error loading vendors</p></div>'

@main.route("/api/integration/health")
def integration_health():
    try:
        total_systems = System.query.count()
        integrated_systems = db.session.query(System).join(System.integration_points).distinct().count()
        
        if total_systems > 0:
            health_percentage = (integrated_systems / total_systems) * 100
        else:
            health_percentage = 0
        
        color = "green" if health_percentage >= 80 else "yellow" if health_percentage >= 50 else "red"
        
        html = f"""
        <div class="text-center">
            <div class="relative inline-flex items-center justify-center w-16 h-16 mb-4">
                <svg class="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
                    <path class="text-slate-700" stroke="currentColor" stroke-width="3" fill="none" d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"/>
                    <path class="text-{color}-500" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="{health_percentage}, 100" d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"/>
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                    <span class="text-lg font-bold text-white">{health_percentage:.0f}%</span>
                </div>
            </div>
            <h4 class="text-sm font-medium text-white mb-1">Integration Health</h4>
            <p class="text-xs text-slate-400">{integrated_systems} of {total_systems} systems integrated</p>
        </div>
        """
        
        return html
    except Exception as e:
        return f'<div class="text-center py-6 text-slate-500"><p class="text-sm">Error calculating health</p></div>'

@main.route("/api/activity/recent")
def recent_activity():
    try:
        recent_updates = UpdateLog.query.join(System).order_by(UpdateLog.update_date.desc()).limit(10).all()
        
        html = ""
        for update in recent_updates:
            time_ago = datetime.utcnow() - update.update_date
            if time_ago.days > 0:
                time_str = f"{time_ago.days}d ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600}h ago"
            else:
                time_str = f"{time_ago.seconds // 60}m ago"
            
            html += f"""
            <div class="flex items-center space-x-4 p-4 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-colors">
                <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center">
                    <svg class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
                    </svg>
                </div>
                <div class="flex-1">
                    <p class="text-sm font-medium text-white">{update.system.name} updated</p>
                    <p class="text-xs text-slate-400">{update.change_summary[:100] + '...' if update.change_summary and len(update.change_summary) > 100 else update.change_summary or 'No summary provided'}</p>
                    <p class="text-xs text-slate-500 mt-1">by {update.updated_by} • {time_str}</p>
                </div>
            </div>
            """
        
        if not html:
            html = """
            <div class="text-center py-8">
                <svg class="w-12 h-12 text-slate-600 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                </svg>
                <h3 class="text-lg font-medium text-slate-400 mb-2">No Recent Activity</h3>
                <p class="text-slate-500">System updates will appear here.</p>
            </div>
            """
        
        return html
    except Exception as e:
        return f'<div class="text-center py-8 text-slate-500"><p class="text-sm">Error loading activity</p></div>'

@main.route("/api/systems/refresh")
def systems_refresh():
    return systems_overview()

# Transit Systems Management Routes
@main.route("/transit-systems")
def transit_systems_page():
    """Transit systems management page"""
    return render_template("transit_systems.html")

@main.route("/api/transit-systems/list")
def transit_systems_list():
    """Get all transit systems with filtering"""
    try:
        search = request.args.get('search', '').lower()
        
        query = TransitSystem.query
        
        # Apply search filter
        if search:
            query = query.filter(TransitSystem.name.ilike(f'%{search}%'))
        
        transit_systems = query.order_by(TransitSystem.name).all()
        
        return render_template('fragments/transit_system_list.html', 
                             transit_systems=transit_systems)
    except Exception as e:
        return html_error_fragment(f"Error loading transit systems: {str(e)}")

@main.route("/api/transit-systems/<int:transit_system_id>/details")
def transit_system_details(transit_system_id):
    """Get detailed information about a specific transit system"""
    try:
        transit_system = TransitSystem.query.get_or_404(transit_system_id)
        
        return render_template('fragments/transit_system_details.html', 
                             transit_system=transit_system)
    except Exception as e:
        return html_error_fragment(f"Error loading transit system details: {str(e)}")

@main.route("/api/transit-systems/form")
def transit_system_form():
    """Return new transit system form"""
    try:
        return render_template('fragments/transit_system_form.html', 
                             transit_system=None)
    except Exception as e:
        return html_error_fragment(f"Error loading form: {str(e)}")

@main.route("/api/transit-systems/<int:transit_system_id>/form")
def transit_system_edit_form(transit_system_id):
    """Return edit transit system form"""
    try:
        transit_system = TransitSystem.query.get_or_404(transit_system_id)
        
        return render_template('fragments/transit_system_form.html', 
                             transit_system=transit_system)
    except Exception as e:
        return html_error_fragment(f"Error loading edit form: {str(e)}")

@main.route("/api/transit-systems", methods=['POST'])
@login_required
def create_transit_system():
    """Create a new transit system"""
    try:
        data = request.form
        
        # Validate required fields
        if not data.get('name'):
            return html_error_fragment("Transit system name is required")
        
        # Check for duplicate names
        existing = TransitSystem.query.filter_by(name=data['name']).first()
        if existing:
            return html_error_fragment(f"Transit system '{data['name']}' already exists")
        
        # Process additional metadata
        additional_metadata = {}
        metadata_keys = data.getlist('metadata_key[]')
        metadata_values = data.getlist('metadata_value[]')
        
        for key, value in zip(metadata_keys, metadata_values):
            if key.strip() and value.strip():  # Only add non-empty pairs
                additional_metadata[key.strip()] = value.strip()
        
        # Create new transit system with all fields
        transit_system = TransitSystem(
            name=data['name'],
            location=data.get('location') or None,
            description=data.get('description') or None,
            website=data.get('website') or None,
            ceo=data.get('ceo') or None,
            address_hq=data.get('address_hq') or None,
            phone_number=data.get('phone_number') or None,
            transit_map_link=data.get('transit_map_link') or None,
            contact_email=data.get('contact_email') or None,
            contact_phone=data.get('contact_phone') or None,
            contact_name=data.get('contact_name') or None,
            additional_metadata=additional_metadata if additional_metadata else None
        )
        
        db.session.add(transit_system)
        db.session.commit()
        
        return html_success_fragment(f"Transit system '{transit_system.name}' created successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error creating transit system: {str(e)}")

@main.route("/api/transit-systems/<int:transit_system_id>", methods=['PUT'])
@login_required
def update_transit_system(transit_system_id):
    """Update an existing transit system"""
    try:
        transit_system = TransitSystem.query.get_or_404(transit_system_id)
        data = request.form
        
        # Validate required fields
        if not data.get('name'):
            return html_error_fragment("Transit system name is required")
        
        # Check for duplicate names (excluding current system)
        existing = TransitSystem.query.filter(
            TransitSystem.name == data['name'],
            TransitSystem.id != transit_system_id
        ).first()
        if existing:
            return html_error_fragment(f"Transit system '{data['name']}' already exists")
        
        # Process additional metadata
        additional_metadata = {}
        metadata_keys = data.getlist('metadata_key[]')
        metadata_values = data.getlist('metadata_value[]')
        
        for key, value in zip(metadata_keys, metadata_values):
            if key.strip() and value.strip():  # Only add non-empty pairs
                additional_metadata[key.strip()] = value.strip()
        
        # Track changes for logging
        changes = []
        if transit_system.name != data['name']:
            changes.append(f"name: '{transit_system.name}' → '{data['name']}'")
        if transit_system.location != data.get('location'):
            changes.append(f"location updated")
        if transit_system.ceo != data.get('ceo'):
            changes.append(f"CEO updated")
        
        # Update all fields
        transit_system.name = data['name']
        transit_system.location = data.get('location') or None
        transit_system.description = data.get('description') or None
        transit_system.website = data.get('website') or None
        transit_system.ceo = data.get('ceo') or None
        transit_system.address_hq = data.get('address_hq') or None
        transit_system.phone_number = data.get('phone_number') or None
        transit_system.transit_map_link = data.get('transit_map_link') or None
        transit_system.contact_email = data.get('contact_email') or None
        transit_system.contact_phone = data.get('contact_phone') or None
        transit_system.contact_name = data.get('contact_name') or None
        transit_system.additional_metadata = additional_metadata if additional_metadata else None
        
        db.session.commit()
        
        return html_success_fragment(f"Transit system '{transit_system.name}' updated successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error updating transit system: {str(e)}")

@main.route("/api/transit-systems/<int:transit_system_id>", methods=['DELETE'])
@login_required
def delete_transit_system(transit_system_id):
    """Delete a transit system"""
    try:
        transit_system = TransitSystem.query.get_or_404(transit_system_id)
        name = transit_system.name
        
        # Note: Skip logging for transit systems since UpdateLog is for individual systems
        
        # Delete the transit system (cascade will handle related records)
        db.session.delete(transit_system)
        db.session.commit()
        
        return html_success_fragment(f"Transit system '{name}' deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error deleting transit system: {str(e)}")
    
# Functional Areas Management Routes
@main.route("/functional-areas")
def functional_areas_page():
    """Functional areas management page"""
    return render_template("functional_areas.html")

@main.route("/api/functional-areas/list")
def functional_areas_list():
    """Get all functional areas with filtering"""
    try:
        search = request.args.get('search', '').lower()
        transit_system = request.args.get('transit_system')
        
        query = FunctionalArea.query.join(TransitSystem)
        
        # Apply filters
        if search:
            query = query.filter(FunctionalArea.name.ilike(f'%{search}%'))
        if transit_system:
            try:
                ts_id = int(transit_system)
                query = query.filter(FunctionalArea.transit_system_id == ts_id)
            except ValueError:
                pass  # Invalid transit system ID, ignore filter
        
        functional_areas = query.order_by(TransitSystem.name, FunctionalArea.name).all()
        
        return render_template('fragments/functional_area_list.html', 
                             functional_areas=functional_areas)
    except Exception as e:
        return html_error_fragment(f"Error loading functional areas: {str(e)}")

@main.route("/api/functional-areas/<int:functional_area_id>/details")
def functional_area_details(functional_area_id):
    """Get detailed information about a specific functional area"""
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        
        return render_template('fragments/functional_area_details.html', 
                             functional_area=functional_area)
    except Exception as e:
        return html_error_fragment(f"Error loading functional area details: {str(e)}")

@main.route("/api/functional-areas/form")
def functional_area_form():
    """Return new functional area form"""
    try:
        # Get all transit systems for the dropdown
        transit_systems = TransitSystem.query.order_by(TransitSystem.name).all()
        
        return render_template('fragments/functional_area_form.html', 
                             functional_area=None, 
                             transit_systems=transit_systems)
    except Exception as e:
        return html_error_fragment(f"Error loading form: {str(e)}")

@main.route("/api/functional-areas/<int:functional_area_id>/form")
def functional_area_edit_form(functional_area_id):
    """Return edit functional area form"""
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        transit_systems = TransitSystem.query.order_by(TransitSystem.name).all()
        
        return render_template('fragments/functional_area_form.html', 
                             functional_area=functional_area,
                             transit_systems=transit_systems)
    except Exception as e:
        return html_error_fragment(f"Error loading edit form: {str(e)}")

@main.route("/api/functional-areas", methods=['POST'])
@login_required
def create_functional_area():
    """Create a new functional area"""
    try:
        data = request.form
        
        # Validate required fields
        if not data.get('name'):
            return html_error_fragment("Functional area name is required")
        
        if not data.get('transit_system_id'):
            return html_error_fragment("Transit system is required")
        
        try:
            transit_system_id = int(data['transit_system_id'])
        except ValueError:
            return html_error_fragment("Invalid transit system selected")
        
        # Verify transit system exists
        transit_system = TransitSystem.query.get(transit_system_id)
        if not transit_system:
            return html_error_fragment("Selected transit system does not exist")
        
        # Check for duplicate names within the same transit system
        existing = FunctionalArea.query.filter_by(
            name=data['name'], 
            transit_system_id=transit_system_id
        ).first()
        if existing:
            return html_error_fragment(f"Functional area '{data['name']}' already exists in {transit_system.name}")
        
        # Create new functional area
        functional_area = FunctionalArea(
            name=data['name'],
            description=data.get('description') or None,
            transit_system_id=transit_system_id
        )
        
        db.session.add(functional_area)
        db.session.commit()
        
        return html_success_fragment(f"Functional area '{functional_area.name}' created successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error creating functional area: {str(e)}")

@main.route("/api/functional-areas/<int:functional_area_id>", methods=['PUT'])
@login_required
def update_functional_area(functional_area_id):
    """Update an existing functional area"""
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        data = request.form
        
        # Validate required fields
        if not data.get('name'):
            return html_error_fragment("Functional area name is required")
        
        if not data.get('transit_system_id'):
            return html_error_fragment("Transit system is required")
        
        try:
            transit_system_id = int(data['transit_system_id'])
        except ValueError:
            return html_error_fragment("Invalid transit system selected")
        
        # Verify transit system exists
        transit_system = TransitSystem.query.get(transit_system_id)
        if not transit_system:
            return html_error_fragment("Selected transit system does not exist")
        
        # Check for duplicate names within the same transit system (excluding current area)
        existing = FunctionalArea.query.filter(
            FunctionalArea.name == data['name'],
            FunctionalArea.transit_system_id == transit_system_id,
            FunctionalArea.id != functional_area_id
        ).first()
        if existing:
            return html_error_fragment(f"Functional area '{data['name']}' already exists in {transit_system.name}")
        
        # Update functional area
        functional_area.name = data['name']
        functional_area.description = data.get('description') or None
        functional_area.transit_system_id = transit_system_id
        
        db.session.commit()
        
        return html_success_fragment(f"Functional area '{functional_area.name}' updated successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error updating functional area: {str(e)}")

@main.route("/api/functional-areas/<int:functional_area_id>", methods=['DELETE'])
@login_required
def delete_functional_area(functional_area_id):
    """Delete a functional area"""
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        name = functional_area.name
        transit_system_name = functional_area.transit_system.name
        
        # Delete the functional area (cascade will handle related records)
        db.session.delete(functional_area)
        db.session.commit()
        
        return html_success_fragment(f"Functional area '{name}' from {transit_system_name} deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error deleting functional area: {str(e)}")

# Helper routes for transit system selection
@main.route("/api/transit-systems/options")
def transit_systems_options():
    """Get transit system options for dropdowns"""
    try:
        transit_systems = TransitSystem.query.order_by(TransitSystem.name).all()
        
        html = '<option value="">All Transit Systems</option>'
        for ts in transit_systems:
            location_part = f" ({ts.location})" if ts.location else ""
            html += f'<option value="{ts.id}">{ts.name}{location_part}</option>'
        
        return html
    except Exception as e:
        return '<option value="">Error loading transit systems</option>'

@main.route("/api/transit-systems/selector")
def transit_systems_selector():
    """Get transit system selector widget"""
    try:
        transit_systems = TransitSystem.query.order_by(TransitSystem.name).all()
        
        html = '''
        <h3 class="text-lg font-semibold text-white mb-4">Transit Systems</h3>
        <div class="space-y-2">
        '''
        
        for ts in transit_systems:
            area_count = FunctionalArea.query.filter_by(transit_system_id=ts.id).count()
            html += f'''
            <div class="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-colors cursor-pointer"
                 onclick="filterByTransitSystem({ts.id})">
                <div>
                    <p class="text-sm font-medium text-white">{ts.name}</p>
                    {f'<p class="text-xs text-slate-400">{ts.location}</p>' if ts.location else ''}
                </div>
                <span class="text-xs text-slate-500">{area_count} areas</span>
            </div>
            '''
        
        html += '''
        </div>
        <script>
        function filterByTransitSystem(tsId) {
            document.getElementById('transit-system-filter').value = tsId;
            htmx.trigger('#transit-system-filter', 'change');
        }
        </script>
        '''
        
        return html
    except Exception as e:
        return f'<p class="text-red-400 text-sm">Error loading transit systems: {str(e)}</p>'

# Count endpoints for new entities
@main.route("/api/count/categories")
def count_categories():
    try:
        count = Category.query.count()
        return str(count)
    except Exception as e:
        return "0"

@main.route("/api/count/functions")
def count_functions():
    try:
        count = Function.query.count()
        return str(count)
    except Exception as e:
        return "0"
    

@main.route('/contribute')
def contribute():
    return render_template('contribute.html')