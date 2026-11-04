"""Parsing quirks of the policy sheet and how rules are paired with checkers."""
from pathlib import Path

import pytest

from policy_registry import build_registry, load_checker_map, stamp_hashes
from policy_source import parse_policy_csv, text_hash

ADS_CSV = '''N°,Ads,Policy Admob,,Ví dụ tiêu chuẩn,Ví dụ vi phạm,Confirm,Note
1,Interstitial Ad,"Bắt buộc phải show
loading ad",,good,bad,FALSE,
3,,Ad inter hiển thị ngay,,,,FALSE,
,App AI,Có nút report,,,,FALSE,
'''

SUB_CSV = '''N°,Purchase,Policy,,Ví dụ tiêu chuẩn,Ví dụ vi phạm,Confirm
2,Subscriptions,Gói có free trial,"start with X days trial then giá",,,FALSE
3,,,Text trial không làm button riêng,,,FALSE
'''


def test_group_is_carried_down_and_numbers_keep_their_gaps():
    rules = parse_policy_csv(ADS_CSV, "Ad_VN")
    assert [r["no"] for r in rules[:2]] == ["1", "3"]
    assert rules[1]["group"] == "Interstitial Ad"
    # Line breaks inside a cell are not part of the rule's meaning.
    assert rules[0]["text"] == "Bắt buộc phải show loading ad"


def test_rule_without_number_gets_a_stable_text_key():
    rule = parse_policy_csv(ADS_CSV, "Ad_VN")[2]
    assert rule["no"] == f"h{text_hash('Có nút report')}"
    assert rule["group"] == "App AI"


def test_detail_column_is_the_rule_and_heading_is_inherited():
    rules = parse_policy_csv(SUB_CSV, "Sub_VN")
    assert rules[0]["text"] == "start with X days trial then giá"
    assert rules[1]["text"] == "Text trial không làm button riêng"
    assert rules[1]["topic"] == "Gói có free trial"
    assert rules[1]["group"] == "Subscriptions"


def _map(*refs):
    return {"tabs": ["Ad_VN"], "checkers": [{"id": "c1", "kind": "auto", "placement": "inter", "rules": list(refs)}]}


def test_rules_without_a_checker_are_reported_not_dropped():
    rules = parse_policy_csv(ADS_CSV, "Ad_VN")
    reg = build_registry(rules, _map({"tab": "Ad_VN", "no": "1"}))
    assert [r["no"] for r in reg["unmapped"]] == ["3", rules[2]["no"]]
    assert reg["checkers"][0]["rule_objs"][0]["no"] == "1"


def test_removed_and_reworded_rules_are_flagged():
    rules = parse_policy_csv(ADS_CSV, "Ad_VN")
    reg = build_registry(rules, _map({"tab": "Ad_VN", "no": "99"}, {"tab": "Ad_VN", "no": "1", "text_hash": "deadbeef"}))
    assert reg["missing"] == [{"checker": "c1", "tab": "Ad_VN", "no": "99"}]
    assert reg["drifted"][0]["rule"]["no"] == "1"


def test_stamp_records_current_wording():
    rules = parse_policy_csv(ADS_CSV, "Ad_VN")
    m = _map({"tab": "Ad_VN", "no": "1"})
    assert stamp_hashes(rules, m) == 1
    assert build_registry(rules, m)["drifted"] == []


def test_shipped_map_is_valid():
    data = load_checker_map()
    assert data["tabs"] == ["Đối tác", "Ad_VN", "Sub_VN"]


def test_duplicate_checker_ids_are_rejected(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text('{"tabs": [], "checkers": [{"id": "a", "kind": "auto", "rules": []},'
                 '{"id": "a", "kind": "auto", "rules": []}]}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_checker_map(p)
