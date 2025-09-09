# app/routes/configurations.py
from flask import Blueprint, render_template, request, jsonify
from app import db
from app.auth import login_required, get_updated_by
from app.models.tran import (
    Configuration, ConfigurationHistory, ConfigurationProduct,
    Product, ProductVersion, Agency, Function, Component
)
from app.forms.forms import (
    ConfigurationForm, ConfigurationProductForm, ProductForm, ProductVersionForm
)
from datetime import datetime

config_bp = Blueprint('configurations', __name__)

# --------- Helper / Advisory Stub ---------

def advisory_validate(configuration: Configuration, products):
    """Return non-blocking advisory warning dicts (stub)."""
    warnings = []
    # Placeholder examples
    # warnings.append({"code": "EOL_VERSION", "message": "One product version near end-of-life."})
    return warnings

# Helper: parse product_ids from args or form (supports repeated params and comma-separated)
def _parse_product_ids(arg_source) -> list[int]:
    ids: list[int] = []
    if hasattr(arg_source, 'getlist'):
        raw_list = arg_source.getlist('product_ids')
    else:
        raw_list = []
    # Also support comma-separated single value
    raw_single = arg_source.get('product_ids') if hasattr(arg_source, 'get') else None
    if raw_single and isinstance(raw_single, str) and ',' in raw_single:
        raw_list.extend(raw_single.split(','))
    elif raw_single and not raw_list:
        raw_list.append(raw_single)
    # Normalize & dedupe
    for pid in raw_list:
        try:
            pid_int = int(str(pid).strip())
            ids.append(pid_int)
        except (TypeError, ValueError):
            continue
    # unique preserve order
    seen = set()
    result = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            result.append(i)
    return result

# --------- Pages ---------

@config_bp.route('/configurations')
@login_required
def configurations_page():
    agencies = Agency.query.order_by(Agency.name.asc()).all()
    functions = Function.query.order_by(Function.name.asc()).all()
    return render_template('configurations.html', agencies=agencies, functions=functions, selected_agency_id=None)

@config_bp.route('/agencies/<int:agency_id>/configurations')
@login_required
def agency_configurations_page(agency_id):
    agency = Agency.query.get_or_404(agency_id)
    agencies = Agency.query.order_by(Agency.name.asc()).all()
    functions = Function.query.order_by(Function.name.asc()).all()
    return render_template('configurations.html', agency=agency, agencies=agencies, functions=functions, selected_agency_id=agency.id)

# --------- Configuration API ---------

@config_bp.route('/api/configurations/list')
@login_required
def configurations_list():
    agency_id = request.args.get('agency_id', type=int)
    function_id = request.args.get('function_id', type=int)
    status = (request.args.get('status') or '').strip()
    q = Configuration.query
    if agency_id:
        q = q.filter(Configuration.agency_id == agency_id)
    if function_id:
        q = q.filter(Configuration.function_id == function_id)
    if status:
        q = q.filter(Configuration.status == status)
    configs = q.order_by(Configuration.created_at.desc()).limit(250).all()
    return render_template('fragments/configuration_list.html', configurations=configs)

@config_bp.route('/api/configurations/<int:config_id>/row')
@login_required
def configuration_row(config_id):
    c = Configuration.query.get_or_404(config_id)
    return render_template('fragments/configuration_row.html', c=c)

@config_bp.route('/api/configurations/<int:config_id>/details')
@login_required
def configuration_details(config_id):
    c = Configuration.query.get_or_404(config_id)
    warnings = advisory_validate(c, [cp.product for cp in c.products])
    return render_template('fragments/configuration_details.html', c=c, warnings=warnings)

@config_bp.route('/api/configurations', methods=['POST'])
@login_required
def configuration_create():
    form = ConfigurationForm()
    if form.validate_on_submit():
        c = Configuration()
        form.populate_configuration(c)
        db.session.add(c)
        db.session.flush()
        hist = ConfigurationHistory(configuration_id=c.id, action='created', changed_by=get_updated_by(), new_values={})
        db.session.add(hist)
        db.session.commit()
        return render_template('fragments/configuration_row.html', c=c), 201
    return jsonify({'error': 'validation', 'messages': form.errors}), 400

@config_bp.route('/api/configurations/<int:config_id>', methods=['POST'])
@login_required
def configuration_update(config_id):
    c = Configuration.query.get_or_404(config_id)
    form = ConfigurationForm()
    if form.validate_on_submit():
        old = { 'status': c.status, 'version_label': c.version_label }
        form.populate_configuration(c)
        hist = ConfigurationHistory(configuration_id=c.id, action='updated', changed_by=get_updated_by(), old_values=old, new_values={'status': c.status, 'version_label': c.version_label})
        db.session.add(hist)
        db.session.commit()
        return render_template('fragments/configuration_row.html', c=c)
    return jsonify({'error': 'validation', 'messages': form.errors}), 400

