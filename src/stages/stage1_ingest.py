import sys
import shutil
import os
import time
from pathlib import Path
from datetime import datetime

from src.project import Project, ProjectItem
from src.config import PipelineConfig
from src.storage import compute_sha256
from src.metadata_extractor import PHOTO_EXTENSIONS, VIDEO_EXTENSIONS

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

    print(f"\n📥 [ETAPA 1] Copiando {len(media_files)} arquivos do SD para o SSD...")
    print(f"   Origem:  {source_dir}")
    print(f"   Destino: {staging_dir}")
    print(f"   Log:     {log_file}\n")

    verified_items: list[ProjectItem] = []
    errors: list[str] = []

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 1: {datetime.now().isoformat()} ===\n")
        log.write(f"Origem: {source_dir} | Destino: {staging_dir}\n\n")

        for idx, src_p in enumerate(media_files, start=1):
            rel_path = src_p.relative_to(source_dir)
            target_p = staging_dir / rel_path
            target_p.parent.mkdir(parents=True, exist_ok=True)

            src_size = src_p.stat().st_size
            src_sha = compute_sha256(src_p)

            # Copy file
            shutil.copy2(src_p, target_p)
            dest_size = target_p.stat().st_size
            dest_sha = compute_sha256(target_p)

            if src_sha == dest_sha and src_size == dest_size:
                log_line = f"[{idx}/{len(media_files)}] OK | SHA256:{src_sha} | {rel_path} ({src_size} bytes)"
                log.write(log_line + "\n")
                sys.stdout.write(f"\r[{idx}/{len(media_files)}] ✅ {src_p.name[:35]:<35} SHA-256 OK")
                sys.stdout.flush()

                verified_items.append(ProjectItem(
                    original_path=str(src_p.resolve()),
                    staging_path=str(target_p.resolve()),
                    sha256=src_sha,
                    file_size_bytes=src_size,
                ))
            else:
                err_msg = f"FALHA DE INTEGRIDADE: {src_p} ({src_sha}) != {target_p} ({dest_sha})"
                errors.append(err_msg)
                log.write(f"[ERRO] {err_msg}\n")
                print(f"\n❌ {err_msg}")

    print(f"\n\n📊 Cópia finalizada: {len(verified_items)} verificados com sucesso, {len(errors)} erros.")

    if errors or len(verified_items) != len(media_files):
        print("🛑 [SEGURANÇA] Houve erros de integridade! O cartão SD NÃO será apagado.")
        return False

    # All files 100% verified!
    project.items = verified_items
    project.current_stage = 1
    project.save()

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
