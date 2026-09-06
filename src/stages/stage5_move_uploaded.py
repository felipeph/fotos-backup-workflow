import sys
import shutil
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.storage import safe_copy_file, compute_sha256

def run_stage5(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 5: Transferência dos arquivos cujo upload já ocorreu corretamente
    para a pasta UPLOADED, preservando a estrutura de pastas.
    """
    if project.current_stage < 4 or not project.items:
        print("[ERRO] Etapa de upload não concluída. Execute a Etapa 4 primeiro.")
        return False

    uploaded_candidates = [
        it for it in project.items
        if it.uploaded_at and not it.uploaded_path
    ]

    if not uploaded_candidates:
        print("\nℹ️  [ETAPA 5] Nenhuma foto pendente de transferência para a pasta UPLOADED.")
        project.current_stage = max(project.current_stage, 5)
        project.save()
        return True

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage5_move_uploaded.log"

    dest_uploaded_root = config.uploaded_path
    total = len(uploaded_candidates)
    print(f"\n📦 [ETAPA 5] Movendo {total} fotos confirmadas no Google Fotos para: {dest_uploaded_root} ...")

    success_count = 0
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 5 (MOVER PARA UPLOADED): {datetime.now().isoformat()} ===\n\n")

        for idx, it in enumerate(uploaded_candidates, start=1):
            cur_p = Path(it.organized_path)
            if not cur_p.exists():
                log.write(f"[{idx}/{total}] ARQUIVO NÃO ENCONTRADO: {cur_p}\n")
                continue

            target_dir = dest_uploaded_root / it.relative_dest_dir
            res = safe_copy_file(cur_p, target_dir, it.target_filename)

            if res.status in ("copied", "skipped_duplicate"):
                it.uploaded_path = str(res.target_path.resolve())
                # Safe move: remove from original Biblioteca location
                cur_p.unlink(missing_ok=True)
                success_count += 1

                log.write(f"[{idx}/{total}] MOVIDO: {cur_p.name} -> {res.target_path}\n")
                sys.stdout.write(f"\r[{idx}/{total}] 📦 {cur_p.name[:40]:<40} -> UPLOADED")
                sys.stdout.flush()
            else:
                log.write(f"[{idx}/{total}] ERRO: {res.error_message} | {cur_p}\n")
                print(f"\n❌ Erro ao mover {cur_p.name}: {res.error_message}")

    project.current_stage = 5
    project.save()

    print(f"\n\n✨ Transferência para UPLOADED concluída: {success_count}/{total} arquivos movidos com sucesso!")
    return success_count == total
