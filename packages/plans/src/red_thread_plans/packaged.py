"""The files the plans package ships: the outline of section headings a plan holds."""

from red_thread_core.packaged import load_asset

from red_thread_plans.domain import Outline

PLANS_PACKAGE = 'red_thread_plans'
OUTLINE_FILE = 'outline.yaml'


def load_outline() -> Outline:
    return load_asset(PLANS_PACKAGE, OUTLINE_FILE, Outline)
