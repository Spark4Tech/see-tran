# app/routes/main.py
from flask import Blueprint, render_template, jsonify, request, url_for
from app import db
from app.models.tran import (
    Agency, FunctionalArea, Component, Vendor, IntegrationPoint, 
    UpdateLog, Function, Standard, Tag, TagGroup, UserRole, AgencyFunctionImplementation,
    integration_standard, component_integration, Configuration, ConfigurationProduct, Product
)
from app.forms.forms import AgencyForm, VendorForm, ComponentForm
from app.auth import login_required, get_updated_by
from app.utils.errors import (
    json_error_response, json_success_response, 
    html_error_fragment, html_success_fragment,
    json_form_error_response
)
from app.utils.afi import (
    create_afi_with_optional_children,
    component_supports_function,
    get_children_supporting_function,
    record_afi_history,
)
from sqlalchemy import func, case, distinct
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

main = Blueprint("main", __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/components")
def components_page():
    """Components management page"""
    return render_template("components.html")

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
@main.route("/api/count/agencies")
def count_agencies():
    try:
        count = Agency.query.count()
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

@main.route("/api/count/components")
def count_components():
    try:
        count = Component.query.count()
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

@main.route("/api/count/configurations")
def count_configurations():
    try:
        return str(Configuration.query.count())
    except Exception:
        return "0"

@main.route("/api/count/products")
def count_products():
    try:
        return str(Product.query.count())
    except Exception:
        return "0"

# Components endpoints
@main.route("/api/components/list")
def components_list():
    """Get all components with filtering (updated to use Configuration instead of AFI)."""
    try:
        functional_area = (request.args.get('functional_area') or '').strip()
        agency = (request.args.get('agency') or '').strip()
        status = (request.args.get('status') or '').strip()
        search = (request.args.get('search') or '').strip()
        # vendor filter removed (Component no longer tied to vendor)
        query = db.session.query(Component).distinct()
        if functional_area:
            query = (query
                     .join(Configuration, Configuration.component_id == Component.id)
                     .join(Function, Function.id == Configuration.function_id)
                     .join(FunctionalArea, FunctionalArea.id == Function.functional_area_id)
                     .filter(FunctionalArea.name == functional_area))
        if agency:
            query = (query
                     .join(Configuration, Configuration.component_id == Component.id)
                     .join(Agency, Agency.id == Configuration.agency_id)
                     .filter(Agency.name == agency))
        if status:
            query = (query
                     .join(Configuration, Configuration.component_id == Component.id)
                     .filter(Configuration.status == status))
        if search:
            name_like = f"%{search}%"
            query = query.filter(Component.name.ilike(name_like))
        query = query.order_by(Component.name.asc())
        components = query.all()
        view_components = []
        for component in components:
            agencies_using = (db.session.query(Agency.name)
                              .join(Configuration, Configuration.agency_id == Agency.id)
                              .filter(Configuration.component_id == component.id)
                              .distinct().limit(3).all())
            agencies_display = ", ".join([a.name for a in agencies_using]) or 'No agencies'
            if len(agencies_using) == 3:
                agencies_display += ' +more'
            functions_implemented = (db.session.query(Function.name)
                                     .join(Configuration, Configuration.function_id == Function.id)
                                     .filter(Configuration.component_id == component.id)
                                     .distinct().limit(3).all())
            functions_display = ", ".join([f.name for f in functions_implemented]) or 'No functions'
            if len(functions_implemented) == 3:
                functions_display += ' +more'
            view_components.append(type('VC', (), {
                'id': component.id,
                'name': component.name,
                'is_composite': False,
                'status_indicator': 'green',
                'functions_display': functions_display,
                'vendor_name': '—',
                'agencies_display': agencies_display,
                'deployment_date_str': '',
                'version': None,
                'known_issues': None,
            }))
        return render_template('fragments/component_list.html', components=view_components)
    except Exception as e:
        return html_error_fragment(f"Error loading components: {str(e)}")

@main.route("/api/components/<int:component_id>/details")
def component_details(component_id):
    """Updated component details using Configurations."""
    try:
        component = Component.query.get_or_404(component_id)
        configurations = (Configuration.query
                          .filter_by(component_id=component_id)
                          .join(Agency).join(Function).join(FunctionalArea)
                          .order_by(Agency.name, FunctionalArea.name, Function.name)
                          .all())
        agency_usage_html = ""
        if configurations:
            agency_usage_html = "<h4 class='font-medium text-white mb-3'>Agency Usage:</h4>"
            agencies = {}
            for c in configurations:
                agencies.setdefault(c.agency.name, []).append(c)
            for agency_name, cfgs in agencies.items():
                agency_usage_html += f'''<div class="mb-4"><h5 class="text-sm font-medium text-blue-400 mb-2">{agency_name}</h5><div class="space-y-2 ml-3">'''
                for cfg in cfgs:
                    status_color = "green" if cfg.status == "Active" else "yellow"
                    agency_usage_html += f'''<div class="flex items-center justify-between p-2 bg-slate-700/30 rounded"><div class="flex items-center space-x-2"><div class="w-2 h-2 bg-{status_color}-500 rounded-full"></div><span class="text-sm text-slate-300">{cfg.function.name}</span></div><div class="text-right"><span class="text-xs text-slate-500">{cfg.deployment_date.strftime('%Y-%m-%d') if cfg.deployment_date else 'No date'}</span>{f'<br><span class="text-xs text-slate-400">{cfg.version_label}</span>' if cfg.version_label else ''}</div></div>'''
                agency_usage_html += "</div></div>"
        else:
            agency_usage_html = "<p class='text-slate-400 text-sm'>No configuration usage tracked for this component.</p>"
        roles = ""
        if component.user_roles:
            roles = "<h4 class='font-medium text-white mb-2 mt-4'>User Roles:</h4><ul class='space-y-1'>" + \
                "".join([f'<li class="text-sm text-slate-300">• {r.role_name}: {r.description or "No description"}</li>' for r in component.user_roles]) + "</ul>"
        metadata = ""
        if component.additional_metadata:
            metadata = "<h4 class='font-medium text-white mb-2 mt-4'>Additional Information:</h4><ul class='space-y-1'>" + \
                "".join([f'<li class="text-sm text-slate-300">• {k.replace("_"," ").title()}: {v}</li>' for k,v in component.additional_metadata.items()]) + "</ul>"
        html = f'''<div class="glass-effect rounded-xl p-6 border border-slate-700/50"><div class="flex items-center justify-between mb-4"><div class="flex items-center space-x-3"><h2 class="text-2xl font-bold text-white">{component.name}</h2></div><button class="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors" onclick="clearComponentDetails()">✕ Close</button></div><div class="grid grid-cols-1 gap-6"><div><h3 class="font-medium text-white mb-3">Component Information</h3><div class="space-y-2 text-sm"><p class="text-slate-300"><strong>Template:</strong> Logical component</p></div><div class="mt-6">{agency_usage_html}</div>{roles}{metadata}</div></div></div>'''
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading component details: {str(e)}")

@main.route("/api/agencies/options")
def agencies_filter_options():
    """Get agency options for filter dropdowns (based on Configurations now)."""
    try:
        agencies = (db.session.query(Agency.name)
                    .join(Configuration, Configuration.agency_id == Agency.id)
                    .distinct()
                    .order_by(Agency.name)
                    .all())
        html = '<option value="">All Agencies</option>'
        for agency in agencies:
            html += f'<option value="{agency.name}">{agency.name}</option>'
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading agency options: {str(e)}")

# New full-page component details view
@main.route("/components/<int:component_id>")
def component_detail_page(component_id: int):
    try:
        component = Component.query.get_or_404(component_id)
        configurations = (Configuration.query
                          .filter_by(component_id=component_id)
                          .join(Agency).join(Function).join(FunctionalArea)
                          .order_by(Agency.name, FunctionalArea.name, Function.name)
                          .all())
        by_agency = {}
        for cfg in configurations:
            by_agency.setdefault(cfg.agency.name, []).append(cfg)
        integrations = component.integration_points or []
        return render_template(
            'component_detail.html',
            component=component,
            implementations_by_agency=by_agency,  # variable name kept for template compatibility
            integrations=integrations
        )
    except Exception as e:
        return html_error_fragment(f"Error loading component page: {str(e)}")

def clear_component_details_js():
    return '''
    <script>
    function clearComponentDetails() {
        // Reset component details panel
        document.getElementById('component-details').innerHTML = `
            <div class="glass-effect rounded-xl p-6 border border-slate-700/50 text-center">
                <div class="w-16 h-16 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
                    </svg>
                </div>
                <h3 class="text-lg font-medium text-slate-400 mb-2">Component Details</h3>
                <p class="text-slate-500 text-sm">Select a component to view details</p>
            </div>`;
        
        // Reset vendor details panel
        document.getElementById('vendor-details').innerHTML = `
            <div class="text-center py-4">
                <span class="text-slate-500 text-sm">No component selected</span>
            </div>`;
        
        // Reset integration details panel
        document.getElementById('integration-details').innerHTML = `
            <div class="text-center py-4">
                <span class="text-slate-500 text-sm">No component selected</span>
            </div>`;
    }
    </script>
    '''

# Vendors Management Routes
@main.route("/vendors")
def vendors_page():
    """Vendors management page"""
    return render_template("vendors.html")

@main.route("/api/vendors/list")
def vendors_list():
    """Get all vendors with enhanced filtering and component counts"""
    try:
        search = request.args.get('search', '').lower()
        sort_by = request.args.get('sort', 'name')
        agency_filter = request.args.get('agency', '')
        functional_area_filter = request.args.get('functional_area', '')
        
        # Base query with component counts
        query = db.session.query(
            Vendor,
            func.count(distinct(Component.id)).label('component_count')
        ).outerjoin(Component).group_by(Vendor.id)
        
        # Apply search filter
        if search:
            query = query.filter(Vendor.name.ilike(f'%{search}%'))
        
        # Apply agency filter
        if agency_filter:
            agency_component_ids = db.session.query(Component.id)\
                .join(AgencyFunctionImplementation)\
                .join(Agency)\
                .filter(Agency.name == agency_filter)
            
            query = query.filter(Component.id.in_(agency_component_ids.scalar_subquery()))
        
        # Apply functional area filter
        if functional_area_filter:
            fa_component_ids = db.session.query(Component.id)\
                .join(AgencyFunctionImplementation)\
                .join(Function)\
                .join(FunctionalArea)\
                .filter(FunctionalArea.name == functional_area_filter)
            
            query = query.filter(Component.id.in_(fa_component_ids.scalar_subquery()))
        
        # Apply sorting
        if sort_by == 'components':
            query = query.order_by(func.count(distinct(Component.id)).desc())
        elif sort_by == 'recent':
            # Sort by most recent component deployment
            subquery = db.session.query(
                Component.vendor_id,
                func.max(Component.deployment_date).label('latest_deployment')
            ).group_by(Component.vendor_id).subquery()
            
            query = query.outerjoin(subquery, Vendor.id == subquery.c.vendor_id)\
                         .order_by(subquery.c.latest_deployment.desc().nullslast())
        else:
            query = query.order_by(Vendor.name)
        
        vendors_with_counts = query.all()
        
        for vendor, component_count in vendors_with_counts:
            vendor.component_count = component_count
        
        return render_template('fragments/vendor_list.html', 
                             vendors_with_counts=vendors_with_counts)
    except Exception as e:
        return html_error_fragment(f"Error loading vendors: {str(e)}")

@main.route("/api/vendors/<int:vendor_id>/details")
def vendor_details(vendor_id):
    """Get detailed information about a specific vendor"""
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        
        # Get components grouped by functional area
        components_by_area = {}
        
        components_query = db.session.query(Component, FunctionalArea.name.label('area_name'))\
            .filter(Component.vendor_id == vendor_id)\
            .join(AgencyFunctionImplementation, Component.agency_usages)\
            .join(Function, AgencyFunctionImplementation.function)\
            .join(FunctionalArea, Function.functional_area)\
            .distinct(Component.id, FunctionalArea.name)\
            .all()
        
        for component, area_name in components_query:
            if area_name not in components_by_area:
                components_by_area[area_name] = []
            if component not in components_by_area[area_name]:
                components_by_area[area_name].append(component)
        
        # Get vendor statistics
        total_components = Component.query.filter_by(vendor_id=vendor_id).count()
        components_with_issues = Component.query.filter_by(vendor_id=vendor_id).filter(Component.known_issues.isnot(None)).count()
        recent_deployments = Component.query.filter_by(vendor_id=vendor_id)\
            .filter(Component.deployment_date >= datetime.now().date() - timedelta(days=365)).count()
        
        # Get integration standards
        vendor_components = Component.query.filter_by(vendor_id=vendor_id).all()
        integration_standards = set()
        for component in vendor_components:
            for integration_point in component.integration_points:
                for standard in integration_point.standards:
                    integration_standards.add(standard.name)
        
        vendor.total_components = total_components
        vendor.components_with_issues = components_with_issues
        vendor.recent_deployments = recent_deployments
        vendor.integration_standards = list(integration_standards)
        vendor.components_by_area = components_by_area
        
        return render_template('fragments/vendor_details.html', vendor=vendor)
    except Exception as e:
        return html_error_fragment(f"Error loading vendor details: {str(e)}")

@main.route("/api/vendors/form")
def vendor_form():
    """Return new vendor form"""
    try:
        form = VendorForm()
        return render_template('fragments/vendor_form.html', 
                             form=form, 
                             vendor=None)
    except Exception as e:
        return html_error_fragment(f"Error loading form: {str(e)}")

@main.route("/api/vendors/<int:vendor_id>/form")
def vendor_edit_form(vendor_id):
    """Return edit vendor form"""
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        form = VendorForm()
        form.populate_from_vendor(vendor)
        
        return render_template('fragments/vendor_form.html', 
                             form=form, 
                             vendor=vendor)
    except Exception as e:
        return html_error_fragment(f"Error loading edit form: {str(e)}")

@main.route("/api/vendors", methods=['POST'])
@login_required
def create_vendor():
    """Create a new vendor with JSON response"""
    try:
        form = VendorForm()
        
        if form.validate_on_submit():
            # Check for duplicate names
            existing = Vendor.query.filter_by(name=form.name.data).first()
            if existing:
                return json_error_response(f"Vendor '{form.name.data}' already exists")
            
            # Create new vendor
            vendor = Vendor()
            form.populate_vendor(vendor)
            
            db.session.add(vendor)
            db.session.commit()
            
            return json_success_response(f"Vendor '{vendor.name}' created successfully")
        else:
            return json_form_error_response(form)
        
    except Exception as e:
        db.session.rollback()
        return json_error_response(f"Error creating vendor: {str(e)}")

@main.route("/api/vendors/<int:vendor_id>", methods=['POST'])
@login_required
def update_vendor(vendor_id):
    """Update an existing vendor with JSON response"""
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        form = VendorForm()
        
        if form.validate_on_submit():
            # Check for duplicate names (excluding current vendor)
            existing = Vendor.query.filter(
                Vendor.name == form.name.data,
                Vendor.id != vendor_id
            ).first()
            if existing:
                return json_error_response(f"Vendor '{form.name.data}' already exists")
            
            # Update vendor
            form.populate_vendor(vendor)
            
            db.session.commit()
            
            return json_success_response(f"Vendor '{vendor.name}' updated successfully")
        else:
            return json_form_error_response(form)
        
    except Exception as e:
        db.session.rollback()
        return json_error_response(f"Error updating vendor: {str(e)}")

@main.route("/api/vendors/<int:vendor_id>", methods=['DELETE'])
@login_required
def delete_vendor(vendor_id):
    """Delete a vendor with JSON response"""
    try:
        vendor = Vendor.query.get_or_404(vendor_id)
        name = vendor.name
        
        # Check if vendor has components (prevent deletion)
        component_count = Component.query.filter_by(vendor_id=vendor_id).count()
        if component_count > 0:
            return json_error_response(
                f"Cannot delete vendor '{name}' because it has {component_count} associated components. "
                f"Please reassign or delete the components first."
            )
        
        # Delete the vendor
        db.session.delete(vendor)
        db.session.commit()
        
        return json_success_response(f"Vendor '{name}' deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        return json_error_response(f"Error deleting vendor: {str(e)}")

@main.route("/api/vendors/stats")
def vendors_stats():
    """Get vendor statistics for dashboard with optional filtering"""
    try:
        agency_filter = request.args.get('agency', '')
        functional_area_filter = request.args.get('functional_area', '')
        
        # Base vendor query
        vendor_query = db.session.query(Vendor)
        
        # Apply filters to get relevant vendors
        if agency_filter or functional_area_filter:
            component_subquery = db.session.query(Component.vendor_id).distinct()
            
            if agency_filter:
                component_subquery = component_subquery\
                    .join(AgencyFunctionImplementation)\
                    .join(Agency)\
                    .filter(Agency.name == agency_filter)
            
            if functional_area_filter:
                if not agency_filter:
                    component_subquery = component_subquery.join(AgencyFunctionImplementation)
                component_subquery = component_subquery\
                    .join(Function)\
                    .join(FunctionalArea)\
                    .filter(FunctionalArea.name == functional_area_filter)
            
            # Fix: Use scalar_subquery() to avoid SQLAlchemy warning
            vendor_ids_subquery = component_subquery.scalar_subquery()
            vendor_query = vendor_query.filter(Vendor.id.in_(vendor_ids_subquery))
        
        stats = {
            'total_vendors': vendor_query.count(),
            'active_vendors': vendor_query.join(Component).distinct().count(),
            'top_vendor': None,
            'avg_components_per_vendor': 0
        }
        
        # Get top vendor within filtered set
        top_vendor_query = db.session.query(
            Vendor.name,
            func.count(Component.id).label('component_count')
        ).join(Component)
        
        if agency_filter or functional_area_filter:
            # Apply same filter to top vendor query
            vendor_ids_list = [v.id for v in vendor_query.all()]
            if vendor_ids_list:
                top_vendor_query = top_vendor_query.filter(Vendor.id.in_(vendor_ids_list))
        
        top_vendor_result = top_vendor_query.group_by(Vendor.id, Vendor.name)\
                                          .order_by(func.count(Component.id).desc())\
                                          .first()
        
        if top_vendor_result:
            stats['top_vendor'] = {
                'name': top_vendor_result.name,
                'component_count': top_vendor_result.component_count
            }
        
        # Calculate average components per vendor
        if stats['active_vendors'] > 0:
            total_components_query = db.session.query(func.count(Component.id))\
                .filter(Component.vendor_id.isnot(None))
            
            if agency_filter or functional_area_filter:
                vendor_ids_list = [v.id for v in vendor_query.all()]
                if vendor_ids_list:
                    total_components_query = total_components_query\
                        .filter(Component.vendor_id.in_(vendor_ids_list))
            
            total_components = total_components_query.scalar()
            stats['avg_components_per_vendor'] = round(total_components / stats['active_vendors'], 1)
        
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
    """Get vendor performance insights with filtering support"""
    try:
        agency_filter = request.args.get('agency', '')
        functional_area_filter = request.args.get('functional_area', '')
        
        # Base vendor filter condition
        vendor_filter_condition = True
        
        if agency_filter or functional_area_filter:
            # Build subquery for vendor IDs that match filters
            component_query = db.session.query(Component.vendor_id).distinct()
            
            if agency_filter:
                component_query = component_query\
                    .join(AgencyFunctionImplementation)\
                    .join(Agency)\
                    .filter(Agency.name == agency_filter)
            
            if functional_area_filter:
                component_query = component_query\
                    .join(Function)\
                    .join(FunctionalArea)\
                    .filter(FunctionalArea.name == functional_area_filter)
            
            # Get list of vendor IDs that match the filters
            vendor_ids_list = [row[0] for row in component_query.all() if row[0] is not None]
            if vendor_ids_list:
                vendor_filter_condition = Vendor.id.in_(vendor_ids_list)
            else:
                vendor_filter_condition = False  # No vendors match filters
        
        # Most reliable vendor (least issues)
        reliable_vendor = db.session.query(
            Vendor.name,
            func.count(Component.id).label('total_components'),
            func.sum(case((Component.known_issues.isnot(None), 1), else_=0)).label('issues_count')
        ).join(Component)\
         .filter(vendor_filter_condition)\
         .group_by(Vendor.id, Vendor.name)\
         .having(func.count(Component.id) > 0)\
         .order_by((func.sum(case((Component.known_issues.isnot(None), 1), else_=0)) / func.count(Component.id)).asc())\
         .first()
        
        # Newest vendor (most recent first deployment)
        newest_vendor = db.session.query(
            Vendor.name,
            func.min(Component.deployment_date).label('first_deployment')
        ).join(Component)\
         .filter(vendor_filter_condition)\
         .group_by(Vendor.id, Vendor.name)\
         .order_by(func.min(Component.deployment_date).desc())\
         .first()
        
        # Largest vendor (most components)
        largest_vendor = db.session.query(
            Vendor.name,
            func.count(Component.id).label('component_count')
        ).join(Component)\
         .filter(vendor_filter_condition)\
         .group_by(Vendor.id, Vendor.name)\
         .order_by(func.count(Component.id).desc())\
         .first()
        
        return jsonify({
            'most_reliable': reliable_vendor.name if reliable_vendor else 'N/A',
            'newest': newest_vendor.name if newest_vendor else 'N/A',
            'largest': largest_vendor.name if largest_vendor else 'N/A'
        })
    except Exception as e:
        return json_error_response(f"Error getting vendor performance: {str(e)}")

@main.route("/api/components/overview")
def components_overview():
    try:
        components = Component.query.join(FunctionalArea).join(Vendor).limit(10).all()
        
        html = ""
        for component in components:
            status_color = "green" if component.known_issues is None else "yellow"
            html += f"""
            <div class="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700/30 hover:bg-slate-800/70 transition-colors">
                <div class="flex items-center space-x-4">
                    <div class="w-3 h-3 bg-{status_color}-500 rounded-full"></div>
                    <div>
                        <h4 class="font-medium text-white">{component.name}</h4>
                        <p class="text-sm text-slate-400">{component.functional_area.name} • {component.vendor.name if component.vendor else 'No Vendor'}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-sm text-slate-300">{component.version or 'No Version'}</p>
                    <p class="text-xs text-slate-500">{component.deployment_date.strftime('%Y-%m-%d') if component.deployment_date else 'No Date'}</p>
                </div>
            </div>
            """
        
        if not html:
            html = """
            <div class="text-center py-12">
                <svg class="w-12 h-12 text-slate-600 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <h3 class="text-lg font-medium text-slate-400 mb-2">No Components Found</h3>
                <p class="text-slate-500 mb-4">Add your first agency to get started.</p>
                <button class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
                    Add Component
                </button>
            </div>
            """
        
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading components overview: {str(e)}")

@main.route("/api/vendors/top")
def top_vendors():
    try:
        vendors = db.session.query(Vendor, func.count(Component.id).label('component_count'))\
            .join(Component).group_by(Vendor.id).order_by(func.count(Component.id).desc()).limit(5).all()
        
        html = ""
        for vendor, count in vendors:
            html += f"""
            <div class="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                <div>
                    <p class="font-medium text-white text-sm">{vendor.name}</p>
                    <p class="text-xs text-slate-400">{count} components</p>
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
        total_components = Component.query.count()
        integrated_components = db.session.query(Component).join(Component.integration_points).distinct().count()
        
        if total_components > 0:
            health_percentage = (integrated_components / total_components) * 100
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
            <p class="text-xs text-slate-400">{integrated_components} of {total_components} components integrated</p>
        </div>
        """
        
        return html
    except Exception as e:
        return f'<div class="text-center py-6 text-slate-500"><p class="text-sm">Error calculating health</p></div>'

@main.route("/api/activity/recent")
def recent_activity():
    try:
        recent_updates = UpdateLog.query.join(Component).order_by(UpdateLog.update_date.desc()).limit(10).all()
        
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
                    <p class="text-sm font-medium text-white">{update.component.name} updated</p>
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
                <p class="text-slate-500">Component updates will appear here.</p>
            </div>
            """
        
        return html
    except Exception as e:
        return f'<div class="text-center py-8 text-slate-500"><p class="text-sm">Error loading activity</p></div>'

@main.route("/api/components/refresh")
def components_refresh():
    return components_overview()

# Agencies Management Routes
@main.route("/agencies")
def agencies_page():
    """Agencys management page"""
    return render_template("agencies.html")

@main.route("/api/agencies/list")
def agencies_list():
    """Get all agencys with filtering"""
    try:
        search = request.args.get('search', '').lower()
        
        query = Agency.query
        
        # Apply search filter
        if search:
            query = query.filter(Agency.name.ilike(f'%{search}%'))
        
        agencies = query.order_by(Agency.name).all()
        for agency in agencies:
            agency.logo_url = url_for('static', filename=f'images/transit_logos/{agency.short_name.lower().replace(" ", "_")}_logo.png')
            
        return render_template('fragments/agency_list.html', 
                             agencies=agencies)
    except Exception as e:
        return html_error_fragment(f"Error loading agencys: {str(e)}")

@main.route("/api/agencies/<int:agency_id>/details")
def agency_details(agency_id):
    """Get detailed information about a specific agency"""
    try:
        agency = Agency.query.get_or_404(agency_id)
        agency.header_url = url_for('static', filename=f'images/transit_headers/{agency.short_name.lower().replace(" ", "_")}_header.png')

        
        return render_template('fragments/agency_details.html', 
                             agency=agency)
    except Exception as e:
        return html_error_fragment(f"Error loading agency details: {str(e)}")

@main.route("/api/agencies/form")
def agency_form():
    """Return new agency form"""
    try:
        form = AgencyForm()
        return render_template('fragments/agency_form.html', 
                             form=form, 
                             agency=None)
    except Exception as e:
        return html_error_fragment(f"Error loading form: {str(e)}")


@main.route("/api/agencies/<int:agency_id>/form")
def agency_edit_form(agency_id):
    """Return edit agency form"""
    try:
        agency = Agency.query.get_or_404(agency_id)
        form = AgencyForm()
        form.populate_from_agency(agency)
        
        return render_template('fragments/agency_form.html', 
                             form=form, 
                             agency=agency)
    except Exception as e:
        return html_error_fragment(f"Error loading edit form: {str(e)}")

@main.route("/api/agencies", methods=['POST'])
@login_required
def create_agency():
    """Create a new agency"""
    try:
        form = AgencyForm()
        
        if form.validate_on_submit():
            # Check for duplicate names
            existing = Agency.query.filter_by(name=form.name.data).first()
            if existing:
                return html_error_fragment(f"Agency '{form.name.data}' already exists")
            
            # Process additional metadata
            additional_metadata = {}
            metadata_keys = request.form.getlist('metadata_key[]')
            metadata_values = request.form.getlist('metadata_value[]')
            
            for key, value in zip(metadata_keys, metadata_values):
                if key.strip() and value.strip():
                    additional_metadata[key.strip()] = value.strip()
            
            # Create new agency
            agency = Agency()
            form.populate_agency(agency)
            agency.additional_metadata = additional_metadata if additional_metadata else None
            # Handle plain inputs
            agency.short_name = request.form.get('short_name') or None
            agency.email_domain = form.email_domain.data or None
            
            db.session.add(agency)
            db.session.commit()
            
            return html_success_fragment(f"Agency '{agency.name}' created successfully")
        else:
            # Form validation failed, return form with errors
            return render_template('fragments/agency_form.html', 
                                 form=form, 
                                 agency=None)
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error creating agency: {str(e)}")
    
@main.route("/api/agencies/<int:agency_id>", methods=['POST'])  # Note: Using POST with _method=PUT for HTMX
@login_required
def update_agency(agency_id):
    try:
        agency = Agency.query.get_or_404(agency_id)
        form = AgencyForm()
        
        if form.validate_on_submit():
            # Check for duplicate names (excluding current agency)
            existing = Agency.query.filter(
                Agency.name == form.name.data,
                Agency.id != agency_id
            ).first()
            if existing:
                return html_error_fragment(f"Agency '{form.name.data}' already exists")
            
            # Process additional metadata
            additional_metadata = {}
            metadata_keys = request.form.getlist('metadata_key[]')
            metadata_values = request.form.getlist('metadata_value[]')
            
            for key, value in zip(metadata_keys, metadata_values):
                if key.strip() and value.strip():
                    additional_metadata[key.strip()] = value.strip()
            
            # Update agency
            form.populate_agency(agency)
            agency.additional_metadata = additional_metadata if additional_metadata else None
            # Handle plain inputs
            agency.short_name = request.form.get('short_name') or agency.short_name
            agency.email_domain = form.email_domain.data or None
            
            db.session.commit()
            
            return html_success_fragment(f"Agency '{agency.name}' updated successfully")
        else:
            # Form validation failed, return form with errors
            return render_template('fragments/agency_form.html', 
                                 form=form, 
                                 agency=agency)
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error updating agency: {str(e)}")

@main.route("/api/agencies/<int:agency_id>", methods=['DELETE'])
@login_required
def delete_agency(agency_id):
    try:
        agency = Agency.query.get_or_404(agency_id)
        name = agency.name
        
        # Delete the agency (cascade will handle related records)
        db.session.delete(agency)
        db.session.commit()
        
        return html_success_fragment(f"Agency '{name}' deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error deleting agency: {str(e)}")
    
@main.route("/api/agencies/stats")
def agencies_stats():
    """Get agency statistics for dashboard"""
    try:
        # Total agencies
        total_agencies = Agency.query.count()
        
        # Active implementations
        active_implementations = AgencyFunctionImplementation.query.filter_by(status='Active').count()
        
        # Average implementations per agency
        avg_implementations = 0
        if total_agencies > 0:
            total_implementations = AgencyFunctionImplementation.query.count()
            avg_implementations = round(total_implementations / total_agencies, 1)
        
        # Average vendors per agency (agencies that use components from different vendors)
        avg_vendors = 0
        if total_agencies > 0:
            # Count unique vendors per agency
            vendor_counts = db.session.query(
                AgencyFunctionImplementation.agency_id,
                func.count(func.distinct(Component.vendor_id)).label('vendor_count')
            ).join(Component)\
             .filter(Component.vendor_id.isnot(None))\
             .group_by(AgencyFunctionImplementation.agency_id)\
             .all()
            
            if vendor_counts:
                total_vendor_relationships = sum([count.vendor_count for count in vendor_counts])
                agencies_with_vendors = len(vendor_counts)
                avg_vendors = round(total_vendor_relationships / agencies_with_vendors, 1)
        
        # Most active agency (agency with most implementations)
        most_active = db.session.query(
            Agency.name,
            func.count(AgencyFunctionImplementation.id).label('impl_count')
        ).join(AgencyFunctionImplementation)\
         .group_by(Agency.id, Agency.name)\
         .order_by(func.count(AgencyFunctionImplementation.id).desc())\
         .first()
        
        stats = {
            'total_agencies': total_agencies,
            'active_implementations': active_implementations,
            'avg_implementations_per_agency': avg_implementations,
            'avg_vendors_per_agency': avg_vendors,
            'most_active_agency': most_active.name if most_active else 'N/A',
            'most_active_count': most_active.impl_count if most_active else 0
        }
        
        return jsonify(stats)
    except Exception as e:
        return json_error_response(f"Error getting agency stats: {str(e)}")

@main.route("/api/count/active-implementations")
def count_active_implementations():
    try:
        count = AgencyFunctionImplementation.query.filter_by(status='Active').count()
        return str(count)
    except Exception as e:
        return "0"

@main.route("/api/agencies/insights")
def agency_insights():
    """Get agency insights for the sidebar"""
    try:
        # Most tech-advanced agency
        tech_leader = db.session.query(
            Agency.name,
            func.count(AgencyFunctionImplementation.id).label('tech_count')
        ).join(AgencyFunctionImplementation)\
         .group_by(Agency.id, Agency.name)\
         .order_by(func.count(AgencyFunctionImplementation.id).desc())\
         .first()
        
        # Most common functional area
        common_area = db.session.query(
            FunctionalArea.name,
            func.count(AgencyFunctionImplementation.id).label('usage_count')
        ).join(Function)\
         .join(AgencyFunctionImplementation)\
         .group_by(FunctionalArea.id, FunctionalArea.name)\
         .order_by(func.count(AgencyFunctionImplementation.id).desc())\
         .first()
        
        # Most used vendor
        top_vendor = db.session.query(
            Vendor.name,
            func.count(AgencyFunctionImplementation.id).label('deployment_count')
        ).join(Component)\
         .join(AgencyFunctionImplementation)\
         .group_by(Vendor.id, Vendor.name)\
         .order_by(func.count(AgencyFunctionImplementation.id).desc())\
         .first()
        
        return jsonify({
            'tech_leader': tech_leader.name if tech_leader else 'N/A',
            'tech_leader_count': tech_leader.tech_count if tech_leader else 0,
            'common_area': common_area.name if common_area else 'N/A',
            'top_vendor': top_vendor.name if top_vendor else 'N/A'
        })
    except Exception as e:
        return json_error_response(f"Error getting agency insights: {str(e)}")
    
# Functional Areas Management Routes
@main.route("/functional-areas")
def functional_areas_page():
    return render_template("functional_areas.html")

@main.route("/api/functional-areas/list")
def functional_areas_list():
    try:
        search = request.args.get('search', '').lower()
        
        # Simple query - no agency relationship anymore
        query = FunctionalArea.query
        
        # Apply search filter
        if search:
            query = query.filter(FunctionalArea.name.ilike(f'%{search}%'))
        
        # Order by functional area name only
        functional_areas = query.order_by(FunctionalArea.name).all()
        
        return render_template('fragments/functional_area_list.html', 
                             functional_areas=functional_areas)
    except Exception as e:
        return html_error_fragment(f"Error loading functional areas: {str(e)}")

@main.route("/api/functional-areas/<int:functional_area_id>/details")
def functional_area_details(functional_area_id):
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        
        # Sort functions by criticality (high -> medium -> low) then by name
        criticality_order = {'high': 1, 'medium': 2, 'low': 3}
        sorted_functions = sorted(
            functional_area.functions,
            key=lambda f: (criticality_order.get(f.criticality.value, 4), f.name.lower())
        )
        
        # Add component count for each function
        for function in sorted_functions:
            function.component_count = len(function.components)
            function.agency_count = len(set(impl.agency for impl in function.agency_implementations))
        
        functional_area.sorted_functions = sorted_functions
        
        return render_template('fragments/functional_area_details.html', 
                             functional_area=functional_area)
    except Exception as e:
        return html_error_fragment(f"Error loading functional area details: {str(e)}")

@main.route("/api/functional-areas/form")
def functional_area_form():
    try:
        # Get all agencys for the dropdown
        agencies = Agency.query.order_by(Agency.name).all()
        
        return render_template('fragments/functional_area_form.html', 
                             functional_area=None, 
                             agencies=agencies)
    except Exception as e:
        return html_error_fragment(f"Error loading form: {str(e)}")

@main.route("/api/functional-areas/<int:functional_area_id>/form")
def functional_area_edit_form(functional_area_id):
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        agencies = Agency.query.order_by(Agency.name).all()
        
        return render_template('fragments/functional_area_form.html', 
                             functional_area=functional_area,
                             agencies=agencies)
    except Exception as e:
        return html_error_fragment(f"Error loading edit form: {str(e)}")

@main.route("/api/functional-areas", methods=['POST'])
@login_required
def create_functional_area():
    try:
        data = request.form
        
        # Validate required fields
        if not data.get('name'):
            return html_error_fragment("Functional area name is required")
        
        # Global duplicate check (functional areas are no longer agency-specific)
        existing = FunctionalArea.query.filter_by(name=data['name']).first()
        if existing:
            return html_error_fragment(f"Functional area '{data['name']}' already exists")
        
        # Create new functional area (no agency linkage)
        functional_area = FunctionalArea(
            name=data['name'],
            description=data.get('description') or None
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
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        data = request.form
        
        # Validate required fields
        if not data.get('name'):
            return html_error_fragment("Functional area name is required")
        
        # Global duplicate check excluding current record
        existing = FunctionalArea.query.filter(
            FunctionalArea.name == data['name'],
            FunctionalArea.id != functional_area_id
        ).first()
        if existing:
            return html_error_fragment(f"Functional area '{data['name']}' already exists")
        
        # Update fields (no agency linkage)
        functional_area.name = data['name']
        functional_area.description = data.get('description') or None
        
        db.session.commit()
        
        return html_success_fragment(f"Functional area '{functional_area.name}' updated successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error updating functional area: {str(e)}")

@main.route("/api/functional-areas/<int:functional_area_id>", methods=['DELETE'])
@login_required
def delete_functional_area(functional_area_id):
    try:
        functional_area = FunctionalArea.query.get_or_404(functional_area_id)
        name = functional_area.name
        
        # Delete the functional area (cascade will handle related records)
        db.session.delete(functional_area)
        db.session.commit()
        
        return html_success_fragment(f"Functional area '{name}' deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error deleting functional area: {str(e)}")

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

@main.route("/api/filter-options/functional-areas")
def functional_areas_filter_options():
    """Get functional area options that have associated components"""
    try:
        functional_areas = db.session.query(FunctionalArea.name)\
            .join(Component)\
            .distinct()\
            .order_by(FunctionalArea.name)\
            .all()
        
        html = '<option value="">All Functional Areas</option>'
        for fa in functional_areas:
            html += f'<option value="{fa.name}">{fa.name}</option>'
        
        return html
    except Exception as e:
        return '<option value="">All Functional Areas</option>'

@main.route("/api/filter-options/vendors")
def vendors_filter_options():
    """Get vendor options that have associated components"""
    try:
        vendors = db.session.query(Vendor.name)\
            .join(Component)\
            .distinct()\
            .order_by(Vendor.name)\
            .all()
        
        html = '<option value="">All Vendors</option>'
        for vendor in vendors:
            html += f'<option value="{vendor.name}">{vendor.name}</option>'
        
        return html
    except Exception as e:
        return '<option value="">All Vendors</option>'
    
@main.route("/api/vendors/filter-options/agencies")
def vendor_agencies_filter_options():
    """Get agencies that have vendor relationships for filter dropdown"""
    try:
        # Find agencies that have components from vendors
        agencies = db.session.query(Agency.name)\
            .join(AgencyFunctionImplementation)\
            .join(Component)\
            .join(Vendor)\
            .distinct()\
            .order_by(Agency.name)\
            .all()
        
        html = '<option value="">All Agencies</option>'
        for agency in agencies:
            html += f'<option value="{agency.name}">{agency.name}</option>'
        
        return html
    except Exception as e:
        return '<option value="">All Agencies</option>'

@main.route("/api/vendors/filter-options/functional-areas")
def vendor_functional_areas_filter_options():
    """Get functional areas that have vendor relationships for filter dropdown"""
    try:
        # Find functional areas that have components from vendors
        functional_areas = db.session.query(FunctionalArea.name)\
            .join(Function)\
            .join(AgencyFunctionImplementation)\
            .join(Component)\
            .join(Vendor)\
            .distinct()\
            .order_by(FunctionalArea.name)\
            .all()
        
        html = '<option value="">All Functional Areas</option>'
        for fa in functional_areas:
            html += f'<option value="{fa.name}">{fa.name}</option>'
        
        return html
    except Exception as e:
        return '<option value="">All Functional Areas</option>'

@main.route("/api/components/<int:component_id>/vendor")
def component_vendor_details(component_id):
    """Get vendor information for a specific component (without descriptions)"""
    try:
        component = Component.query.get_or_404(component_id)
        
        if not component.vendor:
            return '''
            <div class="text-center py-4">
                <span class="text-slate-500 text-sm">No vendor assigned</span>
            </div>
            '''
        
        vendor = component.vendor
        website_link = f'<a href="{vendor.website}" target="_blank" class="text-blue-400 hover:text-blue-300">{vendor.website}</a>' if vendor.website else "No website"
        
        html = f'''
        <div class="space-y-3">
            <div class="flex items-center justify-between">
                <span class="text-slate-400 text-sm">Name</span>
                <span class="text-white font-medium">{vendor.name}</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-400 text-sm">Website</span>
                <span class="text-white text-sm">{website_link}</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-400 text-sm">Contact</span>
                <span class="text-white text-sm">{vendor.contact_email or vendor.contact_name or "Not provided"}</span>
            </div>
            <div class="flex items-center justify-between">
                <span class="text-slate-400 text-sm">Phone</span>
                <span class="text-white text-sm">{vendor.contact_phone or vendor.vendor_phone or "Not provided"}</span>
            </div>
        </div>
        '''
        
        return html
    except Exception as e:
        return f'<div class="text-center py-4"><span class="text-red-400 text-sm">Error loading vendor info</span></div>'

@main.route("/api/components/<int:component_id>/integrations")
def component_integration_details(component_id):
    """Get integration points for a specific component (without descriptions)"""
    try:
        component = Component.query.get_or_404(component_id)
        
        if not component.integration_points:
            return '''
            <div class="text-center py-4">
                <span class="text-slate-500 text-sm">No integrations configured</span>
            </div>
            '''
        
        html = '<div class="space-y-2">'
        for ip in component.integration_points:
            html += f'''
            <div class="flex items-center justify-between p-2 bg-slate-700/30 rounded">
                <span class="text-sm text-slate-300">{ip.name}</span>
                <span class="text-xs text-slate-500">{ip.integration_type or "Standard"}</span>
            </div>
            '''
        html += '</div>'
        
        return html
    except Exception as e:
        return f'<div class="text-center py-4"><span class="text-red-400 text-sm">Error loading integrations</span></div>'

@main.route("/api/agencies/<int:agency_id>/implementations")
@login_required
def agency_implementations_page(agency_id: int):
    try:
        agency = Agency.query.get_or_404(agency_id)
        agency.header_url = url_for('static', filename=f'images/transit_headers/{agency.short_name.lower().replace(" ", "_")}_header.png') if agency.short_name else None
        implementations = AgencyFunctionImplementation.query\
            .filter_by(agency_id=agency_id)\
            .join(Function).join(FunctionalArea)\
            .order_by(FunctionalArea.name, Function.name)\
            .all()
        return render_template('agency_implementations.html', agency=agency, implementations=implementations)
    except Exception as e:
        return html_error_fragment(f"Error loading implementations page: {str(e)}")

@main.route("/agencies/<int:agency_id>/implementations")
@login_required
def agency_implementations_full_page(agency_id: int):
    try:
        agency = Agency.query.get_or_404(agency_id)
        agency.header_url = url_for('static', filename=f'images/transit_headers/{agency.short_name.lower().replace(" ", "_")}_header.png') if agency.short_name else None
        implementations = AgencyFunctionImplementation.query\
            .filter_by(agency_id=agency_id)\
            .join(Function).join(FunctionalArea)\
            .order_by(FunctionalArea.name, Function.name)\
            .all()
        return render_template('agency_implementations.html', agency=agency, implementations=implementations)
    except Exception as e:
        return html_error_fragment(f"Error loading implementations page: {str(e)}")


@main.route("/api/agencies/<int:agency_id>/implementations/list")
@login_required
def agency_implementations_list(agency_id: int):
    try:
        status = request.args.get('status')
        q = AgencyFunctionImplementation.query.filter_by(agency_id=agency_id)
        if status in ('Active', 'Planned', 'Retired'):
            q = q.filter(AgencyFunctionImplementation.status == status)
        implementations = q.join(Function).join(FunctionalArea).order_by(FunctionalArea.name, Function.name).all()
        return render_template('fragments/afi_list.html', implementations=implementations)
    except Exception as e:
        return html_error_fragment(f"Error loading implementations list: {str(e)}")

@main.route("/api/agencies/<int:agency_id>/implementations", methods=["POST"])  # Create AFI (parent + optional children)
@login_required
def create_agency_implementation(agency_id: int):
    try:
        agency = Agency.query.get_or_404(agency_id)
        function_id = int(request.form.get('function_id'))
        component_id = int(request.form.get('component_id'))
        selected_child_ids = request.form.getlist('selected_child_ids[]') or request.form.getlist('selected_child_ids')
        selected_child_ids = [int(cid) for cid in selected_child_ids] if selected_child_ids else None

        function = Function.query.get_or_404(function_id)
        component = Component.query.get_or_404(component_id)

        # Collect details
        details = {
            'status': request.form.get('status') or 'Active',
            'deployment_date': (datetime.strptime(request.form.get('deployment_date'), '%Y-%m-%d').date()
                                if request.form.get('deployment_date') else None),
            'version': request.form.get('version') or None,
            'deployment_notes': request.form.get('deployment_notes') or None,
            'implementation_notes': request.form.get('implementation_notes') or None,
            'additional_metadata': None,
        }

        # If non-composite or a child is chosen, ensure compatibility
        if not component.is_composite:
            if not component_supports_function(component, function):
                return html_error_fragment("Selected component does not implement the chosen function.")
        # For composite parent, children will be validated per-child in util

        # Create AFI(s)
        create_afi_with_optional_children(
            agency=agency,
            function=function,
            component=component,
            details=details,
            selected_child_ids=selected_child_ids
        )
        db.session.commit()

        # Decide response target based on HX-Current-URL (full page vs sidebar)
        current_url = request.headers.get('HX-Current-URL', '')
        if f"/agencies/{agency.id}/implementations" in current_url:
            implementations = AgencyFunctionImplementation.query\
                .filter_by(agency_id=agency.id)\
                .join(Function).join(FunctionalArea)\
                .order_by(FunctionalArea.name, Function.name)\
                .all()
            return render_template('fragments/afi_list.html', implementations=implementations)

        # Return refreshed agency details into the right panel (legacy sidebar flow)
        agency.header_url = url_for('static', filename=f'images/transit_headers/{agency.short_name.lower().replace(" ", "_")}_header.png') if agency.short_name else None
        return render_template('fragments/agency_details.html', agency=agency)

    except IntegrityError as ie:
        db.session.rollback()
        return html_error_fragment("This implementation already exists for the agency/function/component.")
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error creating implementation: {str(e)}")


@main.route("/api/wizard/afi/step1")
@login_required
def wizard_afi_step1():
    try:
        agency_id = int(request.args.get('agency_id'))
        component_id = request.args.get('component_id')
        agency = Agency.query.get_or_404(agency_id)
        functional_areas = FunctionalArea.query.order_by(FunctionalArea.name).all()
        preselected_component = Component.query.get(int(component_id)) if component_id else None
        return render_template('fragments/wizard_afi_step1.html',
                               agency=agency,
                               functional_areas=functional_areas,
                               preselected_component=preselected_component)
    except Exception as e:
        return html_error_fragment(f"Error loading wizard: {str(e)}")


@main.route("/api/wizard/afi/step2")
@login_required
def wizard_afi_step2():
    try:
        agency_id = int(request.args.get('agency_id'))
        function_id = int(request.args.get('function_id'))
        search = (request.args.get('component_search') or '').strip()
        vendor_id = request.args.get('vendor_id')
        preselected_component_id = request.args.get('component_id')

        agency = Agency.query.get_or_404(agency_id)
        function = Function.query.get_or_404(function_id)

        # Components that directly implement the function
        direct_components = db.session.query(Component).join(Component.functions)\
            .filter(Function.id == function_id)
        
        # Optional filters
        if vendor_id:
            try:
                vid = int(vendor_id)
                direct_components = direct_components.filter(Component.vendor_id == vid)
            except ValueError:
                pass
        if search:
            direct_components = direct_components.filter(Component.name.ilike(f"%{search}%"))
        direct_components = direct_components.distinct().order_by(Component.name).all()

        # Composite parents with children that implement the function
        # Strategy: find children implementing the function, collect their parents
        children_q = db.session.query(Component).join(Component.functions)\
            .filter(Function.id == function_id, Component.parent_component_id.isnot(None))
        if vendor_id:
            try:
                vid = int(vendor_id)
                children_q = children_q.filter(Component.vendor_id == vid)
            except ValueError:
                pass
        if search:
            children_q = children_q.filter(Component.name.ilike(f"%{search}%"))
        child_components = children_q.all()
        parents_map = {}
        for child in child_components:
            parent = child.parent_component
            if not parent:
                continue
            parents_map.setdefault(parent.id, {'parent': parent, 'children': []})
            if child not in parents_map[parent.id]['children']:
                parents_map[parent.id]['children'].append(child)
        composite_parents = list(parents_map.values())

        preselected_component = Component.query.get(int(preselected_component_id)) if preselected_component_id else None

        return render_template('fragments/wizard_afi_step2_components.html',
                               agency=agency,
                               function=function,
                               direct_components=direct_components,
                               composite_parents=composite_parents,
                               preselected_component=preselected_component)
    except Exception as e:
        return html_error_fragment(f"Error loading components: {str(e)}")


@main.route("/api/wizard/afi/step3")
@login_required
def wizard_afi_step3():
    try:
        agency_id = int(request.args.get('agency_id'))
        function_id = int(request.args.get('function_id'))
        component_id = int(request.args.get('component_id'))
        selected_child_ids = request.args.getlist('selected_child_ids') or request.args.getlist('selected_child_ids[]')
        
        agency = Agency.query.get_or_404(agency_id)
        function = Function.query.get_or_404(function_id)
        component = Component.query.get_or_404(component_id)
        selected_children = []
        if selected_child_ids:
            child_ids_int = [int(cid) for cid in selected_child_ids]
            selected_children = Component.query.filter(Component.id.in_(child_ids_int)).all()
        return render_template('fragments/wizard_afi_step3_details.html',
                               agency=agency,
                               function=function,
                               component=component,
                               selected_children=selected_children)
    except Exception as e:
        return html_error_fragment(f"Error loading details: {str(e)}")


@main.route("/api/wizard/afi/step4")
@login_required
def wizard_afi_step4():
    try:
        # Pass-through all params to final review
        agency_id = int(request.args.get('agency_id'))
        function_id = int(request.args.get('function_id'))
        component_id = int(request.args.get('component_id'))
        selected_child_ids = request.args.getlist('selected_child_ids') or request.args.getlist('selected_child_ids[]')
        status = request.args.get('status') or 'Active'
        deployment_date = request.args.get('deployment_date') or ''
        version = request.args.get('version') or ''
        deployment_notes = request.args.get('deployment_notes') or ''
        implementation_notes = request.args.get('implementation_notes') or ''

        agency = Agency.query.get_or_404(agency_id)
        function = Function.query.get_or_404(function_id)
        component = Component.query.get_or_404(component_id)
        selected_children = []
        if selected_child_ids:
            child_ids_int = [int(cid) for cid in selected_child_ids]
            selected_children = Component.query.filter(Component.id.in_(child_ids_int)).all()

        return render_template('fragments/wizard_afi_step4_review.html',
                               agency=agency,
                               function=function,
                               component=component,
                               selected_children=selected_children,
                               status=status,
                               deployment_date=deployment_date,
                               version=version,
                               deployment_notes=deployment_notes,
                               implementation_notes= implementation_notes)
    except Exception as e:
        return html_error_fragment(f"Error loading review: {str(e)}")


@main.route("/api/components/<int:component_id>/children")
@login_required
def component_children_for_function(component_id):
    try:
        function_id = int(request.args.get('function_id'))
        function = Function.query.get_or_404(function_id)
        component = Component.query.get_or_404(component_id)
        children = component.child_components or []
        html = ''
        for child in children:
            supports = component_supports_function(child, function)
            disabled_attr = '' if supports else 'disabled'
            note = '' if supports else '<span class="text-xs text-slate-500 ml-1">(does not implement)</span>'
            html += f'<label class="flex items-center space-x-2 py-1"><input type="checkbox" name="selected_child_ids" value="{child.id}" {disabled_attr} class="accent-blue-500"/><span class="text-sm text-slate-200">{child.name}</span>{note}</label>'
        if not html:
            html = '<div class="text-sm text-slate-400">No subcomponents</div>'
        return html
    except Exception as e:
        return html_error_fragment(f"Error loading children: {str(e)}")

@main.route('/api/options/functions')
@login_required
def options_functions():
    try:
        fa_id = request.args.get('functional_area_id') or request.args.get('fa_id')
        if not fa_id:
            return '<option value="">Select a function</option>'
        fid = int(fa_id)
        functions = Function.query.filter_by(functional_area_id=fid).order_by(Function.name).all()
        html = '<option value="">Select a function</option>'
        for f in functions:
            html += f'<option value="{f.id}">{f.name}</option>'
        return html
    except Exception:
        return '<option value="">Select a function</option>'

@main.route('/api/implementations/<int:impl_id>/edit')
@login_required
def afi_edit_form(impl_id: int):
    try:
        impl = AgencyFunctionImplementation.query.get_or_404(impl_id)
        # Load functions list for select (by FA of current function to keep concise)
        functional_areas = FunctionalArea.query.order_by(FunctionalArea.name).all()
        functions = Function.query.order_by(Function.name).all()
        return render_template('fragments/afi_edit_form.html', impl=impl, functions=functions, functional_areas=functional_areas)
    except Exception as e:
        return html_error_fragment(f"Error loading edit form: {str(e)}")


@main.route('/api/implementations/<int:impl_id>', methods=['POST'])
@login_required
def afi_update(impl_id: int):
    try:
        impl = AgencyFunctionImplementation.query.get_or_404(impl_id)
        old = {
                       'function_id': impl.function_id,
            'status': impl.status,
            'version': impl.version,
            'deployment_date': impl.deployment_date.isoformat() if impl.deployment_date else None,
            'deployment_notes': impl.deployment_notes,
            'implementation_notes': impl.implementation_notes,
        }
        # Optional function change
        function_id = request.form.get('function_id')
        if function_id:
            new_function_id = int(function_id)
            # Only validate and update if the function actually changed
            if new_function_id != impl.function_id:
                new_function = Function.query.get(new_function_id)
                if not new_function:
                    return html_error_fragment('Invalid function selected')
                # Validate compatibility for non-parent, non-composite component
                is_parent = bool(impl.child_afis)
                if (not is_parent) and (not impl.component.is_composite) and (not component_supports_function(impl.component, new_function)):
                    return html_error_fragment('Component does not implement the selected function')
                impl.function_id = new_function.id
        # Other fields
        impl.status = request.form.get('status') or impl.status
        dd = request.form.get('deployment_date')
        impl.deployment_date = datetime.strptime(dd, '%Y-%m-%d').date() if dd else None
        impl.version = request.form.get('version') or None
        impl.deployment_notes = request.form.get('deployment_notes') or None
        impl.implementation_notes = request.form.get('implementation_notes') or None

        db.session.flush()
        new = {
            'function_id': impl.function_id,
            'status': impl.status,
            'version': impl.version,
            'deployment_date': impl.deployment_date.isoformat() if impl.deployment_date else None,
            'deployment_notes': impl.deployment_notes,
            'implementation_notes': impl.implementation_notes,
        }
        action = 'function_changed' if old['function_id'] != new['function_id'] else 'updated'
        record_afi_history(impl, action, old_values=old, new_values=new)
        db.session.commit()
        # Return updated row
        return render_template('fragments/afi_row.html', impl=impl)
    except IntegrityError:
        db.session.rollback()
        return html_error_fragment('Update violates uniqueness or constraints')
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error updating implementation: {str(e)}")


@main.route('/api/implementations/<int:impl_id>/status', methods=['POST'])
@login_required
def afi_update_status(impl_id: int):
    try:
        impl = AgencyFunctionImplementation.query.get_or_404(impl_id)
        old_status = impl.status
        new_status = request.form.get('status')
        if new_status not in ('Active', 'Planned', 'Retired'):
            return html_error_fragment('Invalid status')
        impl.status = new_status
        db.session.flush()
        record_afi_history(impl, 'status_change', old_values={'status': old_status}, new_values={'status': new_status})
        db.session.commit()
        return render_template('fragments/afi_row.html', impl=impl)
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error updating status: {str(e)}")


@main.route('/api/implementations/<int:impl_id>', methods=['DELETE'])
@login_required
def afi_delete(impl_id: int):
    try:
        impl = AgencyFunctionImplementation.query.get_or_404(impl_id)
        old = {
            'agency_id': impl.agency_id,
            'function_id': impl.function_id,
            'component_id': impl.component_id,
            'status': impl.status,
            'version': impl.version,
        }
        afi_id_for_history = impl.id
        db.session.delete(impl)
        db.session.flush()
        # Create a manual history row after delete
        from app.models.tran import AgencyFunctionImplementationHistory
        hist = AgencyFunctionImplementationHistory(
            afi_id=afi_id_for_history,
            action='deleted',
            changed_by=get_updated_by(),
            old_values=old,
            new_values=None,
        )
        db.session.add(hist)
        db.session.commit()
        return ''  # Let HTMX remove the row via hx-swap=outerHTML
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error deleting implementation: {str(e)}")


@main.route('/api/implementations/<int:parent_id>/child/<int:child_id>', methods=['DELETE'])
@login_required
def afi_remove_child(parent_id: int, child_id: int):
    try:
        # Ensure parent exists
        parent = AgencyFunctionImplementation.query.get_or_404(parent_id)
        # Ensure child belongs to parent
        child = AgencyFunctionImplementation.query.get_or_404(child_id)
        if child.parent_afi_id != parent.id:
            return html_error_fragment('Child does not belong to this composite')
        # Remove child
        from app.utils.afi import remove_child_afi
        ok = remove_child_afi(child_id)
        if not ok:
            db.session.rollback()
            return html_error_fragment('Unable to remove child implementation')
        db.session.commit()
        # Return refreshed parent row or agency details; choose parent row refresh
        parent = AgencyFunctionImplementation.query.get(parent_id)
        return render_template('fragments/afi_row.html', impl=parent)
    except Exception as e:
        db.session.rollback()
        return html_error_fragment(f"Error removing subcomponent: {str(e)}")


@main.route('/api/implementations/<int:impl_id>/history')
@login_required
def afi_history(impl_id: int):
    try:
        impl = AgencyFunctionImplementation.query.get_or_404(impl_id)
        entries = impl.history_entries
        # Sort newest first
        entries = sorted(entries, key=lambda h: h.timestamp or datetime.min, reverse=True)
        return render_template('fragments/afi_history.html', impl=impl, entries=entries)
    except Exception as e:
        return html_error_fragment(f"Error loading history: {str(e)}")

@main.route('/api/implementations/<int:impl_id>/row')
@login_required
def afi_row(impl_id: int):
    try:
        impl = AgencyFunctionImplementation.query.get_or_404(impl_id)
        return render_template('fragments/afi_row.html', impl=impl)
    except Exception as e:
        return html_error_fragment(f"Error loading implementation row: {str(e)}")

# Components CRUD Endpoints
@main.route("/api/components/form")
@login_required
def component_form():
    try:
        form = ComponentForm()
        vendors = Vendor.query.order_by(Vendor.name).all()
        return render_template('fragments/component_form.html', form=form, component=None, vendors=vendors)
    except Exception as e:
        return html_error_fragment(f"Error loading component form: {str(e)}")

@main.route("/api/components/<int:component_id>/form")
@login_required
def component_edit_form(component_id):
    try:
        component = Component.query.get_or_404(component_id)
        form = ComponentForm()
        form.populate_from_component(component)
        vendors = Vendor.query.order_by(Vendor.name).all()
        return render_template('fragments/component_form.html', form=form, component=component, vendors=vendors)
    except Exception as e:
        return html_error_fragment(f"Error loading component edit form: {str(e)}")

@main.route('/api/components', methods=['POST'])
@login_required
def create_component():
    try:
        form = ComponentForm()
        if form.validate_on_submit():
            existing = Component.query.filter_by(name=form.name.data).first()
            if existing:
                return json_error_response(f"Component '{form.name.data}' already exists")
            component = Component()
            form.populate_component(component)
            db.session.add(component)
            db.session.commit()
            return json_success_response(f"Component '{component.name}' created successfully")
        else:
            return json_form_error_response(form)
    except Exception as e:
        db.session.rollback()
        return json_error_response(f"Error creating component: {str(e)}")

@main.route('/api/components/<int:component_id>', methods=['POST'])
@login_required
def update_component(component_id):
    try:
        component = Component.query.get_or_404(component_id)
        form = ComponentForm()
        if form.validate_on_submit():
            existing = Component.query.filter(Component.name == form.name.data, Component.id != component_id).first()
            if existing:
                return json_error_response(f"Component '{form.name.data}' already exists")
            form.populate_component(component)
            db.session.commit()
            return json_success_response(f"Component '{component.name}' updated successfully")
        else:
            return json_form_error_response(form)
    except Exception as e:
        db.session.rollback()
        return json_error_response(f"Error updating component: {str(e)}")

@main.route('/api/components/<int:component_id>', methods=['DELETE'])
@login_required
def delete_component(component_id):
    try:
        component = Component.query.get_or_404(component_id)
        name = component.name
        # Prevent delete if used in AFIs
        usage_count = AgencyFunctionImplementation.query.filter_by(component_id=component_id).count()
        if usage_count > 0:
            return json_error_response(f"Cannot delete component '{name}' because it is used in {usage_count} implementations.")
        db.session.delete(component)
        db.session.commit()
        return json_success_response(f"Component '{name}' deleted successfully")
    except Exception as e:
        db.session.rollback()
        return json_error_response(f"Error deleting component: {str(e)}")