@config_bp.route('/api/configurations/<int:config_id>', methods=['DELETE'])
@login_required
def configuration_delete(config_id):
    c = Configuration.query.get_or_404(config_id)
    hist = ConfigurationHistory(configuration_id=c.id, action='deleted', changed_by=get_updated_by(), old_values={'id': c.id})
    db.session.add(hist)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'status': 'deleted', 'id': config_id})

@config_bp.route('/api/configurations/<int:config_id>/history')
@login_required
def configuration_history(config_id):
    c = Configuration.query.get_or_404(config_id)
    history = ConfigurationHistory.query.filter_by(configuration_id=config_id).order_by(ConfigurationHistory.timestamp.desc()).all()
    return render_template('fragments/configuration_history.html', c=c, history=history)

# --------- ConfigurationProduct API ---------

@config_bp.route('/api/configurations/<int:config_id>/products/list')
@login_required
def configuration_products_list(config_id):
    c = Configuration.query.get_or_404(config_id)
    return render_template('fragments/configuration_products_list.html', c=c, products=c.products)

@config_bp.route('/api/configurations/<int:config_id>/products/form')
@login_required
def configuration_product_form(config_id):
    c = Configuration.query.get_or_404(config_id)
    form = ConfigurationProductForm()
    form.configuration_id.data = str(c.id)
    return render_template('fragments/configuration_product_form.html', form=form, configuration=c)

@config_bp.route('/api/configurations/<int:config_id>/products', methods=['POST'])
@login_required
def configuration_product_create(config_id):
    c = Configuration.query.get_or_404(config_id)
    form = ConfigurationProductForm()
    if form.validate_on_submit():
        cp = ConfigurationProduct()
        form.populate_configuration_product(cp)
        cp.configuration_id = c.id
        db.session.add(cp)
        db.session.flush()
        hist = ConfigurationHistory(configuration_id=c.id, action='product_added', changed_by=get_updated_by(), new_values={'configuration_product_id': cp.id})
        db.session.add(hist)
        db.session.commit()
        return render_template('fragments/configuration_products_list.html', c=c, products=c.products)
    return jsonify({'error': 'validation', 'messages': form.errors}), 400

@config_bp.route('/api/configuration-products/<int:cp_id>', methods=['POST'])
@login_required
def configuration_product_update(cp_id):
    cp = ConfigurationProduct.query.get_or_404(cp_id)
    form = ConfigurationProductForm()
    if form.validate_on_submit():
        old = {'status': cp.status}
        form.populate_configuration_product(cp)
        hist = ConfigurationHistory(configuration_id=cp.configuration_id, action='product_updated', changed_by=get_updated_by(), old_values=old, new_values={'status': cp.status})
        db.session.add(hist)
        db.session.commit()
        configuration = Configuration.query.get(cp.configuration_id)
        return render_template('fragments/configuration_products_list.html', c=configuration, products=configuration.products)
    return jsonify({'error': 'validation', 'messages': form.errors}), 400

@config_bp.route('/api/configuration-products/<int:cp_id>', methods=['DELETE'])
@login_required
def configuration_product_delete(cp_id):
    cp = ConfigurationProduct.query.get_or_404(cp_id)
    configuration_id = cp.configuration_id
    hist = ConfigurationHistory(configuration_id=configuration_id, action='product_removed', changed_by=get_updated_by(), old_values={'configuration_product_id': cp.id})
    db.session.add(hist)
    db.session.delete(cp)
    db.session.commit()
    configuration = Configuration.query.get(configuration_id)
    return render_template('fragments/configuration_products_list.html', c=configuration, products=configuration.products)

# --------- Product & Versions API ---------

@config_bp.route('/products')
@login_required
def products_page():
    return render_template('products.html')

@config_bp.route('/api/products/list')
@login_required
def products_list():
    vendor_id = request.args.get('vendor_id', type=int)
    q = Product.query
    if vendor_id:
        q = q.filter(Product.vendor_id == vendor_id)
    products = q.order_by(Product.name.asc()).limit(250).all()
    return render_template('fragments/product_list.html', products=products)

@config_bp.route('/api/products/<int:product_id>/details')
@login_required
def product_details(product_id):
    p = Product.query.get_or_404(product_id)
    versions = ProductVersion.query.filter_by(product_id=product_id).order_by(ProductVersion.release_date.desc().nullslast()).all()
    return render_template('fragments/product_details.html', p=p, versions=versions)

@config_bp.route('/api/products/form')
@login_required
def product_form():
    form = ProductForm()
    return render_template('fragments/product_form.html', form=form)

