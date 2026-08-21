from issuepack.context_renderer import render_compact_context
from issuepack.models import Message, MessageType


def test_compact_context_deduplicates_people_and_date():
    messages = [
        Message("msg-001", "春天@微信@微信联系人", "8/17 14:12:07", MessageType.TEXT, "这是之前提出的修改意见，还没改，请一并修改"),
        Message("msg-002", "王挺", "8/17 14:12:32", MessageType.TEXT, "好的，我统一修改"),
    ]
    context = render_compact_context("小程序修改", messages)
    assert context.startswith("# 小程序修改\n")
    assert "people:A=春天@微信@微信联系人;B=王挺" in context
    assert "date:8/17" in context
    assert "14:12:07 A> 这是之前提出的修改意见，还没改，请一并修改" in context
    assert "14:12:32 B> 好的，我统一修改" in context
    assert "8/17 14:12:07" not in context


def test_compact_context_merges_adjacent_same_sender_time_text_and_image():
    messages = [
        Message("msg-001", "春天", "8/17 14:21:00", MessageType.TEXT, "辛苦啦"),
        Message("msg-002", "春天", "8/17 14:21:00", MessageType.IMAGE, "图片"),
    ]
    context = render_compact_context("合作反馈", messages, {"msg-002": "assets/i1.png"})
    assert "14:21:00 A> 辛苦啦 [img:assets/i1.png]" in context
    assert context.count("14:21:00 A>") == 1


def test_compact_context_marks_date_changes_only_when_needed():
    messages = [
        Message("msg-001", "A", "8/17 23:59:00", MessageType.TEXT, "第一天"),
        Message("msg-002", "A", "8/18 00:01:00", MessageType.TEXT, "第二天"),
    ]
    context = render_compact_context("跨天", messages)
    assert "date:" not in context
    assert "@8/17\n23:59:00 A> 第一天" in context
    assert "@8/18\n00:01:00 A> 第二天" in context
