"""
Decision Logger - SQLite persistence for all agent decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json
import sqlite3
import threading
from pathlib import Path


class DecisionType(str, Enum):
    """Types of decisions that can be logged."""
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_ALLOCATION = "resource_allocation"
    RESOURCE_RELEASE = "resource_release"
    BID_SUBMITTED = "bid_submitted"
    BID_APPROVED = "bid_approved"
    BID_REJECTED = "bid_rejected"
    BUDGET_WARNING = "budget_warning"
    BUDGET_OVERRIDE = "budget_override"
    PREEMPTION = "preemption"
    IRRIGATION = "irrigation"
    FEED = "feed"
    MAINTENANCE = "maintenance"
    ALERT = "alert"
    MANUAL_OVERRIDE = "manual_override"


class DecisionOutcome(str, Enum):
    """Outcome of a decision."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class DecisionRecord:
    """A logged decision record."""
    decision_id: str
    farm_id: str
    agent_id: str
    decision_type: DecisionType
    timestamp: datetime
    outcome: DecisionOutcome
    description: str
    resource_type: Optional[str] = None
    amount: Optional[float] = None
    priority: Optional[int] = None
    justification: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    related_decisions: List[str] = field(default_factory=list)
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "decision_id": self.decision_id,
            "farm_id": self.farm_id,
            "agent_id": self.agent_id,
            "decision_type": self.decision_type.value,
            "timestamp": self.timestamp.isoformat(),
            "outcome": self.outcome.value,
            "description": self.description,
            "resource_type": self.resource_type,
            "amount": self.amount,
            "priority": self.priority,
            "justification": self.justification,
            "context": json.dumps(self.context),
            "related_decisions": json.dumps(self.related_decisions),
            "duration_ms": self.duration_ms,
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> "DecisionRecord":
        """Create from database row."""
        return cls(
            decision_id=row[0],
            farm_id=row[1],
            agent_id=row[2],
            decision_type=DecisionType(row[3]),
            timestamp=datetime.fromisoformat(row[4]),
            outcome=DecisionOutcome(row[5]),
            description=row[6],
            resource_type=row[7],
            amount=row[8],
            priority=row[9],
            justification=row[10],
            context=json.loads(row[11]) if row[11] else {},
            related_decisions=json.loads(row[12]) if row[12] else [],
            duration_ms=row[13],
        )


