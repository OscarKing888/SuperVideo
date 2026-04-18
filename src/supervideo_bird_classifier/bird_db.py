"""Bird species database manager using SQLite."""

import os
import sqlite3
from typing import Dict, List, Optional, Set


class BirdDatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "data", "bird_reference.sqlite")
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Bird database not found: {db_path}")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_bird_by_class_id(self, class_id: int) -> Optional[Dict]:
        query = (
            "SELECT id, english_name, chinese_simplified, chinese_traditional, "
            "scientific_name, ebird_code, short_description_zh "
            "FROM BirdCountInfo WHERE model_class_id = ?"
        )
        with self._connect() as conn:
            row = conn.execute(query, (class_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "english_name": row[1],
            "chinese_simplified": row[2],
            "chinese_traditional": row[3],
            "scientific_name": row[4],
            "ebird_code": row[5],
            "description": row[6],
        }

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        sql = (
            "SELECT id, english_name, chinese_simplified, ebird_code, scientific_name "
            "FROM BirdCountInfo "
            "WHERE english_name LIKE ? OR chinese_simplified LIKE ? OR scientific_name LIKE ? "
            "LIMIT ?"
        )
        term = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(sql, (term, term, term, limit)).fetchall()
        return [
            {
                "id": r[0],
                "english_name": r[1],
                "chinese_simplified": r[2],
                "ebird_code": r[3],
                "scientific_name": r[4],
            }
            for r in rows
        ]

    def get_all_ebird_codes(self) -> Set[str]:
        query = (
            "SELECT DISTINCT ebird_code FROM BirdCountInfo "
            "WHERE ebird_code IS NOT NULL AND ebird_code != ''"
        )
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
        return {r[0] for r in rows}

    def get_statistics(self) -> Dict:
        queries = {
            "total": "SELECT COUNT(*) FROM BirdCountInfo",
            "with_ebird": "SELECT COUNT(*) FROM BirdCountInfo WHERE ebird_code IS NOT NULL AND ebird_code != ''",
        }
        stats = {}
        with self._connect() as conn:
            for key, q in queries.items():
                stats[key] = conn.execute(q).fetchone()[0]
        return stats
