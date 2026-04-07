from hyper.layouts.base import BaseLayout


class DocsCatchAllPage(BaseLayout):
    def get(self, request, path, **params):
        parts = [part for part in path.split("/") if part]
        return {
            "raw_path": path,
            "parts": parts,
        }
