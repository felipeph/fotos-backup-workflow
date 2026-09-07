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

        # Create 2 sample photos and 1 video on SD card
        f1 = sd_card / "IMG_0001.JPG"
        f1.write_bytes(b"content_photo_1")
        f2 = sd_card / "IMG_0002.JPG"
        f2.write_bytes(b"content_photo_2")
        v1 = sd_card / "MVI_0001.MP4"
        v1.write_bytes(b"content_video_1")

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
            assert len(proj.items) == 3
            # SD files should be erased now
            assert not f1.exists()
            assert not f2.exists()
            assert not v1.exists()
            # Staging files should exist
            assert Path(proj.items[0].staging_path).exists()

            # --- ETAPA 2: Planejamento ---
            ok2 = run_stage2(proj, cfg)
            assert ok2 is True
            assert proj.current_stage == 2
            assert proj.items[0].target_filename != ""
            video_items = [it for it in proj.items if it.category == "video"]
            assert len(video_items) == 1
            assert "videos" in video_items[0].relative_dest_dir

            # --- ETAPA 3: Organização Física ---
            ok3 = run_stage3(proj, cfg)
            assert ok3 is True
            assert proj.current_stage == 3
            assert Path(proj.items[0].organized_path).exists()
            assert Path(video_items[0].organized_path).exists()

            # --- ETAPA 4: Teste de Recusa (ainda não subiu) ---
            monkeypatch.setattr("builtins.input", lambda prompt="": "n")
            ok4_declined = run_stage4(proj, cfg, auto_confirm=False)
            assert ok4_declined is False
            assert proj.current_stage == 3
            assert proj.items[0].uploaded_at == ""
            assert video_items[0].uploaded_at == ""

            # --- ETAPA 4: Teste de Confirmação (upload web feito) ---
            ok4_confirmed = run_stage4(proj, cfg, auto_confirm=True)
            assert ok4_confirmed is True
            assert proj.current_stage == 4
            assert proj.items[0].uploaded_at != ""
            assert proj.items[1].uploaded_at != ""
            assert video_items[0].uploaded_at != ""

            # --- ETAPA 5: Transferência para UPLOADED ---
            ok5 = run_stage5(proj, cfg)
            assert ok5 is True
            assert proj.current_stage == 5
            assert Path(proj.items[0].uploaded_path).exists()
            assert "UPLOADED" in proj.items[0].uploaded_path
            assert Path(video_items[0].uploaded_path).exists()
            assert "UPLOADED" in video_items[0].uploaded_path
            assert "videos" in video_items[0].uploaded_path

            # --- ETAPA 7: Limpeza pós-upload no SSD ---
            ok7 = run_stage7(proj, cfg, auto_confirm=True)
            assert ok7 is True
            assert proj.current_stage == 7
            assert not Path(proj.items[0].uploaded_path).exists()
            assert not Path(video_items[0].uploaded_path).exists()

        finally:
            src.project.PROJECTS_DIR = old_dir

