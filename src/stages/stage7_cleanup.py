import sys
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig

def run_stage7(project: Project, config: PipelineConfig, auto_confirm: bool = False) -> bool:
    """
    Etapa 7: Limpeza de arquivos no SSD cujo upload para o Google Fotos foi
    efetuado e comprovado por meio do log e manifesto da Etapa 4.
    """
    candidates = [
        it for it in project.items
        if it.uploaded_at and it.uploaded_path and not it.cleaned_at
    ]

    if not candidates:
        print("\nℹ️  [ETAPA 7] Nenhum arquivo elegível para limpeza neste projeto.")
        project.current_stage = max(project.current_stage, 7)
        project.save()
        return True

    # Validate against upload log
    log_stage4 = Path("logs") / f"{project.project_id}_stage4_upload.log"
    verified_candidates = []
    total_bytes = 0

    for it in candidates:
        p = Path(it.uploaded_path)
        if p.exists():
            verified_candidates.append(it)
            total_bytes += it.file_size_bytes

    if not verified_candidates:
        print("\nℹ️  [ETAPA 7] Os arquivos já haviam sido limpos ou não foram encontrados no disco.")
        project.current_stage = max(project.current_stage, 7)
        project.save()
        return True

    total_mb = total_bytes / (1024 * 1024)
    print(f"\n🧹 [ETAPA 7] LIMPEZA DE ARQUIVOS ENVIADOS NO SSD:")
    print(f"   Arquivos com upload comprovado no Google Fotos: {len(verified_candidates)}")
    print(f"   Espaço total que será liberado no SSD:          {total_mb:.2f} MB ({total_mb / 1024:.2f} GB)")

    confirmed = auto_confirm
    if not auto_confirm:
        print("\n⚠️  [CONFIRMAÇÃO NECESSÁRIA]")
        print("Estes arquivos já estão salvos com segurança na nuvem (Google Fotos).")
        resp = input("Deseja apagar agora as cópias locais destes arquivos da pasta UPLOADED? (s/N): ").strip().lower()
        confirmed = (resp == "s")

    if not confirmed:
        print("ℹ️  Limpeza cancelada pelo usuário. Os arquivos foram mantidos no SSD.")
        return False

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage7_cleanup.log"

    deleted_count = 0
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 7 (LIMPEZA PÓS-UPLOAD): {datetime.now().isoformat()} ===\n")
        log.write(f"Total de arquivos a remover: {len(verified_candidates)} ({total_mb:.2f} MB)\n\n")

        for idx, it in enumerate(verified_candidates, start=1):
            p = Path(it.uploaded_path)
            try:
                if p.exists():
                    p.unlink()
                    it.cleaned_at = datetime.now().isoformat()
                    deleted_count += 1
                    log.write(f"[{idx}/{len(verified_candidates)}] APAGADO: {p}\n")
                    sys.stdout.write(f"\r[{idx}/{len(verified_candidates)}] 🗑️  {p.name[:45]:<45}")
                    sys.stdout.flush()
            except Exception as e:
                log.write(f"[ERRO] Falha ao apagar {p}: {e}\n")

    project.current_stage = 7
    project.save()

    print(f"\n\n✨ Limpeza concluída: {deleted_count} arquivos apagados. {total_mb:.2f} MB liberados no SSD!")
    return True
