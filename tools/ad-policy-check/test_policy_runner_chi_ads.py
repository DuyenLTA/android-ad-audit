"""Luot chi check policy ads: rule chi thuoc tab Sub_VN bi bo, rule dung chung tab ads van giu."""
from policy_check_runner import chi_sub


def test_rule_chi_thuoc_sub_bi_bo():
    assert chi_sub([{"tab": "Sub_VN", "no": "1"}, {"tab": "Sub_VN", "no": "2"}])


def test_rule_dung_chung_tab_ads_van_giu():
    assert not chi_sub([{"tab": "Sub_VN", "no": "3"}, {"tab": "Ad_VN", "no": "4"}])
    assert not chi_sub([{"tab": "Đối tác", "no": "1"}])
    assert not chi_sub([])
