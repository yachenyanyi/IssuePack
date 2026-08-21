from issuepack.clipboard import enrich_plain_text_with_html_assets


def test_enriches_plain_image_placeholders_from_rich_clipboard_html():
    plain = """客户A 8/17 09:48:37
[图片]

客户A 8/17 13:21:57
图片
"""
    rich = """
    <div>客户A 8/17 09:48:37</div>
    <div><img src="file:///D:/WXWork/Cache/Image/first.png"></div>
    <div>客户A 8/17 13:21:57</div>
    <div><img src="file:///D:/WXWork/Cache/Image/second.jpg"></div>
    """

    enriched = enrich_plain_text_with_html_assets(plain, rich)

    assert "[image](file:///D:/WXWork/Cache/Image/first.png)" in enriched
    assert "[image](file:///D:/WXWork/Cache/Image/second.jpg)" in enriched
    assert enriched.index("first.png") < enriched.index("second.jpg")


def test_does_not_overwrite_text_that_already_contains_file_urls():
    plain = "[image](file:///D:/WXWork/Cache/Image/already.png)"
    rich = '<img src="file:///D:/WXWork/Cache/Image/other.png">'
    assert enrich_plain_text_with_html_assets(plain, rich) == plain
