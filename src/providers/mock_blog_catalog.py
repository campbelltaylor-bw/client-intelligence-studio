import csv

from src.providers.base import BlogCatalogProvider


class MockBlogCatalogProvider(BlogCatalogProvider):
    def __init__(self, data_path: str = "data/blog_catalog.csv"):
        self._path = data_path

    def load(self) -> list[dict]:
        rows = []
        with open(self._path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows
