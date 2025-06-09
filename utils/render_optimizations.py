from collections import OrderedDict
import time

class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

# Placeholder RenderBuffer if not already defined
class RenderBuffer:
    def __init__(self, max_rows):
        self.rows = {}
        self.max_rows = max_rows

    def update_row(self, row_id, data):
        self.rows[row_id] = data

    def get_all_rows(self):
        return list(self.rows.values())

# VisualRenderer init only
class VisualRenderer:
    def __init__(self, max_rows=1000, refresh_rate_ms=60):
        self.buffer_a = RenderBuffer(max_rows)
        self.buffer_b = RenderBuffer(max_rows)
        self.display_buffer = self.buffer_a
        self.staging_buffer = self.buffer_b
        self.refresh_rate_ms = refresh_rate_ms
        self.last_render_time = 0
        self.dirty_rows = set()
        self.row_hashes = {}  # Ensure hash tracking map is initialized
        self.render_cache = LRUCache(1000)