@config_bp.route('/api/products', methods=['POST'])
@login_required
def product_create():
    form = ProductForm()
    if form.validate_on_submit():
        p = Product()
        form.populate_product(p)
        db.session.add(p)
        db.session.commit()
        return render_template('fragments/product_list.html', products=Product.query.order_by(Product.name.asc()).all()), 201
    return jsonify({'error': 'validation', 'messages': form.errors}), 400

@config_bp.route('/api/products/<int:product_id>/versions/list')
@login_required
def product_versions_list(product_id):
    p = Product.query.get_or_404(product_id)
    versions = ProductVersion.query.filter_by(product_id=product_id).order_by(ProductVersion.release_date.desc().nullslast()).all()
    return render_template('fragments/product_versions_list.html', p=p, versions=versions)

@config_bp.route('/api/products/<int:product_id>/versions/form')
@login_required
def product_version_form(product_id):
    p = Product.query.get_or_404(product_id)
    form = ProductVersionForm()
    form.product_id.data = str(p.id)
    return render_template('fragments/product_version_form.html', form=form, product=p)

@config_bp.route('/api/products/<int:product_id>/versions', methods=['POST'])
@login_required
def product_version_create(product_id):
    p = Product.query.get_or_404(product_id)
    form = ProductVersionForm()
    if form.validate_on_submit():
        pv = ProductVersion()
        form.populate_version(pv)
        pv.product_id = p.id
        db.session.add(pv)
        db.session.commit()
        versions = ProductVersion.query.filter_by(product_id=product_id).order_by(ProductVersion.release_date.desc().nullslast()).all()
        return render_template('fragments/product_versions_list.html', p=p, versions=versions), 201
    return jsonify({'error': 'validation', 'messages': form.errors}), 400

# --------- Wizard (Config) ---------

@config_bp.route('/api/wizard/config/step1')
@login_required
def wizard_config_step1():
    agencies = Agency.query.order_by(Agency.name.asc()).all()
    functions = Function.query.order_by(Function.name.asc()).all()
    return render_template('fragments/wizard_config_step1.html', agencies=agencies, functions=functions)

@config_bp.route('/api/wizard/config/step2')
@login_required
def wizard_config_step2():
    agency_id = request.args.get('agency_id', type=int)
    function_id = request.args.get('function_id', type=int)
    components = []
    if function_id:
        func = Function.query.get(function_id)
        if func:
            components = sorted(func.components, key=lambda c: c.name.lower())
    if not components:
        components = Component.query.order_by(Component.name.asc()).all()
    return render_template('fragments/wizard_config_step2.html', components=components, agency_id=agency_id, function_id=function_id)

@config_bp.route('/api/wizard/config/step3')
@login_required
def wizard_config_step3():
    agency_id = request.args.get('agency_id', type=int)
    function_id = request.args.get('function_id', type=int)
    component_id = request.args.get('component_id', type=int)
    products = Product.query.order_by(Product.name.asc()).all()
    return render_template('fragments/wizard_config_step3.html', products=products, agency_id=agency_id, function_id=function_id, component_id=component_id)

@config_bp.route('/api/wizard/config/step4')
@login_required
def wizard_config_step4():
    agency_id = request.args.get('agency_id', type=int)
    function_id = request.args.get('function_id', type=int)
    component_id = request.args.get('component_id', type=int)
    # selected products list (supports repeated params or comma-separated ids)
    ids = _parse_product_ids(request.args)
    selected_products = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    fake_config = Configuration(agency_id=agency_id, function_id=function_id, component_id=component_id, status='Draft')
    warnings = advisory_validate(fake_config, selected_products)
    return render_template('fragments/wizard_config_step4.html', agency_id=agency_id, function_id=function_id, component_id=component_id, products=selected_products, product_ids=ids, warnings=warnings)

@config_bp.route('/api/wizard/config/confirm', methods=['POST'])
@login_required
def wizard_config_confirm():
    try:
        # Create configuration
        form = ConfigurationForm()
        if not form.validate_on_submit():
            return jsonify({'error': 'validation', 'messages': form.errors}), 400
        c = Configuration()
        form.populate_configuration(c)
        db.session.add(c)
        db.session.flush()
        db.session.add(ConfigurationHistory(configuration_id=c.id, action='created', changed_by=get_updated_by(), new_values={}))
        # Attach products if provided
        ids = _parse_product_ids(request.form)
        for pid in ids:
            cp = ConfigurationProduct(configuration_id=c.id, product_id=pid, status='Active')
            db.session.add(cp)
            db.session.flush()
            db.session.add(ConfigurationHistory(configuration_id=c.id, action='product_added', changed_by=get_updated_by(), new_values={'configuration_product_id': cp.id}))
        db.session.commit()
        return render_template('fragments/configuration_row.html', c=c), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'server', 'message': str(e)}), 500
