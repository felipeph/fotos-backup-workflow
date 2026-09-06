import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig

def run_stage4(project: Project, config: PipelineConfig, auto_confirm: bool = False) -> bool:
    """
    Etapa 4: Confirmação de Upload no Google Fotos Web.
    
    Como o upload oficial do Google Fotos via navegador aplica nativamente o modo
    'Economia de Armazenamento' (Storage Saver) nos servidores do Google, esta etapa:
    1. Aponta as fotos e pastas prontas na Biblioteca do SSD.
    2. Dá a opção de abrir a pasta no Explorer para arrastar para photos.google.com.
    3. Pergunta se o upload foi concluído com sucesso.
    4. Ao confirmar, grava o timestamp de 'uploaded_at' de cada foto no project_plan.json.
    """
    if project.current_stage < 3 or not project.items:
        print("[ERRO] Arquivos ainda não foram organizados. Execute a Etapa 3 primeiro.")
        return False

    upload_candidates = [
        it for it in project.items
        if it.category in ("rajada", "avulsa") and not it.uploaded_at
    ]

    if not upload_candidates:
        print("\nℹ️  [ETAPA 4] Nenhuma foto normal pendente de upload no projeto.")
        project.current_stage = max(project.current_stage, 4)
        project.save()
        return True

    total = len(upload_candidates)
    bib_path = config.biblioteca_path

    print(f"\n☁️  [ETAPA 4] UPLOAD MANUAL NO GOOGLE FOTOS WEB (Storage Saver)")
    print("=" * 65)
    print(f"  📸 Total de fotos pendentes para upload: {total}")
    print(f"  📂 Pasta no SSD: {bib_path}")
    print(f"  🌐 Acesse no navegador: https://photos.google.com")
    print("=" * 65)
    print("Dica: No navegador, garanta que a opção 'Economia de Armazenamento'")
    print("está selecionada nas configurações do Google Fotos.\n")

    confirmed = auto_confirm

    if not confirmed:
        # Oferece abrir a pasta no explorer no Windows
        if sys.platform == "win32" and bib_path.exists():
            open_folder = input("Deseja abrir a pasta da Biblioteca no Explorador de Arquivos? [S/N]: ").strip().lower()
            if open_folder in ("s", "sim", "y", "yes"):
                os.startfile(str(bib_path))

        ans = input(f"\n❓ O upload das {total} fotos foi concluído com sucesso no Google Fotos? [S/N]: ").strip().lower()
        if ans in ("s", "sim", "y", "yes"):
            confirmed = True
        else:
            print("\n⏸️  Upload mantido como PENDENTE.")
            print("Quando terminar de subir os arquivos no navegador, execute a Etapa 4 novamente.")
            return False

    # Usuário confirmou que o upload foi concluído
    now_iso = datetime.now().isoformat()
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage4_upload.log"

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== ETAPA 4 (CONFIRMAÇÃO DE UPLOAD WEB): {now_iso} ===\n")
        log.write(f"Total de fotos confirmadas: {total}\n")

        for idx, it in enumerate(upload_candidates, start=1):
            it.uploaded_at = now_iso
            log.write(f"[{idx}/{total}] CONFIRMADO_WEB | {it.target_filename or it.original_path}\n")

    project.current_stage = max(project.current_stage, 4)
    project.save()

    print(f"\n✅ [ETAPA 4] Sucesso! {total} fotos marcadas como enviadas no project_plan.json.")
    print("As fotos confirmadas agora estão prontas para a Etapa 5 (Mover para UPLOADED/).")
    return True
