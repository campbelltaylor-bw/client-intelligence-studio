import pandas as pd

from src.providers.base import BlogCatalogProvider


class CSVBlogCatalogProvider(BlogCatalogProvider):
    def __init__(self, data_path: str = "data/blog_catalog.csv"):
        self._path = data_path

    def load(self) -> list[dict]:
        df = pd.read_csv(self._path)
        return df.to_dict(orient="records")
