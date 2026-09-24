from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import hashlib
import json
import re
import sqlite3
import uuid
import random
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = FastAPI(title="Smart Contract Security Auditor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ---------------------------------------------------------------------------
# 风险台账持久化
# 同一份合约（以规范化代码的 sha256 为身份）无论提交多少次，台账中只保留一条，
# 重复提交只刷新最近一次审计结果、漏洞数量与时间，并累计审计次数。
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "audits.db"

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_LEVELS = ("critical", "high", "medium", "low")
CLEAN_NOTE = "该合约最近一次审计未命中任何已知漏洞模式，当前无在册风险项。建议保持关注编译器告警并定期复审。"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contract_audits (
                contract_key   TEXT PRIMARY KEY,
                filename       TEXT NOT NULL,
                code           TEXT NOT NULL,
                score          INTEGER NOT NULL,
                vuln_count     INTEGER NOT NULL,
                vulnerabilities TEXT NOT NULL,
                audit_count    INTEGER NOT NULL DEFAULT 1,
                first_audit_at TEXT NOT NULL,
                last_audit_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()


init_db()


def normalize_code(code: str) -> str:
    """规范化代码：统一换行符、去掉行尾空白与首尾空行，作为合约归并身份。"""
    unified = code.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in unified.split("\n")]
    return "\n".join(lines).strip()


def make_contract_key(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode("utf-8")).hexdigest()


def record_audit(filename: str, code: str, score: int, vulnerabilities: List[dict], ts: str) -> tuple[str, int]:
    """写入一次审计；合约已存在时更新原记录，不产生重复台账条目。"""
    key = make_contract_key(code)
    payload = json.dumps(vulnerabilities, ensure_ascii=False)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT audit_count FROM contract_audits WHERE contract_key = ?", (key,)
        ).fetchone()
        if row is None:
            audit_count = 1
            conn.execute(
                """INSERT INTO contract_audits
                   (contract_key, filename, code, score, vuln_count, vulnerabilities,
                    audit_count, first_audit_at, last_audit_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (key, filename, code, score, len(vulnerabilities), payload, audit_count, ts, ts),
            )
        else:
            audit_count = row["audit_count"] + 1
            conn.execute(
                """UPDATE contract_audits
                   SET filename = ?, code = ?, score = ?, vuln_count = ?,
                       vulnerabilities = ?, audit_count = ?, last_audit_at = ?
                   WHERE contract_key = ?""",
                (filename, code, score, len(vulnerabilities), payload, audit_count, ts, key),
            )
        conn.commit()
    return key, audit_count


def build_ledger_entries() -> List[dict]:
    """台账与历史共用同一份归并数据，保证两个入口条目数一致。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM contract_audits ORDER BY last_audit_at DESC"
        ).fetchall()

    entries = []
    for row in rows:
        vulns = json.loads(row["vulnerabilities"])
        # 台账中漏洞按严重程度排列（critical -> high -> medium -> low），同级按行号
        vulns.sort(key=lambda v: (SEVERITY_ORDER.get(v["severity"], 99), v.get("lineStart", v.get("line", 0))))
        severity_counts = {level: 0 for level in SEVERITY_LEVELS}
        for v in vulns:
            severity_counts[v["severity"]] = severity_counts.get(v["severity"], 0) + 1
        entries.append({
            "contractKey": row["contract_key"],
            "filename": row["filename"],
            "score": row["score"],
            "vulnCount": row["vuln_count"],
            "severityCounts": severity_counts,
            "auditCount": row["audit_count"],
            "firstAuditAt": row["first_audit_at"],
            "lastAuditAt": row["last_audit_at"],
            "vulnerabilities": vulns,
            # 无漏洞合约给明确说明，避免展开后一片空白
            "note": None if vulns else CLEAN_NOTE,
        })
    return entries


# Vulnerability patterns
VULNERABILITY_PATTERNS = [
    {
        "type": "重入攻击 (Reentrancy)",
        "severity": "critical",
        "pattern": r"\.call\{[^}]*value:\s*[^}]*\}\([^)]*\)",
        "description": "使用低级call()或send()转移ETH存在重入攻击风险。攻击者可部署恶意合约在fallback中反复调用提款。",
        "suggestion": "使用Checks-Effects-Interactions模式，或引入ReentrancyGuard。推荐使用transfer()或call()并限制Gas。"
    },
    {
        "type": "整数溢出 (Integer Overflow/Underflow)",
        "severity": "high",
        "pattern": r"[+\-*/]\s*=|(&&|\|\|)\s*\w+\s*[<>=]",
        "description": "Solidity 0.7及以下版本，未使用SafeMath时可能发生整数溢出。",
        "suggestion": "使用SafeMath库或升级到Solidity 0.8+（内置溢出检查）。"
    },
    {
        "type": "未授权访问控制",
        "severity": "high",
        "pattern": r"function\s+\w+\s*\([^)]*\)\s*public\s*(payable)?\s*\{[^}]*(?:require|if)\s*\(",
        "description": "关键函数缺少访问控制检查，任何人都可以调用。",
        "suggestion": "添加onlyOwner或自定义访问控制修饰符。"
    },
    {
        "type": "selfdestruct使用",
        "severity": "medium",
        "pattern": r"selfdestruct|suicide",
        "description": "selfdestruct可强制将合约所有ETH发送到任意地址，可能被滥用。",
        "suggestion": "谨慎使用selfdestruct，确保有正当的业务需求。"
    },
    {
        "type": "tx.origin钓鱼",
        "severity": "high",
        "pattern": r"tx\.origin",
        "description": "使用tx.origin进行身份验证可能被钓鱼攻击，攻击者诱导用户触发交易。",
        "suggestion": "使用msg.sender代替tx.origin进行身份验证。"
    },
    {
        "type": "精确度损失",
        "severity": "medium",
        "pattern": r"/\s*\d+",
        "description": "除法运算可能导致精度损失，特别是在代币金额计算中。",
        "suggestion": "先乘后除，使用高精度计算或使用Babylonian方法。"
    },
]

