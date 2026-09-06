import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.project import Project, ProjectItem, create_project, load_project
from src.config import PipelineConfig
from src.stages.stage1_ingest import run_stage1
from src.stages.stage2_plan import run_stage2
from src.stages.stage3_organize import run_stage3
from src.stages.stage4_upload import run_stage4
from src.stages.stage5_move_uploaded import run_stage5
from src.stages.stage7_cleanup import run_stage7
from src.metadata_extractor import MediaMetadata

def test_project_lifecycle_and_state_persistence():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        projects_dir = root / "projects"
        projects_dir.mkdir()

        # Monkeypatch projects dir
        import src.project
        old_dir = src.project.PROJECTS_DIR
        src.project.PROJECTS_DIR = projects_dir

        try:
            p = create_project("test_session_01", "E:/DCIM")
            assert p.current_stage == 0
            assert p.plan_file.exists()

            p.current_stage = 1
            p.items.append(ProjectItem(original_path="E:/DCIM/IMG1.JPG", sha256="abc123"))
            p.save()

            loaded = load_project("test_session_01")
            assert loaded is not None
            assert loaded.current_stage == 1
            assert len(loaded.items) == 1
            assert loaded.items[0].sha256 == "abc123"
        finally:
            src.project.PROJECTS_DIR = old_dir

def test_stages_1_to_5_and_7_complete_flow(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sd_card = root / "sd_card"
        sd_card.mkdir()
        ssd_root = root / "ssd"
        ssd_root.mkdir()

        # Create 2 sample photos on SD card
        f1 = sd_card / "IMG_0001.JPG"
        f1.write_bytes(b"content_photo_1")
        f2 = sd_card / "IMG_0002.JPG"
        f2.write_bytes(b"content_photo_2")

        cfg = PipelineConfig(
            destination_root=str(ssd_root),
            staging_dir=str(ssd_root / "staging"),
            uploaded_dir=str(ssd_root / "UPLOADED"),
        )

        import src.project
        old_dir = src.project.PROJECTS_DIR
        src.project.PROJECTS_DIR = root / "projects"
        try:
            proj = create_project("sessao_teste", str(sd_card))

            # --- ETAPA 1: Ingestão SD -> SSD com auto_delete_sd=True ---
            ok1 = run_stage1(proj, cfg, auto_delete_sd=True)
            assert ok1 is True
            assert proj.current_stage == 1
            assert len(proj.items) == 2
            # SD files should be erased now
            assert not f1.exists()
            assert not f2.exists()
            # Staging files should exist
            assert Path(proj.items[0].staging_path).exists()

            # --- ETAPA 2: Planejamento ---
            ok2 = run_stage2(proj, cfg)
            assert ok2 is True
            assert proj.current_stage == 2
            assert proj.items[0].target_filename != ""

            # --- ETAPA 3: Organização Física ---
            ok3 = run_stage3(proj, cfg)
            assert ok3 is True
            assert proj.current_stage == 3
            assert Path(proj.items[0].organized_path).exists()

            # --- ETAPA 4: Teste de Recusa (ainda não subiu) ---
            monkeypatch.setattr("builtins.input", lambda prompt="": "n")
            ok4_declined = run_stage4(proj, cfg, auto_confirm=False)
            assert ok4_declined is False
            assert proj.current_stage == 3
            assert proj.items[0].uploaded_at == ""

            # --- ETAPA 4: Teste de Confirmação (upload web feito) ---
            ok4_confirmed = run_stage4(proj, cfg, auto_confirm=True)
            assert ok4_confirmed is True
            assert proj.current_stage == 4
            assert proj.items[0].uploaded_at != ""
            assert proj.items[1].uploaded_at != ""

            # --- ETAPA 5: Transferência para UPLOADED ---
            ok5 = run_stage5(proj, cfg)
            assert ok5 is True
            assert proj.current_stage == 5
            assert Path(proj.items[0].uploaded_path).exists()
            assert "UPLOADED" in proj.items[0].uploaded_path

            # --- ETAPA 7: Limpeza pós-upload no SSD ---
            ok7 = run_stage7(proj, cfg, auto_confirm=True)
            assert ok7 is True
            assert proj.current_stage == 7
            assert not Path(proj.items[0].uploaded_path).exists()

        finally:
            src.project.PROJECTS_DIR = old_dir
