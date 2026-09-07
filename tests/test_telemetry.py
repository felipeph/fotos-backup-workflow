from datetime import datetime, timedelta
from rich.progress import Task
from src.telemetry import (
    EstimatedEndTimeColumn,
    SpeedPerSecondColumn,
    CurrentFileColumn,
    create_byte_progress,
    create_item_progress,
    print_stage_header,
    print_stage_summary,
)

def test_estimated_end_time_column():
    col = EstimatedEndTimeColumn()
    
    class DummyTask:
        time_remaining = None
    
    # When remaining is None
    res = col.render(DummyTask())
    assert "--:--:--" in res.plain

    # When remaining is 120 seconds
    DummyTask.time_remaining = 120
    res = col.render(DummyTask())
    assert "Término:" in res.plain
    assert "--:--:--" not in res.plain

def test_speed_per_second_column():
    col = SpeedPerSecondColumn(unit="arqs/s")

    class DummyTask:
        speed = None

    res = col.render(DummyTask())
    assert "--.- arqs/s" in res.plain

    DummyTask.speed = 15.5
    res = col.render(DummyTask())
    assert "15.5 arqs/s" in res.plain

def test_create_progress_builders():
    byte_prog = create_byte_progress()
    assert byte_prog is not None

    item_prog = create_item_progress(unit="arqs/s")
    assert item_prog is not None

def test_print_headers_and_summaries(capsys):
    # Ensure they run without throwing exceptions
    print_stage_header("TEST STAGE", total_items=10, total_bytes=1024*1024*50)
    print_stage_summary("TEST STAGE", datetime.now() - timedelta(seconds=5), success=True, items_done=10, bytes_done=1024*1024*50)

def test_current_file_column():
    col = CurrentFileColumn(max_width=20)
    class DummyTask:
        fields = {}

    t = DummyTask()
    assert col.render(t).plain.strip() == ""

    t.fields = {"filename": "foto1.jpg"}
    assert "foto1.jpg" in col.render(t).plain

    t.fields = {"filename": "a_very_long_file_name_that_should_be_truncated.jpg"}
    res = col.render(t).plain
    assert "..." in res
    assert len(res.strip()) <= 24
