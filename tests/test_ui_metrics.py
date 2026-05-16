from app.components.metrics_cards import render_progress_bar


class TestRenderProgressBar:
    def test_zero_total_shows_no_crawl_message(self, capsys):
        render_progress_bar(0, 0)

    def test_partial_progress(self, capsys):
        render_progress_bar(50, 200)

    def test_full_progress(self, capsys):
        render_progress_bar(200, 200)
