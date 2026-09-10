from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import json
import os

PROJECTS_DIR = Path("projects")

@dataclass
class ProjectItem:
    original_path: str
    staging_path: str = ""
    sha256: str = ""
    file_size_bytes: int = 0
    category: str = ""  # astro_lua, timelapse_gopro, rajada, avulsa, video
    relative_dest_dir: str = ""
    target_filename: str = ""
    organized_path: str = ""
    extra_dest_dirs: list[str] = field(default_factory=list)
    extra_organized_paths: list[str] = field(default_factory=list)
    uploaded_at: str = ""
    upload_token: str = ""
    uploaded_path: str = ""
    cleaned_at: str = ""

@dataclass
class Project:
    project_id: str
    source_path: str
    current_stage: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    items: list[ProjectItem] = field(default_factory=list)
    upload_status: str = ""

    @property
    def project_dir(self) -> Path:
        return PROJECTS_DIR / self.project_id

    @property
    def plan_file(self) -> Path:
        return self.project_dir / "project_plan.json"

    def save(self):
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.now().isoformat()
        data = {
            "project_id": self.project_id,
            "source_path": self.source_path,
            "current_stage": self.current_stage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "upload_status": self.upload_status,
            "items": [asdict(it) for it in self.items],
        }
        temp_file = self.plan_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        temp_file.replace(self.plan_file)

def list_projects() -> list[str]:
    if not PROJECTS_DIR.exists():
        return []
    res = []
    for p in sorted(PROJECTS_DIR.iterdir(), reverse=True):
        if p.is_dir() and (p / "project_plan.json").exists():
            res.append(p.name)
    return res

def load_project(project_id: str) -> Project | None:
    plan_path = PROJECTS_DIR / project_id / "project_plan.json"
    if not plan_path.exists():
        return None
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = [ProjectItem(**it) for it in data.get("items", [])]
        return Project(
            project_id=data.get("project_id", project_id),
            source_path=data.get("source_path", ""),
            current_stage=data.get("current_stage", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            upload_status=data.get("upload_status", ""),
            items=items,
        )
    except Exception as e:
        print(f"[ERRO] Falha ao carregar projeto {project_id}: {e}")
        return None

def create_project(project_id: str, source_path: str) -> Project:
    proj = Project(
        project_id=project_id,
        source_path=source_path,
        current_stage=0,
    )
    proj.save()
    return proj
