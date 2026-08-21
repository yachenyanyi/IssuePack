from issuepack.models import MessageType
from issuepack.parser import parse_wecom_text


def test_parses_sender_time_text_and_image_placeholder():
    text = """客户A 2026-08-21 10:21
首页这里再改一下

客户A 2026-08-21 10:22
图片

我 2026-08-21 10:23
是产品区域吗？
"""
    messages = parse_wecom_text(text)
    assert [message.type for message in messages] == [MessageType.TEXT, MessageType.IMAGE, MessageType.TEXT]
    assert messages[0].sender == "客户A"
    assert messages[0].content == "首页这里再改一下"
    assert messages[1].id == "msg-002"


def test_supports_same_day_time_headers():
    text = """客户A 10:21
第一句
客户A 10:22
文件
"""
    messages = parse_wecom_text(text)
    assert len(messages) == 2
    assert messages[1].type == MessageType.FILE
    assert messages[1].time == "10:22"


def test_unknown_format_is_preserved_as_text():
    messages = parse_wecom_text("一段没有头部格式的聊天原文")
    assert len(messages) == 1
    assert messages[0].sender == "Unknown"
    assert messages[0].content == "一段没有头部格式的聊天原文"
