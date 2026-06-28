import unittest
from unittest.mock import patch

from localhub.ui.api_client import ApiClient


class ApiClientTests(unittest.TestCase):
    def test_list_files_handles_connection_errors(self) -> None:
        client = ApiClient(base_url="http://127.0.0.1:1")

        with patch.object(client.client, "request", side_effect=Exception("connection failed")):
            self.assertEqual(client.list_files(), [])


if __name__ == "__main__":
    unittest.main()
