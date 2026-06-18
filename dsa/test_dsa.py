import unittest
from top_k_routes import get_top_k_routes

class TestTopKRoutes(unittest.TestCase):
    def test_top_k_extraction(self):
        mock_data = [
            {'pickup_id': 1, 'dropoff_id': 2, 'count': 50},
            {'pickup_id': 3, 'dropoff_id': 4, 'count': 500},
            {'pickup_id': 5, 'dropoff_id': 6, 'count': 20},
            {'pickup_id': 7, 'dropoff_id': 8, 'count': 350},
        ]
        
        # Ask for Top 2 elements
        result = get_top_k_routes(mock_data, k=2)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].trip_count, 500)  # Ranked 1
        self.assertEqual(result[1].trip_count, 350)  # Ranked 2

if __name__ == '__main__':
    unittest.main()