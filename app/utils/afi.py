# app/utils/afi.py
from typing import List, Optional
from datetime import datetime
from flask import current_app
from app import db
from app.models.tran import Agency, Function, Component, AgencyFunctionImplementation, AgencyFunctionImplementationHistory
from app.auth import get_updated_by


def component_supports_function(component: Component, function: Function) -> bool:
    """Return True if the component directly implements the function via m2m mapping."""
    return any(func.id == function.id for func in component.functions)


def get_children_supporting_function(component: Component, function: Function) -> List[Component]:
    return [child for child in component.child_components or [] if component_supports_function(child, function)]


def record_afi_history(afi: AgencyFunctionImplementation, action: str, old_values: Optional[dict] = None, new_values: Optional[dict] = None):
    entry = AgencyFunctionImplementationHistory(
        afi_id=afi.id,
        timestamp=datetime.utcnow(),
        action=action,
        changed_by=get_updated_by(),
        old_values=old_values,
        new_values=new_values,
    )
    db.session.add(entry)


def create_afi_with_optional_children(*, agency: Agency, function: Function, component: Component, details: dict, selected_child_ids: Optional[List[int]] = None) -> AgencyFunctionImplementation:
    """
    Create a parent AFI for the given component and agency/function. If selected_child_ids is provided,
    create child AFIs for those child components, linked via parent_afi_id. If the parent does not
    directly implement the function, we still allow the umbrella AFI per product decision.
    """
    parent_afi = AgencyFunctionImplementation(
        agency_id=agency.id,
        function_id=function.id,
        component_id=component.id,
        deployment_date=details.get('deployment_date'),
        version=details.get('version'),
        deployment_notes=details.get('deployment_notes'),
        status=details.get('status') or 'Active',
        implementation_notes=details.get('implementation_notes'),
        additional_metadata=details.get('additional_metadata'),
    )
    db.session.add(parent_afi)
    db.session.flush()  # to get id for history and child linkage
    record_afi_history(parent_afi, 'created', old_values=None, new_values={
        'agency_id': parent_afi.agency_id,
        'function_id': parent_afi.function_id,
        'component_id': parent_afi.component_id,
        'status': parent_afi.status,
        'version': parent_afi.version,
        'deployment_date': str(parent_afi.deployment_date) if parent_afi.deployment_date else None,
    })

    # Child creation
    if selected_child_ids:
        children = {c.id: c for c in (component.child_components or [])}
        for cid in selected_child_ids:
            child = children.get(cid)
            if not child:
                continue
            # Only create child AFI if it supports the function
            if not component_supports_function(child, function):
                continue
            child_afi = AgencyFunctionImplementation(
                agency_id=agency.id,
                function_id=function.id,
                component_id=child.id,
                parent_afi_id=parent_afi.id,
                deployment_date=details.get('deployment_date'),
                version=details.get('version'),
                deployment_notes=details.get('deployment_notes'),
                status=details.get('status') or 'Active',
                implementation_notes=details.get('implementation_notes'),
                additional_metadata=details.get('additional_metadata'),
            )
            db.session.add(child_afi)
            db.session.flush()
            record_afi_history(child_afi, 'created', old_values=None, new_values={
                'agency_id': child_afi.agency_id,
                'function_id': child_afi.function_id,
                'component_id': child_afi.component_id,
                'parent_afi_id': parent_afi.id,
                'status': child_afi.status,
                'version': child_afi.version,
            })
    return parent_afi


def remove_child_afi(child_afi_id: int) -> bool:
    afi = AgencyFunctionImplementation.query.get(child_afi_id)
    if not afi:
        return False
    old = {
        'agency_id': afi.agency_id,
        'function_id': afi.function_id,
        'component_id': afi.component_id,
        'parent_afi_id': afi.parent_afi_id,
        'status': afi.status,
        'version': afi.version,
    }
    db.session.delete(afi)
    db.session.flush()
    # Log against the deleted AFI id
    hist = AgencyFunctionImplementationHistory(
        afi_id=child_afi_id,
        timestamp=datetime.utcnow(),
        action='deleted',
        changed_by=get_updated_by(),
        old_values=old,
        new_values=None,
    )
    db.session.add(hist)
    return True
