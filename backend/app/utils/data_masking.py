def mask_phone(phone: str) -> str:
    """手机号脱敏，保留前 3 位和后 4 位，中间用 **** 替换。"""
    if not phone:
        return ""
    if len(phone) < 7:
        return "*" * len(phone)
    return phone[:3] + "****" + phone[-4:]


def mask_id_card(id_card: str) -> str:
    """身份证号脱敏，保留前 6 位和后 4 位，中间用 ******** 替换。"""
    if not id_card:
        return ""
    if len(id_card) < 14:
        return "*" * len(id_card)
    return id_card[:6] + "********" + id_card[-4:]


def mask_unpublished_scores(data: dict) -> dict:
    """对未发布状态的考核记录进行分数脱敏，将 total_score 和 grade 置为 None。"""
    status = data.get("status", "")
    if status not in ("published", "archived"):
        data["total_score"] = None
        data["grade"] = None
    return data
