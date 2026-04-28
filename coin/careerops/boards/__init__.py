"""Public job-board API scrapers (Greenhouse, Lever, Ashby).

Pattern adapted from santifer/career-ops scan.mjs (MIT).
"""
from careerops.boards.base import BoardScraper
from careerops.boards.greenhouse import GreenhouseBoard
from careerops.boards.lever import LeverBoard
from careerops.boards.ashby import AshbyBoard

ALL_BOARDS = [GreenhouseBoard, LeverBoard, AshbyBoard]

__all__ = ["BoardScraper", "GreenhouseBoard", "LeverBoard", "AshbyBoard", "ALL_BOARDS"]