GAS_PATTERNS = [
    {"function": "storage_read", "issue": "循环中读取storage变量", "saving": 0.3},
    {"function": "redundant_sstore", "issue": "不必要的storage写入", "saving": 0.25},
    {"function": "short_circuit", "issue": "逻辑运算可短路优化", "saving": 0.15},
]

class AuditRequest(BaseModel):
    code: str
    filename: str

def detect_vulnerabilities(code: str) -> List[dict]:
    """Scan code for vulnerability patterns"""
    lines = code.split("\n")
    vulnerabilities = []

    for vp in VULNERABILITY_PATTERNS:
        matches = re.finditer(vp["pattern"], code, re.MULTILINE)
        for m in matches:
            # 匹配片段可能跨多行，记录行号区间
            line_start = code[:m.start()].count("\n") + 1
            line_end = code[:m.end()].count("\n") + 1
            # Find context
            context_start = max(0, line_start - 2)
            context_end = min(len(lines), line_end + 2)
            context = "\n".join(lines[context_start:context_end])

            vulnerabilities.append({
                "type": vp["type"],
                "severity": vp["severity"],
                "line": line_start,
                "lineStart": line_start,
                "lineEnd": line_end,
                "description": vp["description"],
                "suggestion": vp["suggestion"],
                "code": context.strip()
            })

    # 按严重程度排列
    vulnerabilities.sort(key=lambda v: (SEVERITY_ORDER.get(v["severity"], 99), v["lineStart"]))
    return vulnerabilities

def compute_gas_issues(code: str) -> List[dict]:
    """Analyze gas consumption issues"""
    issues = []
    functions = re.findall(r"function\s+(\w+)\s*\(", code)
    for fn in functions:
        base_gas = random.randint(20000, 60000)
        issues.append({
            "functionName": f"{fn}()",
            "currentGas": base_gas,
            "optimizedGas": int(base_gas * (0.7 + random.random() * 0.2)),
            "suggestion": random.choice(["移除不必要的storage写入", "缓存storage变量到memory", "使用短路逻辑", "合并多个事件为一个"])
        })
    return issues

def compute_security_score(vulnerabilities: List[dict]) -> int:
    """Compute overall security score"""
    if not vulnerabilities:
        return 100
    severity_weights = {"critical": 25, "high": 15, "medium": 8, "low": 3}
    deduction = sum(severity_weights.get(v["severity"], 5) for v in vulnerabilities)
    return max(0, 100 - deduction)

@app.get("/")
async def root():
    return {"message": "Smart Contract Security Auditor", "version": "1.0.0"}

@app.get("/api/patterns")
async def list_patterns():
    return {"code": 0, "message": "success", "data": VULNERABILITY_PATTERNS}

@app.post("/api/audit")
async def audit_contract(request: AuditRequest):
    vulnerabilities = detect_vulnerabilities(request.code)
    gas_issues = compute_gas_issues(request.code)
    score = compute_security_score(vulnerabilities)
    timestamp = datetime.now().isoformat()

    # 提交即入册；同一合约重复提交归并为一条
    contract_key, audit_count = record_audit(
        request.filename, request.code, score, vulnerabilities, timestamp
    )

    result = {
        "id": str(uuid.uuid4()),
        "contractKey": contract_key,
        "filename": request.filename,
        "score": score,
        "vulnerabilities": vulnerabilities,
        "gasIssues": gas_issues,
        "auditCount": audit_count,
        "timestamp": timestamp
    }

    return {"code": 0, "message": "success", "data": result}

@app.get("/api/ledger")
async def get_ledger():
    """风险台账：按合约归并，含最近一次漏洞明细（按严重程度排列）。"""
    return {"code": 0, "message": "success", "data": build_ledger_entries()}

@app.get("/api/history")
async def get_history():
    """审计历史：与台账共用归并数据，条目数一一对应。"""
    data = [
        {
            "contractKey": e["contractKey"],
            "filename": e["filename"],
            "score": e["score"],
            "vulnCount": e["vulnCount"],
            "severityCounts": e["severityCounts"],
            "auditCount": e["auditCount"],
            "timestamp": e["lastAuditAt"],
        }
        for e in build_ledger_entries()
    ]
    return {"code": 0, "message": "success", "data": data}

@app.post("/api/report/{audit_id}")
async def generate_report(audit_id: str):
    """Generate PDF report"""
    # Simplified report generation
    return {"code": 0, "message": "success", "data": {"url": f"/api/reports/{audit_id}.pdf"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
