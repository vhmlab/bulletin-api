"""Router package for boletin service.

This package exposes routers used by the application so imports in `app.main`
remain unchanged when moving from a single `routers.py` file to a package.
"""
from .sabbath_school import sabbath_school_router
from .worship_service import worship_service_router
from .youth_service import youth_service_router
from .wednesday_service import wednesday_service_router
from .forms import forms_router
from .templates import templates_router

__all__ = [
    "sabbath_school_router",
    "worship_service_router",
    "youth_service_router",
    "wednesday_service_router",
    "forms_router",
    "templates_router",
]
