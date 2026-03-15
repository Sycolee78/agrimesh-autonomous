"""
Decision Logger for AgriMesh Autonomous

Persists all agent decisions to SQLite for analysis and auditing.
Supports querying, filtering, and decision replay.
"""

import sqlite3
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


@dataclass
class Decision:
    """A logged agent decision."""
    decision_id: str
    agent_id: str
    agent_name: str
    decision_type: str  # e.g., "irrigation", "allocation", "alert"
    action: str  # e.g., "irrigate_zone_A", "request_water"
    parameters: Dict[str, Any]
    context: Dict[str, Any]  # State at time of decision
    outcome: Optional[str] = None
    outcome_value: Optional[float] = None
    timestamp: datetime = None
    execution_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DecisionLogger:
    """
    SQLite-backed decision logger.
    
    Logs all agent decisions with context for:
    - Post-hoc analysis
    - Decision replay and simulation
    - Audit trail
    - ML training data generation
    """

    def __init__(self, db_path: str = "farm_os/logs/decisions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """Context manager for database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT UNIQUE NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    context TEXT NOT NULL,
                    outcome TEXT,
                    outcome_value REAL,
                    timestamp TEXT NOT NULL,
                    execution_ms INTEGER,
                    success INTEGER NOT NULL DEFAULT 1,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_decisions_agent 
                    ON decisions(agent_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_type 
                    ON decisions(decision_type);
                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp 
                    ON decisions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_decisions_success 
                    ON decisions(success);

                CREATE TABLE IF NOT EXISTS decision_tags (
                    decision_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    PRIMARY KEY (decision_id, tag),
                    FOREIGN KEY (decision_id) REFERENCES decisions(decision_id)
                );

                CREATE TABLE IF NOT EXISTS decision_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (decision_id) REFERENCES decisions(decision_id)
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_decision 
                    ON decision_metrics(decision_id);
            """)
            conn.commit()

    def log(self, decision: Decision) -> str:
        """
        Log a decision to the database.
        
        Returns decision_id.
        """
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO decisions (
                    decision_id, agent_id, agent_name, decision_type,
                    action, parameters, context, outcome, outcome_value,
                    timestamp, execution_ms, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.decision_id,
                decision.agent_id,
                decision.agent_name,
                decision.decision_type,
                decision.action,
                json.dumps(decision.parameters),
                json.dumps(decision.context),
                decision.outcome,
                decision.outcome_value,
                decision.timestamp.isoformat(),
                decision.execution_ms,
                1 if decision.success else 0,
                decision.error_message
            ))
            conn.commit()
        return decision.decision_id

    def log_quick(
        self,
        agent_id: str,
        agent_name: str,
        decision_type: str,
        action: str,
        parameters: Dict = None,
        context: Dict = None
    ) -> str:
        """Quick logging with minimal parameters."""
        from uuid import uuid4
        decision = Decision(
            decision_id=str(uuid4())[:12],
            agent_id=agent_id,
            agent_name=agent_name,
            decision_type=decision_type,
            action=action,
            parameters=parameters or {},
            context=context or {}
        )
        return self.log(decision)

    def update_outcome(
        self,
        decision_id: str,
        outcome: str,
        outcome_value: Optional[float] = None,
        success: bool = True
    ) -> None:
        """Update a decision with its outcome after execution."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE decisions 
                SET outcome = ?, outcome_value = ?, success = ?
                WHERE decision_id = ?
            """, (outcome, outcome_value, 1 if success else 0, decision_id))
            conn.commit()

    def add_tags(self, decision_id: str, tags: List[str]) -> None:
        """Add tags to a decision for categorization."""
        with self._get_conn() as conn:
            for tag in tags:
                conn.execute("""
                    INSERT OR IGNORE INTO decision_tags (decision_id, tag)
                    VALUES (?, ?)
                """, (decision_id, tag))
            conn.commit()

    def add_metric(
        self,
        decision_id: str,
        metric_name: str,
        metric_value: float
    ) -> None:
        """Add a metric measurement linked to a decision."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO decision_metrics (decision_id, metric_name, metric_value)
                VALUES (?, ?, ?)
            """, (decision_id, metric_name, metric_value))
            conn.commit()

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Retrieve a decision by ID."""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT * FROM decisions WHERE decision_id = ?
            """, (decision_id,)).fetchone()
            
            if row:
                return self._row_to_decision(row)
        return None

    def _row_to_decision(self, row: sqlite3.Row) -> Decision:
        """Convert database row to Decision object."""
        return Decision(
            decision_id=row["decision_id"],
            agent_id=row["agent_id"],
            agent_name=row["agent_name"],
            decision_type=row["decision_type"],
            action=row["action"],
            parameters=json.loads(row["parameters"]),
            context=json.loads(row["context"]),
            outcome=row["outcome"],
            outcome_value=row["outcome_value"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            execution_ms=row["execution_ms"],
            success=bool(row["success"]),
            error_message=row["error_message"]
        )

    def query(
        self,
        agent_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success_only: bool = False,
        limit: int = 100
    ) -> List[Decision]:
        """Query decisions with filters."""
        conditions = []
        params = []

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if decision_type:
            conditions.append("decision_type = ?")
            params.append(decision_type)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        if success_only:
            conditions.append("success = 1")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM decisions
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """, params).fetchall()

            return [self._row_to_decision(row) for row in rows]

    def get_daily_summary(self, date: datetime = None) -> Dict:
        """Get summary statistics for a day."""
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        with self._get_conn() as conn:
            # Total decisions
            total = conn.execute("""
                SELECT COUNT(*) FROM decisions
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat())).fetchone()[0]

            # By agent
            by_agent = conn.execute("""
                SELECT agent_name, COUNT(*) as count,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
                FROM decisions
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY agent_name
            """, (start.isoformat(), end.isoformat())).fetchall()

            # By type
            by_type = conn.execute("""
                SELECT decision_type, COUNT(*) as count
                FROM decisions
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY decision_type
            """, (start.isoformat(), end.isoformat())).fetchall()

            return {
                "date": date.strftime("%Y-%m-%d"),
                "total_decisions": total,
                "by_agent": {row[0]: {"count": row[1], "success": row[2]} for row in by_agent},
                "by_type": {row[0]: row[1] for row in by_type}
            }

    def export_for_training(
        self,
        decision_type: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Export decisions as training data for ML models."""
        decisions = self.query(
            decision_type=decision_type,
            start_time=start_time,
            end_time=end_time,
            success_only=True,
            limit=10000
        )

        return [
            {
                "context": d.context,
                "action": d.action,
                "parameters": d.parameters,
                "outcome_value": d.outcome_value
            }
            for d in decisions
            if d.outcome_value is not None
        ]


# Global logger instance
_default_logger: Optional[DecisionLogger] = None


def get_logger(db_path: str = None) -> DecisionLogger:
    """Get or create the default logger instance."""
    global _default_logger
    if _default_logger is None:
        _default_logger = DecisionLogger(
            db_path or "farm_os/logs/decisions.db"
        )
    return _default_logger


def log_decision(
    agent_id: str,
    agent_name: str,
    decision_type: str,
    action: str,
    parameters: Dict = None,
    context: Dict = None
) -> str:
    """Convenience function for quick logging."""
    return get_logger().log_quick(
        agent_id, agent_name, decision_type, action, parameters, context
    )
