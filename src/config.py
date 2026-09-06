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
class GooglePhotosConfig:
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"
    auto_upload_after_countdown: bool = True
    album_name: str = ""

@dataclass
class PipelineConfig:
    destination_root: str = "D:/Fotos_Organizadas"
    gopro_script_path: str = ""
    burst_interval_seconds: float = 3.0
    moon_zoom_threshold_mm: float = 1200.0
    countdown_seconds: int = 180
    naming: NamingConfig = field(default_factory=NamingConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    google_photos: GooglePhotosConfig = field(default_factory=GooglePhotosConfig)

    @property
    def destination_path(self) -> Path:
        return Path(self.destination_root)

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

        gp_data = data.get("google_photos", {})
        google_photos = GooglePhotosConfig(
            credentials_file=gp_data.get("credentials_file", GooglePhotosConfig.credentials_file),
            token_file=gp_data.get("token_file", GooglePhotosConfig.token_file),
            auto_upload_after_countdown=gp_data.get("auto_upload_after_countdown", GooglePhotosConfig.auto_upload_after_countdown),
            album_name=gp_data.get("album_name", GooglePhotosConfig.album_name),
        )

        return PipelineConfig(
            destination_root=data.get("destination_root", "D:/Fotos_Organizadas"),
            gopro_script_path=data.get("gopro_script_path", ""),
            burst_interval_seconds=float(data.get("burst_interval_seconds", 3.0)),
            moon_zoom_threshold_mm=float(data.get("moon_zoom_threshold_mm", 1200.0)),
            countdown_seconds=int(data.get("countdown_seconds", 180)),
            naming=naming,
            notifications=notifications,
            google_photos=google_photos,
        )
    except Exception as e:
        print(f"[WARN] Erro ao carregar {path}, usando valores padrão: {e}")
        return PipelineConfig()

def save_config(config: PipelineConfig, config_path: Path | str = "config.json"):
    path = Path(config_path)
    data = {
        "destination_root": config.destination_root,
        "gopro_script_path": config.gopro_script_path,
        "burst_interval_seconds": config.burst_interval_seconds,
        "moon_zoom_threshold_mm": config.moon_zoom_threshold_mm,
        "countdown_seconds": config.countdown_seconds,
        "naming": {
            "photo_pattern": config.naming.photo_pattern,
            "video_pattern": config.naming.video_pattern,
        },
        "notifications": {
            "toast_enabled": config.notifications.toast_enabled,
            "sound_enabled": config.notifications.sound_enabled,
            "ntfy_topic": config.notifications.ntfy_topic,
        },
        "google_photos": {
            "credentials_file": config.google_photos.credentials_file,
            "token_file": config.google_photos.token_file,
            "auto_upload_after_countdown": config.google_photos.auto_upload_after_countdown,
            "album_name": config.google_photos.album_name,
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
