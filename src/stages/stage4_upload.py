import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.notifier import timed_confirm_prompt
from src.telemetry import print_stage_header, print_stage_summary, console

def run_stage4(
    project: Project,
    config: PipelineConfig,
    auto_confirm: bool = False,
    allow_proceed_on_pending: bool = False
) -> bool:
    """
    Etapa 4: Confirmação de Upload no Google Fotos Web.
    
    Como o upload oficial do Google Fotos via navegador aplica nativamente o modo
    'Economia de Armazenamento' (Storage Saver) nos servidores do Google, esta etapa:
    1. Aponta as fotos e pastas prontas na Biblioteca do SSD.
    2. Dá a opção de abrir a pasta no Explorer para arrastar para photos.google.com.
    3. Pergunta se o upload foi concluído com sucesso (com timer de 180s).
    4. Ao confirmar, grava o timestamp de 'uploaded_at' de cada arquivo no project_plan.json.
    5. Se recusado ou expirar os 180s, adota NÃO por padrão, registra no projeto e (no run-all) prossegue.
    """
    if project.current_stage < 3 or not project.items:
        print("[ERRO] Arquivos ainda não foram organizados. Execute a Etapa 3 primeiro.")
        return False

    upload_candidates = [
        it for it in project.items
        if it.category in ("rajada", "avulsa", "foto", "video") and not it.uploaded_at
    ]

    if not upload_candidates:
        print("\nℹ️  [ETAPA 4] Nenhum arquivo (foto ou vídeo) pendente de upload no projeto.")
        project.upload_status = "concluido"
        project.current_stage = max(project.current_stage, 4)
        project.save()
        return True

    total = len(upload_candidates)
    bib_path = config.biblioteca_path

    print_stage_header("ETAPA 4: CONFIRMAÇÃO DE UPLOAD WEB (GOOGLE FOTOS)", total_items=total)
    start_time = datetime.now()

    confirmed = auto_confirm
    timed_out_choice = False

    if not confirmed:
        # Oferece abrir a pasta no explorer no Windows com timer rápido de 15s
        if sys.platform == "win32" and bib_path.exists():
            open_folder, _ = timed_confirm_prompt(
                "Deseja abrir a pasta da Biblioteca no Explorador de Arquivos? [S/N]",
                timeout_seconds=min(15, config.countdown_seconds),
                default=False
            )
            if open_folder:
                os.startfile(str(bib_path))

        confirmed, timed_out_choice = timed_confirm_prompt(
            f"O upload dos {total} arquivos (fotos e vídeos) foi concluído com sucesso no Google Fotos? [S/N]",
            timeout_seconds=config.countdown_seconds,
            default=False
        )

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage4_upload.log"

    if not confirmed:
        reason = "Tempo limite de 180s esgotado" if timed_out_choice else "Recusado pelo usuário"
        project.upload_status = "pendente_timeout" if timed_out_choice else "pendente_usuario"
        project.save()

        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"=== ETAPA 4 (UPLOAD NÃO CONFIRMADO): {datetime.now().isoformat()} ===\n")
            log.write(f"Status: PENDENTE | Motivo: {reason} | Pendentes: {total} arquivos\n")

        if allow_proceed_on_pending:
            print(f"\n⏸️  [ETAPA 4] Upload mantido como PENDENTE ({reason}).")
            print("ℹ️  Registrado no projeto. Prosseguindo para as próximas etapas (ex: Timelapses)...")
            project.current_stage = max(project.current_stage, 4)
            project.save()
            print_stage_summary("Etapa 4 (Confirmação Upload Web)", start_time, success=True, items_done=0)
            return True
        else:
            print("\n⏸️  Upload mantido como PENDENTE.")
            print("Quando terminar de subir os arquivos no navegador, execute a Etapa 4 novamente.")
            return False

    # Usuário confirmou que o upload foi concluído
    now_iso = datetime.now().isoformat()
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== ETAPA 4 (CONFIRMAÇÃO DE UPLOAD WEB): {now_iso} ===\n")
        log.write(f"Total de arquivos confirmados: {total}\n")

        for idx, it in enumerate(upload_candidates, start=1):
            it.uploaded_at = now_iso
            log.write(f"[{idx}/{total}] CONFIRMADO_WEB | {it.target_filename or it.original_path}\n")

    project.upload_status = "concluido"
    project.current_stage = max(project.current_stage, 4)
    project.save()

    print_stage_summary("Etapa 4 (Confirmação Upload Web)", start_time, success=True, items_done=total)
    console.print(f"✅ [bold green]Sucesso![/bold green] {total} arquivos (fotos e vídeos) marcados como enviados no project_plan.json.")
    console.print("Os arquivos confirmados agora estão prontos para a Etapa 5 (Mover para UPLOADED/).\n")
    return True
