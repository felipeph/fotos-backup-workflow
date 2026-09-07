from dataclasses import dataclass, field
from pathlib import Path
import json
import os

@dataclass
class NamingConfig:
    photo_pattern: str = "{date}_{time}_{camera}_{focal}_{aperture}_{shutter}_{iso}_{original}.{ext}"
    video_pattern: str = "{date}_{time}_{camera}_{resolution}_{fps}_{duration}_{original}.{ext}"

@dataclass
class NotificationConfig:
    toast_enabled: bool = True
    sound_enabled: bool = True
    ntfy_topic: str = "fotos-backup-felipe"

@dataclass
class PipelineConfig:
    destination_root: str = "D:/Fotos_Organizadas"
    staging_dir: str = "D:/Fotos_Organizadas/staging"
    uploaded_dir: str = "D:/Fotos_Organizadas/UPLOADED"
    timelapse_studio_path: str = "C:/code/timelapse/timelapse_studio.py"
    burst_interval_seconds: float = 3.0
    moon_zoom_threshold_mm: float = 1200.0
    countdown_seconds: int = 180
    ingest_workers: int = 4
    checkpoint_interval_items: int = 200
    checkpoint_interval_seconds: float = 10.0
    naming: NamingConfig = field(default_factory=NamingConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)

    @property
    def destination_path(self) -> Path:
        return Path(self.destination_root)

    @property
    def staging_path(self) -> Path:
        return Path(self.staging_dir)

    @property
    def uploaded_path(self) -> Path:
        return Path(self.uploaded_dir)

    @property
    def biblioteca_path(self) -> Path:
        return self.destination_path / "Biblioteca"

    @property
    def astro_lua_path(self) -> Path:
        return self.destination_path / "Astrofotografia" / "Lua"

    @property
    def timelapses_path(self) -> Path:
        return self.destination_path / "Timelapses" / "GoPro"

def load_config(config_path: Path | str = "config.json") -> PipelineConfig:
    path = Path(config_path)
    if not path.exists():
        example_path = Path("config.example.json")
        if example_path.exists():
            path = example_path
        else:
            return PipelineConfig()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        naming_data = data.get("naming", {})
        naming = NamingConfig(
            photo_pattern=naming_data.get("photo_pattern", NamingConfig.photo_pattern),
            video_pattern=naming_data.get("video_pattern", NamingConfig.video_pattern),
        )

        notif_data = data.get("notifications", {})
        notifications = NotificationConfig(
            toast_enabled=notif_data.get("toast_enabled", NotificationConfig.toast_enabled),
            sound_enabled=notif_data.get("sound_enabled", NotificationConfig.sound_enabled),
            ntfy_topic=notif_data.get("ntfy_topic", NotificationConfig.ntfy_topic),
        )

        dest_root = data.get("destination_root", "D:/Fotos_Organizadas")
        staging_dir = data.get("staging_dir", f"{dest_root}/staging")
        uploaded_dir = data.get("uploaded_dir", f"{dest_root}/UPLOADED")
        tl_path = data.get("timelapse_studio_path", data.get("gopro_script_path", "C:/code/timelapse/timelapse_studio.py"))

        return PipelineConfig(
            destination_root=dest_root,
            staging_dir=staging_dir,
            uploaded_dir=uploaded_dir,
            timelapse_studio_path=tl_path,
            burst_interval_seconds=float(data.get("burst_interval_seconds", 3.0)),
            moon_zoom_threshold_mm=float(data.get("moon_zoom_threshold_mm", 1200.0)),
            countdown_seconds=int(data.get("countdown_seconds", 180)),
            ingest_workers=int(data.get("ingest_workers", 4)),
            checkpoint_interval_items=int(data.get("checkpoint_interval_items", 200)),
            checkpoint_interval_seconds=float(data.get("checkpoint_interval_seconds", 10.0)),
            naming=naming,
            notifications=notifications,
        )
    except Exception as e:
        print(f"[WARN] Erro ao carregar {path}, usando valores padrão: {e}")
        return PipelineConfig()

def save_config(config: PipelineConfig, config_path: Path | str = "config.json"):
    path = Path(config_path)
    data = {
        "destination_root": config.destination_root,
        "staging_dir": config.staging_dir,
        "uploaded_dir": config.uploaded_dir,
        "timelapse_studio_path": config.timelapse_studio_path,
        "burst_interval_seconds": config.burst_interval_seconds,
        "moon_zoom_threshold_mm": config.moon_zoom_threshold_mm,
        "countdown_seconds": config.countdown_seconds,
        "ingest_workers": config.ingest_workers,
        "checkpoint_interval_items": config.checkpoint_interval_items,
        "checkpoint_interval_seconds": config.checkpoint_interval_seconds,
        "naming": {
            "photo_pattern": config.naming.photo_pattern,
            "video_pattern": config.naming.video_pattern,
        },
        "notifications": {
            "toast_enabled": config.notifications.toast_enabled,
            "sound_enabled": config.notifications.sound_enabled,
            "ntfy_topic": config.notifications.ntfy_topic,
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
