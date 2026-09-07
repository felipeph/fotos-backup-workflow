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

def test_vertical_byte_progress_renderables():
    prog = create_byte_progress()
    t_id = prog.add_task("Ingestao Test", total=1024*1024*100, filename="teste.jpg")
    prog.update(t_id, advance=1024*1024*50)
    renderables = list(prog.get_renderables())
    assert len(renderables) == 1
    table = renderables[0]
    assert hasattr(table, "columns")

def test_vertical_item_progress_renderables():
    prog = create_item_progress(unit="arqs/s")
    t_id = prog.add_task("Contagem Test", total=20, filename="foto.jpg")
    prog.update(t_id, advance=10)
    renderables = list(prog.get_renderables())
    assert len(renderables) == 1
    table = renderables[0]
    assert hasattr(table, "columns")

def test_timed_confirm_prompt_noninteractive(monkeypatch):
    from src.notifier import timed_confirm_prompt

    # 1. User inputs "s"
    monkeypatch.setattr("builtins.input", lambda prompt="": "s")
    conf, timed_out = timed_confirm_prompt("Confirmar?", timeout_seconds=1, default=False)
    assert conf is True
    assert timed_out is False

    # 2. User inputs "n"
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    conf, timed_out = timed_confirm_prompt("Confirmar?", timeout_seconds=1, default=False)
    assert conf is False
    assert timed_out is False

    # 3. User inputs Enter (empty string) -> default value
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    conf, timed_out = timed_confirm_prompt("Confirmar?", timeout_seconds=1, default=False)
    assert conf is False
    assert timed_out is False

    # 4. EOFError (unattended without stdin) -> default and timed_out=True
    def mock_eof(prompt=""):
        raise EOFError()
    monkeypatch.setattr("builtins.input", mock_eof)
    conf, timed_out = timed_confirm_prompt("Confirmar?", timeout_seconds=1, default=False)
    assert conf is False
    assert timed_out is True

