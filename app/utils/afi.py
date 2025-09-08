# app/utils/afi.py
"""Deprecated AFI utilities retained temporarily for backward import compatibility.
Phase 6: All functionality replaced by Configuration & related helpers.
Each function now raises a RuntimeError directing callers to update.
"""
from typing import List, Optional
from datetime import datetime
from app import db
# Minimal imports to avoid runtime errors if accidentally used
from app.models.tran import Agency, Function, Component  # noqa: F401

_DEPRECATION_MSG = "AFI utilities removed. Use Configuration endpoints (/api/configurations/*) and new helpers instead."

def component_supports_function(component: Component, function: Function) -> bool:  # type: ignore
    raise RuntimeError(_DEPRECATION_MSG)

def get_children_supporting_function(component: Component, function: Function):  # type: ignore
    raise RuntimeError(_DEPRECATION_MSG)

def record_afi_history(*args, **kwargs):  # type: ignore
    raise RuntimeError(_DEPRECATION_MSG)

def create_afi_with_optional_children(*args, **kwargs):  # type: ignore
    raise RuntimeError(_DEPRECATION_MSG)

def remove_child_afi(*args, **kwargs):  # type: ignore
    raise RuntimeError(_DEPRECATION_MSG)
