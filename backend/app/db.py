"""SQLite 持久化层：合约风险台账。

以合约代码内容的 SHA-256 作为去重键：
- 同一份合约（相同代码）重复提交审计，只更新聚合信息，不产生重复记录；
- 风险台账与审计历史共用 contracts 表作为数据源，保证两个入口条目数一致。
"""
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "audit.db"

# 严重程度排序权重：critical > high > medium > low
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                code_hash      TEXT PRIMARY KEY,
                filename       TEXT NOT NULL,
                code           TEXT NOT NULL,
                latest_score   INTEGER NOT NULL,
                latest_vulns   TEXT NOT NULL,
                vuln_count     INTEGER NOT NULL,
                latest_time    TEXT NOT NULL,
                audit_count    INTEGER NOT NULL DEFAULT 1,
                created_time   TEXT NOT NULL
            )
            """
        )


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def save_audit(
    audit_id: str,
    filename: str,
    code: str,
    score: int,
    vulnerabilities: List[dict],
    timestamp: Optional[str] = None,
) -> dict:
    """落库一次审计结果。相同代码重复提交合并为同一条记录。

    返回 {"duplicated": bool, "audit_count": int}。
    """
    timestamp = timestamp or datetime.now().isoformat()
    digest = code_hash(code)
    vuln_json = json.dumps(vulnerabilities, ensure_ascii=False)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT audit_count FROM contracts WHERE code_hash = ?", (digest,)
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO contracts
                    (code_hash, filename, code, latest_score, latest_vulns,
                     vuln_count, latest_time, audit_count, created_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (digest, filename, code, score, vuln_json,
                 len(vulnerabilities), timestamp, timestamp),
            )
            return {"duplicated": False, "audit_count": 1}

        conn.execute(
            """
            UPDATE contracts
               SET filename = ?, code = ?, latest_score = ?, latest_vulns = ?,
                   vuln_count = ?, latest_time = ?, audit_count = audit_count + 1
             WHERE code_hash = ?
            """,
            (filename, code, score, vuln_json, len(vulnerabilities),
             timestamp, digest),
        )
        return {"duplicated": True, "audit_count": existing["audit_count"] + 1}


def _row_to_ledger_entry(row: sqlite3.Row) -> dict:
    vulns = json.loads(row["latest_vulns"])
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for v in vulns:
        key = v.get("severity", "low")
        severity_counts[key] = severity_counts.get(key, 0) + 1

    return {
        "codeHash": row["code_hash"],
        "filename": row["filename"],
        "latestScore": row["latest_score"],
        "vulnCount": row["vuln_count"],
        "latestTime": row["latest_time"],
        "createdTime": row["created_time"],
        "auditCount": row["audit_count"],
        "severityCounts": severity_counts,
        "hasFindings": row["vuln_count"] > 0,
        "vulnerabilities": vulns,
    }


def list_ledger() -> List[dict]:
    """风险台账：一份合约一条，最近审计的排前面。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM contracts ORDER BY latest_time DESC"
        ).fetchall()
    return [_row_to_ledger_entry(r) for r in rows]


def list_history() -> List[dict]:
    """审计历史：与台账同一份数据源，条目数一一对应（去掉漏洞明细）。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM contracts ORDER BY latest_time DESC"
        ).fetchall()

    entries = []
    for row in rows:
        entries.append({
            "codeHash": row["code_hash"],
            "filename": row["filename"],
            "score": row["latest_score"],
            "vulnCount": row["vuln_count"],
            "timestamp": row["latest_time"],
            "auditCount": row["audit_count"],
            "hasFindings": row["vuln_count"] > 0,
        })
    return entries
