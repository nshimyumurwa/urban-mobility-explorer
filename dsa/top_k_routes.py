class RouteMetrics:
    """Structure to hold individual route metrics."""
    def __init__(self, pickup_id, dropoff_id, trip_count):
        self.pickup_id = pickup_id
        self.dropoff_id = dropoff_id
        self.trip_count = trip_count

    def __repr__(self):
        return f"Route({self.pickup_id} -> {self.dropoff_id}: {self.trip_count} trips)"


class CustomMinHeap:
    """A vanilla Min-Heap implementation tailored for RouteMetrics based on trip counts."""
    def __init__(self):
        self.heap = []

    def parent(self, i): return (i - 1) // 2
    def left_child(self, i): return 2 * i + 1
    def right_child(self, i): return 2 * i + 2

    def push(self, item):
        self.heap.append(item)
        self._heapify_up(len(self.heap) - 1)

    def pop(self):
        if not self.heap:
            return None
        if len(self.heap) == 1:
            return self.heap.pop()
        
        root = self.heap[0]
        self.heap[0] = self.heap.pop()
        self._heapify_down(0)
        return root

    def peek(self):
        return self.heap[0] if self.heap else None

    def size(self):
        return len(self.heap)

    def _heapify_up(self, index):
        while index > 0 and self.heap[index].trip_count < self.heap[self.parent(index)].trip_count:
            p_idx = self.parent(index)
            self.heap[index], self.heap[p_idx] = self.heap[p_idx], self.heap[index]
            index = p_idx

    def _heapify_down(self, index):
        smallest = index
        left = self.left_child(index)
        right = self.right_child(index)
        n = len(self.heap)

        if left < n and self.heap[left].trip_count < self.heap[smallest].trip_count:
            smallest = left
        if right < n and self.heap[right].trip_count < self.heap[smallest].trip_count:
            smallest = right

        if smallest != index:
            self.heap[index], self.heap[smallest] = self.heap[smallest], self.heap[index]
            self._heapify_down(smallest)


def get_top_k_routes(raw_trips_list, k):
    """
    Extracts the top K busiest routes using CustomMinHeap.
    Expects a list of dicts: [{'pickup_id': int, 'dropoff_id': int, 'count': int}, ...]
    """
    min_heap = CustomMinHeap()

    for record in raw_trips_list:
        route = RouteMetrics(record['pickup_id'], record['dropoff_id'], record['count'])
        
        if min_heap.size() < k:
            min_heap.push(route)
        else:
            if route.trip_count > min_heap.peek().trip_count:
                min_heap.pop()
                min_heap.push(route)

    result = []
    while min_heap.size() > 0:
        result.append(min_heap.pop())
        
    return result[::-1]  # Return descending order (highest first)