class DecisionLogger:
    """
    Logs all agent decisions to SQLite for audit trail and replay.
    
    Features:
    - Persistent SQLite storage
    - Full-text search on descriptions
    - Filtering by agent, type, outcome, date range
    - Decision replay support
    - Export to JSON/CSV
    - Thread-safe operations
    """
    
    def __init__(self, db_path: str = "data/decisions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._local = threading.local()
        self._decision_counter = 0
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Main decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                farm_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                outcome TEXT NOT NULL,
                description TEXT NOT NULL,
                resource_type TEXT,
                amount REAL,
                priority INTEGER,
                justification TEXT,
                context TEXT,
                related_decisions TEXT,
                duration_ms INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_farm 
            ON decisions(farm_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_agent 
            ON decisions(agent_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_type 
            ON decisions(decision_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_timestamp 
            ON decisions(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_resource 
            ON decisions(resource_type)
        """)
        
        # Full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts
            USING fts5(decision_id, description, justification, content='decisions')
        """)
        
        # Triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
                INSERT INTO decisions_fts(decision_id, description, justification)
                VALUES (new.decision_id, new.description, new.justification);
            END
        """)
        
        conn.commit()
    
    def log(
        self,
        farm_id: str,
        agent_id: str,
        decision_type: DecisionType,
        outcome: DecisionOutcome,
        description: str,
        resource_type: Optional[str] = None,
        amount: Optional[float] = None,
        priority: Optional[int] = None,
        justification: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        related_decisions: Optional[List[str]] = None,
        duration_ms: Optional[int] = None,
    ) -> DecisionRecord:
        """
        Log a decision.
        
        Returns the created record.
        """
        with self._lock:
            self._decision_counter += 1
            decision_id = f"dec-{farm_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._decision_counter:04d}"
        
        record = DecisionRecord(
            decision_id=decision_id,
            farm_id=farm_id,
            agent_id=agent_id,
            decision_type=decision_type,
            timestamp=datetime.now(),
            outcome=outcome,
            description=description,
            resource_type=resource_type,
            amount=amount,
            priority=priority,
            justification=justification,
            context=context or {},
            related_decisions=related_decisions or [],
            duration_ms=duration_ms,
        )
        
        self._insert_record(record)
        return record
    
    def _insert_record(self, record: DecisionRecord) -> None:
        """Insert a record into the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        data = record.to_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        
        cursor.execute(
            f"INSERT INTO decisions ({columns}) VALUES ({placeholders})",
            list(data.values())
        )
        conn.commit()
    
    def get(self, decision_id: str) -> Optional[DecisionRecord]:
        """Get a decision by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM decisions WHERE decision_id = ?",
            (decision_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return DecisionRecord.from_row(tuple(row))
        return None
    
    def query(
        self,
        farm_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        decision_type: Optional[DecisionType] = None,
        outcome: Optional[DecisionOutcome] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[DecisionRecord]:
        """
        Query decisions with filters.
        
        Returns list of matching records.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if farm_id:
            conditions.append("farm_id = ?")
            params.append(farm_id)
        
        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        
        if decision_type:
            conditions.append("decision_type = ?")
            params.append(decision_type.value)
        
        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome.value)
        
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date.isoformat())
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date.isoformat())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order = "DESC" if order_desc else "ASC"
        
        cursor.execute(
            f"""
            SELECT * FROM decisions 
            WHERE {where_clause}
            ORDER BY timestamp {order}
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        )
        
        return [DecisionRecord.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def search(
        self,
        query: str,
        farm_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DecisionRecord]:
        """
        Full-text search on decision descriptions and justifications.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if farm_id:
            cursor.execute(
                """
                SELECT d.* FROM decisions d
                JOIN decisions_fts fts ON d.decision_id = fts.decision_id
                WHERE fts.decisions_fts MATCH ? AND d.farm_id = ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, farm_id, limit)
            )
        else:
            cursor.execute(
                """
                SELECT d.* FROM decisions d
                JOIN decisions_fts fts ON d.decision_id = fts.decision_id
                WHERE fts.decisions_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit)
            )
        
        return [DecisionRecord.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_statistics(
        self,
        farm_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get decision statistics for a farm."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        date_filter = ""
        params = [farm_id]
        
        if start_date:
            date_filter += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            date_filter += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        # Total counts by type
        cursor.execute(
            f"""
            SELECT decision_type, COUNT(*) as count
            FROM decisions
            WHERE farm_id = ? {date_filter}
            GROUP BY decision_type
            """,
            params
        )
        by_type = {row["decision_type"]: row["count"] for row in cursor.fetchall()}
        
        # Counts by outcome
        cursor.execute(
            f"""
            SELECT outcome, COUNT(*) as count
            FROM decisions
            WHERE farm_id = ? {date_filter}
            GROUP BY outcome
            """,
            params
        )
        by_outcome = {row["outcome"]: row["count"] for row in cursor.fetchall()}
        
        # Counts by agent
        cursor.execute(
            f"""
            SELECT agent_id, COUNT(*) as count
            FROM decisions
            WHERE farm_id = ? {date_filter}
            GROUP BY agent_id
            """,
            params
        )
        by_agent = {row["agent_id"]: row["count"] for row in cursor.fetchall()}
        
        # Resource usage
        cursor.execute(
            f"""
            SELECT resource_type, SUM(amount) as total
            FROM decisions
            WHERE farm_id = ? AND amount IS NOT NULL {date_filter}
            GROUP BY resource_type
            """,
            params
        )
        by_resource = {row["resource_type"]: row["total"] for row in cursor.fetchall() if row["resource_type"]}
        
        # Total and success rate
        total = sum(by_outcome.values())
        success = by_outcome.get("success", 0) + by_outcome.get("partial", 0)
        
        return {
            "total_decisions": total,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "by_outcome": by_outcome,
            "by_agent": by_agent,
            "resource_totals": by_resource,
        }
    
    def export_json(
        self,
        farm_id: str,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Export decisions to JSON file.
        
        Returns number of records exported.
        """
        records = self.query(
            farm_id=farm_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )
        
        data = {
            "farm_id": farm_id,
            "exported_at": datetime.now().isoformat(),
            "record_count": len(records),
            "decisions": [r.to_dict() for r in records],
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return len(records)
    
    def export_csv(
        self,
        farm_id: str,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Export decisions to CSV file.
        
        Returns number of records exported.
        """
        import csv
        
        records = self.query(
            farm_id=farm_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )
        
        if not records:
            return 0
        
        fieldnames = [
            "decision_id", "timestamp", "agent_id", "decision_type",
            "outcome", "resource_type", "amount", "priority",
            "description", "justification"
        ]
        
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in records:
                writer.writerow({
                    "decision_id": record.decision_id,
                    "timestamp": record.timestamp.isoformat(),
                    "agent_id": record.agent_id,
                    "decision_type": record.decision_type.value,
                    "outcome": record.outcome.value,
                    "resource_type": record.resource_type,
                    "amount": record.amount,
                    "priority": record.priority,
                    "description": record.description,
                    "justification": record.justification,
                })
        
        return len(records)
    
    def get_timeline(
        self,
        farm_id: str,
        start_date: datetime,
        end_date: datetime,
        bucket_minutes: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Get decision timeline with counts bucketed by time.
        
        Useful for burn-down and activity charts.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # SQLite strftime for bucketing
        cursor.execute(
            """
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as bucket,
                decision_type,
                COUNT(*) as count,
                SUM(CASE WHEN amount IS NOT NULL THEN amount ELSE 0 END) as total_amount
            FROM decisions
            WHERE farm_id = ? AND timestamp >= ? AND timestamp <= ?
            GROUP BY bucket, decision_type
            ORDER BY bucket
            """,
            (farm_id, start_date.isoformat(), end_date.isoformat())
        )
        
        result = []
        current_bucket = None
        bucket_data = {}
        
        for row in cursor.fetchall():
            bucket = row["bucket"]
            
            if bucket != current_bucket:
                if current_bucket and bucket_data:
                    result.append({
                        "timestamp": current_bucket,
                        **bucket_data
                    })
                current_bucket = bucket
                bucket_data = {"decisions": 0, "by_type": {}}
            
            bucket_data["decisions"] += row["count"]
            bucket_data["by_type"][row["decision_type"]] = {
                "count": row["count"],
                "amount": row["total_amount"],
            }
        
        if current_bucket and bucket_data:
            result.append({
                "timestamp": current_bucket,
                **bucket_data
            })
        
        return result
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
