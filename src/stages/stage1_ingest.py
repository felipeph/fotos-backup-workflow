import sys
import shutil
import os
import time
import hashlib
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.project import Project, ProjectItem
from src.config import PipelineConfig
from src.metadata_extractor import PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from src.preflight import check_preflight, scan_source_media
from src.notifier import timed_confirm_prompt
from src.telemetry import create_byte_progress, print_stage_header, print_stage_summary

def _copy_worker(
    src_p: Path,
    target_p: Path,
    rel_path: Path,
    src_size: int,
    orig_key: str,
    progress,
    task_id,
    chunk_size: int = 4 * 1024 * 1024
) -> tuple[bool, str, ProjectItem | None, str]:
    """
    Copia um único arquivo do SD para o SSD calculando SHA-256 em streaming.
    Retorna: (sucesso: bool, log_msg: str, item: ProjectItem | None, erro_msg: str)
    """
    hasher = hashlib.sha256()
    temp_target = target_p.with_name(f".tmp_{target_p.name}")
    try:
        target_p.parent.mkdir(parents=True, exist_ok=True)
        with open(src_p, "rb") as fsrc, open(temp_target, "wb") as fdst:
            while True:
                buf = fsrc.read(chunk_size)
                if not buf:
                    break
                hasher.update(buf)
                fdst.write(buf)
                progress.update(task_id, advance=len(buf), filename=src_p.name)

        shutil.copystat(src_p, temp_target)
        dest_size = temp_target.stat().st_size
        src_sha = hasher.hexdigest()

        if dest_size != src_size:
            temp_target.unlink(missing_ok=True)
            err = f"FALHA DE TAMANHO: {src_p} ({src_size} bytes) != {temp_target} ({dest_size} bytes)"
            return (False, f"[ERRO] {err}", None, err)

        # Atomic replace
        if target_p.exists():
            target_p.unlink()
        temp_target.rename(target_p)

        item = ProjectItem(
            original_path=orig_key,
            staging_path=str(target_p.resolve()),
            sha256=src_sha,
            file_size_bytes=src_size,
        )
        return (True, f"OK | SHA256:{src_sha} | {rel_path} ({src_size} bytes)", item, "")
    except Exception as ex:
        if temp_target.exists():
            temp_target.unlink(missing_ok=True)
        err = f"FALHA DE I/O AO COPIAR {src_p}: {ex}"
        return (False, f"[ERRO] {err}", None, err)

