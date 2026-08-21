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


def test_parses_real_wecom_style_header_and_image_file_uri():
    text = """客户A@微信@微信联系人 8/17 09:48:37
[image](file:///D:/WXWork/Cache/Image/2026-08/customer-shot.png)

客户A@微信@微信联系人 8/17 09:48:37
已经修复完成
"""
    messages = parse_wecom_text(text)
    assert len(messages) == 2
    assert messages[0].sender == "客户A@微信@微信联系人"
    assert messages[0].time == "8/17 09:48:37"
    assert messages[0].type == MessageType.IMAGE
    assert messages[0].source_asset_path is not None
    assert messages[0].source_asset_path.lower().endswith("customer-shot.png")
    assert messages[1].content == "已经修复完成"


def test_splits_text_and_inline_image_into_separate_timeline_events():
    text = """春天@微信@微信联系人 8/17 14:21:00
咱们第一次合作做小程序开发，确实有很多功能和细节需要多次沟通，反复修改，辛苦啦[image](file:///C:/Users/User/AppData/Local/Temp/reaction.png)
"""
    messages = parse_wecom_text(text)
    assert len(messages) == 2
    assert messages[0].type == MessageType.TEXT
    assert messages[0].content.endswith("辛苦啦")
    assert messages[1].type == MessageType.IMAGE
    assert messages[1].source_asset_path is not None
    assert messages[1].source_asset_path.lower().endswith("reaction.png")
    assert messages[0].sender == messages[1].sender
    assert messages[0].time == messages[1].time


def test_header_accepts_non_breaking_spaces_from_wecom_copy():
    text = "客户A@微信@微信联系人\u00a08/16\u00a021:35:55\n域名以前都有提供啊"
    messages = parse_wecom_text(text)
    assert len(messages) == 1
    assert messages[0].sender == "客户A@微信@微信联系人"
    assert messages[0].time == "8/16\u00a021:35:55"
    assert messages[0].content == "域名以前都有提供啊"


def test_unknown_format_is_preserved_as_text():
    messages = parse_wecom_text("一段没有头部格式的聊天原文")
    assert len(messages) == 1
    assert messages[0].sender == "Unknown"
    assert messages[0].content == "一段没有头部格式的聊天原文"