def test_stage1_concurrent_ingestion_and_resume(monkeypatch):
    import hashlib
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sd_card = root / "sd_card"
        sd_card.mkdir()
        ssd_root = root / "ssd"
        ssd_root.mkdir()

        # Create 12 sample files
        expected_hashes = {}
        for i in range(12):
            f = sd_card / f"GOPR{i:04d}.JPG"
            content = f"sample_photo_content_number_{i}".encode("utf-8")
            f.write_bytes(content)
            expected_hashes[str(f.resolve())] = hashlib.sha256(content).hexdigest()

        cfg = PipelineConfig(
            destination_root=str(ssd_root),
            staging_dir=str(ssd_root / "staging"),
            uploaded_dir=str(ssd_root / "UPLOADED"),
            ingest_workers=4,
            checkpoint_interval_items=3,
            checkpoint_interval_seconds=1.0,
        )

        import src.project
        old_dir = src.project.PROJECTS_DIR
        src.project.PROJECTS_DIR = root / "projects"
        try:
            proj = create_project("test_concurrent", str(sd_card))

            # Run Stage 1 with 4 workers
            ok = run_stage1(proj, cfg, auto_delete_sd=False)
            assert ok is True
            assert proj.current_stage == 1
            assert len(proj.items) == 12

            # Verify each item's SHA256 and staging file
            for it in proj.items:
                assert it.original_path in expected_hashes
                assert it.sha256 == expected_hashes[it.original_path]
                assert Path(it.staging_path).exists()
                assert Path(it.staging_path).stat().st_size == it.file_size_bytes

            # Verify reload from disk
            reloaded = load_project("test_concurrent")
            assert reloaded is not None
            assert len(reloaded.items) == 12

            # Run Stage 1 again to test Resume (all 12 files should be resume-ok)
            ok_resume = run_stage1(reloaded, cfg, auto_delete_sd=True)
            assert ok_resume is True
            assert len(reloaded.items) == 12

            # Now SD files should have been deleted
            for f in sd_card.glob("*.JPG"):
                assert False, f"File {f} was not deleted from SD"
        finally:
            src.project.PROJECTS_DIR = old_dir

def test_video_upload_confirmation_and_transfer_to_uploaded():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ssd_root = root / "ssd"
        dest_bib = ssd_root / "Biblioteca" / "2026" / "08" / "08" / "videos"
        dest_bib.mkdir(parents=True)
        vid_file = dest_bib / "2026-08-08_test_video.mp4"
        vid_file.write_bytes(b"dummy_video_bytes_12345")

        cfg = PipelineConfig(
            destination_root=str(ssd_root),
            staging_dir=str(ssd_root / "staging"),
            uploaded_dir=str(ssd_root / "UPLOADED"),
        )

        import src.project
        old_dir = src.project.PROJECTS_DIR
        src.project.PROJECTS_DIR = root / "projects"
        try:
            proj = create_project("test_video_session", str(root / "source"))
            proj.current_stage = 3

            # Add an already uploaded photo
            proj.items.append(ProjectItem(
                original_path="photo1.jpg",
                sha256="hash1",
                file_size_bytes=100,
                category="avulsa",
                relative_dest_dir="Biblioteca/2026/08/08/avulsas",
                target_filename="photo1.jpg",
                organized_path=str(ssd_root / "Biblioteca" / "2026" / "08" / "08" / "avulsas" / "photo1.jpg"),
                uploaded_at="2026-09-07T08:00:00",
                uploaded_path=str(ssd_root / "UPLOADED" / "Biblioteca" / "2026" / "08" / "08" / "avulsas" / "photo1.jpg"),
            ))

            # Add a video that was organized but not yet marked uploaded
            vid_item = ProjectItem(
                original_path="test_video.mp4",
                sha256="hash2",
                file_size_bytes=len(b"dummy_video_bytes_12345"),
                category="video",
                relative_dest_dir="Biblioteca/2026/08/08/videos",
                target_filename="2026-08-08_test_video.mp4",
                organized_path=str(vid_file.resolve()),
                uploaded_at="",
                uploaded_path="",
            )
            proj.items.append(vid_item)
            proj.save()

            # Run Stage 4: should identify the pending video and mark it uploaded
            ok4 = run_stage4(proj, cfg, auto_confirm=True)
            assert ok4 is True
            assert vid_item.uploaded_at != ""

            # Run Stage 5: should move the video to UPLOADED
            ok5 = run_stage5(proj, cfg)
            assert ok5 is True
            assert vid_item.uploaded_path != ""
            assert Path(vid_item.uploaded_path).exists()
            assert "UPLOADED" in vid_item.uploaded_path
            assert "videos" in vid_item.uploaded_path
            assert not vid_file.exists()

            # Run Stage 7: should clean up the video from UPLOADED
            ok7 = run_stage7(proj, cfg, auto_confirm=True)
            assert ok7 is True
            assert vid_item.cleaned_at != ""
            assert not Path(vid_item.uploaded_path).exists()
        finally:
            src.project.PROJECTS_DIR = old_dir
