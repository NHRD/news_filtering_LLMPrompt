import datetime

try:
    from src import Article
except ImportError:
    # This is for standalone execution of the template if needed.
    from dataclasses import dataclass

    @dataclass
    class Article:
        title: str
        published: datetime.datetime
        source: str
        link: str


# --- ここに、テストしたい記事のデータを記述してください ---
# 各記事は辞書として定義し、以下のキーを含めてください。
# - "title": 記事のタイトル (str, 必須)
# - "source": 記事のソース名 (str, 必須)
# - "link": 記事のURL (str, 必須)
# - "published_offset_hours": 現在時刻からの公開時間のオフセット (int)。
#                             0: 現在時刻、1: 1時間前、-1: 1時間後 など。
#                             記事の新旧関係を簡単に設定するために使用します。
#                             この値が大きいほど、記事は古いと見なされます。
test_articles_data = [
    {
        "title": "速報：新型AIチップ、驚異の性能を発表",
        "source": "TechNews A",
        "link": "http://example.com/news1",
        "published_offset_hours": 0
    },
    {
        "title": "新型AI半導体、驚異的なパフォーマンスを公開",
        "source": "TechJournal B",
        "link": "http://example.com/news2_similar", # 異なるリンクだがタイトルは類似
        "published_offset_hours": 1 # 上の記事より古い
    },
    {
        "title": "速報：新型AIチップの性能が明らかに",
        "source": "Gadget Magazine C",
        "link": "http://example.com/news3_similar", # 異なるリンクだがタイトルは類似
        "published_offset_hours": 2 # さらに古い
    },
    {
        "title": "全く関係のないニュース記事 - その1",
        "source": "General News",
        "link": "http://example.com/other1",
        "published_offset_hours": 0
    },
    {
        "title": "全く関係のないニュース記事 - その2",
        "source": "Another Outlet",
        "link": "http://example.com/other2",
        "published_offset_hours": 0
    },
    # --- ここに、ご自身のテストシナリオに応じた記事データを追加してください ---
    # 例:
    # {
    #     "title": "あなたの追加記事タイトル1",
    #     "source": "あなたのソース1",
    #     "link": "http://example.com/your_link1",
    #     "published_offset_hours": 0
    # },
    # {
    #     "title": "あなたの追加記事タイトル2 (上記と類似)",
    #     "source": "あなたのソース2",
    #     "link": "http://example.com/your_link2",
    #     "published_offset_hours": 1
    # },
]

# --- この部分は変更しないでください。Article オブジェクトのリストを生成します ---
# published_offset_hours を使って、現在時刻からの相対的な公開日時を計算します。
current_time = datetime.datetime.now(datetime.timezone.utc)
generated_test_articles = [
    Article(
        title=data["title"],
        published=current_time - datetime.timedelta(hours=data.get("published_offset_hours", 0)),
        source=data["source"],
        link=data["link"]
    ) for data in test_articles_data
]
