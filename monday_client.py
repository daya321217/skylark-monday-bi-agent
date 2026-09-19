import requests

API_URL = "https://api.monday.com/v2"

class MondayAPIError(RuntimeError):
    pass

class MondayClient:
    def __init__(self, token: str, timeout: int = 30):
        self.token = token
        self.timeout = timeout

    def _query(self, query: str, variables=None):
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }
        r = requests.post(
            API_URL,
            headers=headers,
            json={"query": query, "variables": variables or {}},
            timeout=self.timeout,
        )
        if r.status_code != 200:
            raise MondayAPIError(f"HTTP {r.status_code}: {r.text[:500]}")
        payload = r.json()
        if payload.get("errors"):
            raise MondayAPIError(str(payload["errors"])[:1500])
        return payload["data"]

    def get_board(self, board_id: str):
        q = """
        query ($board_id: [ID!]) {
          boards(ids: $board_id) {
            id
            name
            state
            permissions
            columns { id title type }
            items_page(limit: 500) {
              cursor
              items {
                id
                name
                created_at
                updated_at
                column_values { id text value type }
              }
            }
          }
        }
        """
        data = self._query(q, {"board_id": [str(board_id)]})
        boards = data.get("boards", [])
        if not boards:
            raise MondayAPIError(f"Board {board_id} was not found or is not accessible.")

        board = boards[0]
        items = list(board["items_page"]["items"])
        cursor = board["items_page"].get("cursor")

        while cursor:
            q2 = """
            query ($cursor: String!) {
              next_items_page(cursor: $cursor) {
                cursor
                items {
                  id
                  name
                  created_at
                  updated_at
                  column_values { id text value type }
                }
              }
            }
            """
            page = self._query(q2, {"cursor": cursor})["next_items_page"]
            items.extend(page["items"])
            cursor = page.get("cursor")

        return {
            "meta": {
                "id": board["id"],
                "name": board["name"],
                "state": board["state"],
                "permissions": board["permissions"],
                "columns": board["columns"],
                "item_count": len(items),
            },
            "items": items,
        }
