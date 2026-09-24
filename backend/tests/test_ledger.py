"""风险台账行为测试：去重、严重程度排序、行号区间、空结果、台账/历史条目一致。"""
import os
import tempfile

import pytest


@pytest.fixture()
def isolated_db(monkeypatch):
    """每个用例使用独立临时数据库。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    from app import db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_module.Path(tmp.name))
    db_module.init_db()
    yield db_module
    os.unlink(tmp.name)


VULN_CODE = """pragma solidity ^0.8.0;
contract Bank {
    mapping(address=>uint) bal;
    function withdraw(uint a) public {
        require(bal[msg.sender] >= a);
        (bool ok,) = msg.sender.call{value: a}("");
        require(ok);
        bal[msg.sender] -= a;
    }
}"""

CLEAN_CODE = """pragma solidity ^0.8.0;
contract Clean {
    uint public x;
}"""


def test_detect_sorted_by_severity_and_line():
    from app.main import detect_vulnerabilities
    vulns = detect_vulnerabilities(VULN_CODE)
    assert len(vulns) >= 2
    ranks = [{"critical": 0, "high": 1, "medium": 2, "low": 3}[v["severity"]] for v in vulns]
    assert ranks == sorted(ranks)
    # 每条漏洞都带行号区间，且区间合法
    for v in vulns:
        assert v["lineStart"] >= 1
        assert v["lineEnd"] >= v["lineStart"]
        assert v["line"] == v["lineStart"]
        assert v["suggestion"]


def test_repeated_submission_merges(isolated_db):
    isolated_db.save_audit("a1", "Bank.sol", VULN_CODE, 45, [{"severity": "critical"}])
    second = isolated_db.save_audit("a2", "Bank.sol", VULN_CODE, 45, [{"severity": "critical"}])
    assert second == {"duplicated": True, "audit_count": 2}
    ledger = isolated_db.list_ledger()
    assert len(ledger) == 1
    assert ledger[0]["auditCount"] == 2
    assert ledger[0]["vulnCount"] == 1
    # 最近审计时间已更新（created_time 保持首次）
    assert ledger[0]["latestTime"] >= ledger[0]["createdTime"]


def test_different_codes_are_separate(isolated_db):
    isolated_db.save_audit("a1", "Bank.sol", VULN_CODE, 45, [{"severity": "high"}])
    isolated_db.save_audit("a2", "Clean.sol", CLEAN_CODE, 100, [])
    ledger = isolated_db.list_ledger()
    assert len(ledger) == 2


def test_clean_contract_has_explicit_clean_state(isolated_db):
    isolated_db.save_audit("a1", "Clean.sol", CLEAN_CODE, 100, [])
    entry = isolated_db.list_ledger()[0]
    assert entry["vulnCount"] == 0
    assert entry["hasFindings"] is False
    assert entry["vulnerabilities"] == []
    assert entry["severityCounts"] == {"critical": 0, "high": 0, "medium": 0, "low": 0}


def test_severity_counts(isolated_db):
    from app.main import detect_vulnerabilities
    vulns = detect_vulnerabilities(VULN_CODE)
    isolated_db.save_audit("a1", "Bank.sol", VULN_CODE, 45, vulns)
    entry = isolated_db.list_ledger()[0]
    counts = entry["severityCounts"]
    assert sum(counts.values()) == entry["vulnCount"] == len(vulns)
    assert counts["critical"] >= 1


def test_history_matches_ledger(isolated_db):
    isolated_db.save_audit("a1", "Bank.sol", VULN_CODE, 45, [{"severity": "high"}])
    isolated_db.save_audit("dup", "Bank.sol", VULN_CODE, 45, [{"severity": "high"}])
    isolated_db.save_audit("a2", "Clean.sol", CLEAN_CODE, 100, [])
    ledger = isolated_db.list_ledger()
    history = isolated_db.list_history()
    # 两个入口条目数一一对应
    assert len(ledger) == len(history) == 2
    ledger_hashes = {e["codeHash"] for e in ledger}
    history_hashes = {e["codeHash"] for e in history}
    assert ledger_hashes == history_hashes
    bank_hist = next(h for h in history if h["filename"] == "Bank.sol")
    assert bank_hist["auditCount"] == 2
    assert bank_hist["vulnCount"] == 1
    assert bank_hist["hasFindings"] is True
