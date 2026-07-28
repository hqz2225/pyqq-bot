"""
积分兑换插件
管理可增减兑换内容 / 用户积分兑换
"""
import json
import os

from config import EXCHANGE_FILE, DATA_DIR


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(EXCHANGE_FILE):
        with open(EXCHANGE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(EXCHANGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(EXCHANGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _key(group_id):
    return str(group_id)


def list_items(group_id):
    """列出当前群的兑换物品"""
    data = _load()
    k = _key(group_id)
    items = data.get(k, [])
    if not items:
        return "本群暂无兑换物品，管理员可以发送: 添加兑换 名称 所需积分"
    lines = ["兑换列表:"]
    for i, item in enumerate(items):
        lines.append(f"  {i+1}. {item['name']} - {item['price']} 积分")
    lines.append("\n发送: 兑换 编号  来兑换")
    return "\n".join(lines)


def add_item(group_id, name, price):
    """添加兑换物品"""
    data = _load()
    k = _key(group_id)
    if k not in data:
        data[k] = []
    data[k].append({"name": name, "price": price})
    _save(data)
    return f"已添加兑换物品: {name} ({price} 积分)"


def remove_item(group_id, index):
    """删除兑换物品"""
    data = _load()
    k = _key(group_id)
    items = data.get(k, [])
    if not items or index < 1 or index > len(items):
        return "编号无效"
    removed = items.pop(index - 1)
    _save(data)
    return f"已删除兑换物品: {removed['name']}"


def redeem_item(group_id, user_id, nickname, index, get_user_score, deduct_user_score):
    """
    兑换物品
    get_user_score: 获取用户当前积分
    deduct_user_score: 扣除积分
    返回结果消息
    """
    data = _load()
    k = _key(group_id)
    items = data.get(k, [])
    if not items or index < 1 or index > len(items):
        return "编号无效，请发送 兑换 查看列表"
    item = items[index - 1]
    current_score = get_user_score(group_id, user_id)
    if current_score < item["price"]:
        return (
            f"积分不足！{item['name']} 需要 {item['price']} 积分，"
            f"你当前只有 {current_score} 积分"
        )
    new_score = deduct_user_score(group_id, user_id, item["price"])
    return (
        f"兑换成功！{nickname} 兑换了 {item['name']}\n"
        f"消耗 {item['price']} 积分，剩余 {new_score} 积分"
    )