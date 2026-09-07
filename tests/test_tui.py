from unittest.mock import patch
from pathlib import Path
from src.config import PipelineConfig
from src.project import Project, create_project
from src.tui import initial_project_prompt, prompt_create_new_project

def test_initial_project_prompt_resume(tmp_path, monkeypatch):
    # Setup mock projects directory
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    monkeypatch.setattr("src.project.PROJECTS_DIR", projects_dir)
    monkeypatch.setattr("src.tui.clear_screen", lambda: None)

    p1 = create_project("test_sessao_01", "E:\\DCIM")
    
    config = PipelineConfig()
    # Mock user pressing ENTER ("") to resume
    with patch("builtins.input", side_effect=[""]):
        proj = initial_project_prompt(config)
        assert proj is not None
        assert proj.project_id == "test_sessao_01"

def test_initial_project_prompt_exit(tmp_path, monkeypatch):
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    monkeypatch.setattr("src.project.PROJECTS_DIR", projects_dir)
    monkeypatch.setattr("src.tui.clear_screen", lambda: None)

    create_project("test_sessao_01", "E:\\DCIM")

    config = PipelineConfig()
    # Mock user typing "0" to exit
    with patch("builtins.input", side_effect=["0"]):
        proj = initial_project_prompt(config)
        assert proj is None

def test_prompt_create_new_project(tmp_path, monkeypatch):
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    monkeypatch.setattr("src.project.PROJECTS_DIR", projects_dir)
    monkeypatch.setattr("src.tui.clear_screen", lambda: None)

    config = PipelineConfig()
    # Inputs: name, source, enter to continue
    with patch("builtins.input", side_effect=["meu_novo_projeto", "C:\\fotos", ""]):
        proj = prompt_create_new_project(config)
        assert proj is not None
        assert proj.project_id == "meu_novo_projeto"
        assert proj.source_path == "C:\\fotos"
