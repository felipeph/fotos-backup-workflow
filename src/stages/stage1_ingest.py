import sys
import shutil
import os
import time
import hashlib
from pathlib import Path
from datetime import datetime

from src.project import Project, ProjectItem
from src.config import PipelineConfig
from src.storage import compute_sha256
from src.metadata_extractor import PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from src.telemetry import create_byte_progress, print_stage_header, print_stage_summary

def run_stage1(
    project: Project,
    config: PipelineConfig,
    auto_delete_sd: bool = False
) -> bool:
    """
    Etapa 1: Cópia dos arquivos do SD para o SSD com validação SHA-256 arquivo por arquivo.
    Somente após 100% dos arquivos verificados com sucesso, os arquivos do SD são apagados.
    """
    source_dir = Path(project.source_path)
    if not source_dir.exists():
        print(f"[ERRO] Origem não encontrada: {source_dir}")
        return False

    staging_dir = config.staging_path / project.project_id / "raw"
    staging_dir.mkdir(parents=True, exist_ok=True)

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage1_ingestion.log"

    valid_exts = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS
    media_files: list[Path] = []
    for root, _, files in os.walk(source_dir):
        for f in files:
            if f.startswith("."):
                continue
            p = Path(root) / f
            if p.suffix.lower() in valid_exts:
                media_files.append(p)

    if not media_files:
        print(f"[AVISO] Nenhum arquivo de mídia encontrado em {source_dir}.")
        return False

    total_bytes = 0
    file_sizes = {}
    for p in media_files:
        sz = p.stat().st_size
        file_sizes[p] = sz
        total_bytes += sz

    print_stage_header("ETAPA 1: INGESTÃO E VALIDAÇÃO (SD -> SSD)", total_items=len(media_files), total_bytes=total_bytes)
    start_time = datetime.now()

    verified_items: list[ProjectItem] = []
    verified_map: dict[str, ProjectItem] = {it.original_path: it for it in project.items if it.sha256}
    errors: list[str] = []

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 1: {datetime.now().isoformat()} ===\n")
        log.write(f"Origem: {source_dir} | Destino: {staging_dir} | Total: {len(media_files)} arqs ({total_bytes} bytes)\n\n")

        with create_byte_progress() as progress:
            task_id = progress.add_task("[bold blue]Ingestão SD -> SSD", total=total_bytes)

            for idx, src_p in enumerate(media_files, start=1):
                rel_path = src_p.relative_to(source_dir)
                target_p = staging_dir / rel_path
                target_p.parent.mkdir(parents=True, exist_ok=True)
                src_size = file_sizes[src_p]
                orig_key = str(src_p.resolve())
                progress.update(task_id, filename=src_p.name)

                # Check if already verified in a previous interrupted run (Resume)
                if orig_key in verified_map and target_p.exists() and target_p.stat().st_size == src_size:
                    prev_item = verified_map[orig_key]
                    verified_items.append(prev_item)
                    progress.update(task_id, advance=src_size)
                    log.write(f"[{idx}/{len(media_files)}] RESUME-OK | {rel_path} ({src_size} bytes)\n")
                    continue

                # Streaming copy with on-the-fly SHA-256 calculation
                hasher = hashlib.sha256()
                chunk_size = 4 * 1024 * 1024  # 4MB buffer

                try:
                    with open(src_p, "rb") as fsrc, open(target_p, "wb") as fdst:
                        while True:
                            buf = fsrc.read(chunk_size)
                            if not buf:
                                break
                            hasher.update(buf)
                            fdst.write(buf)
                            progress.update(task_id, advance=len(buf))

                    shutil.copystat(src_p, target_p)
                    src_sha = hasher.hexdigest()
                    dest_sha = compute_sha256(target_p)
                    dest_size = target_p.stat().st_size

                    if src_sha == dest_sha and src_size == dest_size:
                        log_line = f"[{idx}/{len(media_files)}] OK | SHA256:{src_sha} | {rel_path} ({src_size} bytes)"
                        log.write(log_line + "\n")
                        item = ProjectItem(
                            original_path=orig_key,
                            staging_path=str(target_p.resolve()),
                            sha256=src_sha,
                            file_size_bytes=src_size,
                        )
                        verified_items.append(item)
                        verified_map[orig_key] = item
                    else:
                        err_msg = f"FALHA DE INTEGRIDADE: {src_p} ({src_sha}) != {target_p} ({dest_sha})"
                        errors.append(err_msg)
                        log.write(f"[ERRO] {err_msg}\n")
                except Exception as ex:
                    err_msg = f"FALHA DE I/O AO COPIAR {src_p}: {ex}"
                    errors.append(err_msg)
                    log.write(f"[ERRO] {err_msg}\n")

                # Checkpoint persistence every 25 files
                if idx % 25 == 0:
                    project.items = verified_items
                    project.save()

    # Final checkpoint of Stage 1
    project.items = verified_items
    if not errors and len(verified_items) == len(media_files):
        project.current_stage = max(project.current_stage, 1)
    project.save()

    print_stage_summary(
        "Etapa 1 (Ingestão SD -> SSD)",
        start_time,
        success=(not errors and len(verified_items) == len(media_files)),
        items_done=len(verified_items),
        bytes_done=sum(it.file_size_bytes for it in verified_items),
    )

    # Step: Delete files from SD card
    delete_confirmed = auto_delete_sd
    if not auto_delete_sd:
        print("\n⚠️  [ATENÇÃO - PERDA DE DADOS NO CARTÃO SD]")
        print("100% dos arquivos foram verificados com sucesso no seu SSD.")
        resp = input("Deseja apagar os arquivos originais do cartão SD agora? (s/N): ").strip().lower()
        delete_confirmed = (resp == "s")

    if delete_confirmed:
        print("\n🗑️  Apagando arquivos verificados do cartão SD...")
        with open(log_file, "a", encoding="utf-8") as log:
            log.write("\n=== REMOÇÃO SEGURA NO CARTÃO SD ===\n")
            for it in verified_items:
                orig = Path(it.original_path)
                try:
                    if orig.exists():
                        orig.unlink()
                        log.write(f"DELETADO NO SD: {orig}\n")
                except Exception as e:
                    log.write(f"ERRO AO DELETAR {orig}: {e}\n")
        print("✅ Limpeza do cartão SD concluída.")
    else:
        print("ℹ️  Arquivos no cartão SD foram mantidos intactos.")

    return True