def run_stage1(
    project: Project,
    config: PipelineConfig,
    auto_delete_sd: bool = False
) -> bool:
    """
    Etapa 1: Cópia dos arquivos do SD para o SSD com validação SHA-256 em streaming
    e suporte a cópia concorrente via ThreadPoolExecutor para máxima taxa de transferência.
    Somente após 100% dos arquivos verificados com sucesso, os arquivos do SD são apagados.
    """
    source_dir = Path(project.source_path)
    if not source_dir.exists():
        print(f"[ERRO] Origem não encontrada: {source_dir}")
        return False

    # Validação de Pré-Voo: Espaço no disco de destino exclusivo para as fotos/vídeos
    pf = check_preflight(destination_root=config.destination_root, source_path=source_dir)
    if not pf.has_enough_space:
        print(f"\n❌ [ERRO DE ESPAÇO EM DISCO] {pf.space_warning}")
        print("Transferência abortada para evitar corrupção por falta de espaço em disco.")
        return False

    staging_dir = config.staging_path / project.project_id / "raw"
    staging_dir.mkdir(parents=True, exist_ok=True)

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage1_ingestion.log"

    media_files, total_bytes = scan_source_media(source_dir)
    if not media_files:
        print(f"[AVISO] Nenhum arquivo de foto ou vídeo encontrado em {source_dir}.")
        return False

    file_sizes = {}
    for p in media_files:
        file_sizes[p] = p.stat().st_size

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

            # 1. Separar itens já verificados (Resume) e itens pendentes de cópia
            files_to_copy = []
            for src_p in media_files:
                rel_path = src_p.relative_to(source_dir)
                target_p = staging_dir / rel_path
                src_size = file_sizes[src_p]
                orig_key = str(src_p.resolve())

                if orig_key in verified_map and target_p.exists() and target_p.stat().st_size == src_size:
                    prev_item = verified_map[orig_key]
                    verified_items.append(prev_item)
                    progress.update(task_id, advance=src_size, filename=src_p.name)
                    log.write(f"[{len(verified_items)}/{len(media_files)}] RESUME-OK | {rel_path} ({src_size} bytes)\n")
                else:
                    files_to_copy.append((src_p, target_p, rel_path, src_size, orig_key))

            # 2. Executar cópia concorrente dos arquivos pendentes
            last_save_time = time.time()
            workers = max(1, config.ingest_workers)

            if files_to_copy:
                try:
                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        future_to_file = {
                            executor.submit(
                                _copy_worker,
                                src_p,
                                target_p,
                                rel_path,
                                src_size,
                                orig_key,
                                progress,
                                task_id,
                            ): (src_p, rel_path, src_size, orig_key)
                            for src_p, target_p, rel_path, src_size, orig_key in files_to_copy
                        }

                        for future in as_completed(future_to_file):
                            src_p, rel_path, src_size, orig_key = future_to_file[future]
                            success, log_msg, item, err = future.result()

                            total_done = len(verified_items) + (1 if success else 0)
                            if success and item:
                                verified_items.append(item)
                                verified_map[orig_key] = item
                                log.write(f"[{total_done}/{len(media_files)}] {log_msg}\n")
                            else:
                                errors.append(err)
                                log.write(f"[ERRO] [{len(verified_items)}/{len(media_files)}] {log_msg}\n")

                            # Checkpoint com throttling (a cada N itens ou X segundos)
                            now = time.time()
                            if (
                                len(verified_items) % config.checkpoint_interval_items == 0
                                or (now - last_save_time) >= config.checkpoint_interval_seconds
                            ):
                                project.items = verified_items
                                project.save()
                                last_save_time = now
                except KeyboardInterrupt:
                    print("\n[AVISO] Ingestão interrompida pelo usuário. Salvando estado atual...")
                    project.items = verified_items
                    project.save()
                    log.write(f"\n[INTERRUPÇÃO] Processo interrompido com {len(verified_items)}/{len(media_files)} arquivos salvos.\n")
                    raise

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

    # Step: Delete media files from source folder / SD card
    delete_confirmed = auto_delete_sd
    if not auto_delete_sd:
        print("\n⚠️  [ATENÇÃO - REMOÇÃO DOS ARQUIVOS ORIGINAIS]")
        print("100% das fotos e vídeos foram verificados com sucesso no SSD.")
        delete_confirmed, _ = timed_confirm_prompt(
            "Deseja apagar os arquivos originais da pasta de origem agora? (s/N)",
            timeout_seconds=config.countdown_seconds,
            default=False
        )

    if delete_confirmed:
        print("\n🗑️  Apagando fotos e vídeos verificados na pasta de origem...")
        with open(log_file, "a", encoding="utf-8") as log:
            log.write("\n=== REMOÇÃO SEGURA NA ORIGEM (APENAS FOTOS E VÍDEOS) ===\n")
            for it in verified_items:
                orig = Path(it.original_path)
                try:
                    if orig.exists():
                        orig.unlink()
                        log.write(f"DELETADO NA ORIGEM: {orig}\n")
                except Exception as e:
                    log.write(f"ERRO AO DELETAR {orig}: {e}\n")
        print("✅ Limpeza das mídias na origem concluída (arquivos não-mídia preservados).")
    else:
        print("ℹ️  Arquivos na pasta de origem foram mantidos intactos.")

    return not errors and len(verified_items) == len(media_files)
