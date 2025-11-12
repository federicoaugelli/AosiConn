import os

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

description="""
[Dashboard](/dashboard)
"""

def get_openapi_configuration(aosicoa: FastAPI):
    
    def custom_openapi():
        if aosicoa.openapi_schema:
            return aosicoa.openapi_schema
        
        openapi_schema = get_openapi(
            title="AosiConn",
            version="alpha 0.1.0",
            description=description,
            routes=aosicoa.routes,
            #swagger_ui_parameters=swagger_ui_parameters
        )

        openapi_schema["info"]["x-logo"] = {
            "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
        }

        # hide path that contains "internal" in the path
        openapi_schema["paths"] = {
            path: path_schema
            for path, path_schema in openapi_schema["paths"].items()
            if "internal" not in path
        }

        aosicoa.openapi_schema = openapi_schema
        return aosicoa.openapi_schema

    return custom_openapi


def get_swagger_ui_parameters():
    return {
        "syntaxHighlight.theme": "nord",
    }
