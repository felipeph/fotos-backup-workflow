import threading
import urllib.request
import urllib.parse
import sys
import time
import subprocess
from src.config import NotificationConfig

try:
    import msvcrt
except ImportError:
    msvcrt = None

def notify_event(
    title: str,
    message: str,
    config: NotificationConfig | None = None,
    sync: bool = False
):
    if config is None:
        config = NotificationConfig()

    def _worker():
        # 1. Beep Sound
        if config.sound_enabled and sys.platform == "win32":
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        # 2. Windows Toast (PowerShell WinRT)
        if config.toast_enabled and sys.platform == "win32":
            try:
                ps_script = f"""
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
                $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
                $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
                $texts = $xml.GetElementsByTagName("text")
                $texts[0].AppendChild($xml.CreateTextNode("{title}")) > $null
                $texts[1].AppendChild($xml.CreateTextNode("{message}")) > $null
                $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("FotosBackupWorkflow").Show($toast)
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                    capture_output=True,
                    timeout=5
                )
            except Exception:
                pass

        # 3. ntfy.sh Push Notification
        if config.ntfy_topic:
            try:
                url = f"https://ntfy.sh/{config.ntfy_topic}"
                req = urllib.request.Request(
                    url,
                    data=message.encode("utf-8"),
                    headers={"Title": title.encode("utf-8")},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=8):
                    pass
            except Exception:
                pass

    if sync:
        _worker()
    else:
        threading.Thread(target=_worker, daemon=True).start()

def countdown_prompt(step_name: str, timeout_seconds: int = 180) -> str:
    """
    Displays an interactive countdown timer before proceeding to the next step.
    Controls:
      - [ENTER / SPACE]: Advance immediately.
      - [P]: Pause (allows manual curation/review).
      - [C / Q]: Cancel the step.
      - [Timeout]: Auto-advances unattended.
    Returns: 'advance', 'paused', 'cancel', or 'timeout'
    """
    print(f"\n⏳ [PRÓXIMA ETAPA] '{step_name}' programada em {timeout_seconds} segundos...")
    print("Controles: [ENTER] Avançar agora | [P] Pausar para curadoria | [C] Cancelar")

    start = time.time()
    while True:
        elapsed = int(time.time() - start)
        remaining = timeout_seconds - elapsed
        if remaining <= 0:
            print("\n⏰ [TEMPO ESGOTADO] Avançando automaticamente...")
            return "timeout"

        sys.stdout.write(f"\r⏳ Tempo restante: {remaining // 60:02d}:{remaining % 60:02d} | Pressione [P] para pausar ou [ENTER] para ir agora... ")
        sys.stdout.flush()

        if msvcrt and msvcrt.kbhit():
            ch = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            if ch in ("\r", "\n", " "):
                print("\n✅ [OK] Avançando imediatamente...")
                return "advance"
            elif ch == "p":
                print("\n⏸️ [PAUSADO] Fluxo pausado para você revisar/curar as fotos.")
                print("Quando terminar a revisão, pressione ENTER para retomar o upload...")
                input()
                return "advance"
            elif ch in ("c", "q"):
                print("\n🛑 [CANCELADO] Etapa cancelada pelo usuário.")
                return "cancel"

        time.sleep(0.5)

def timed_confirm_prompt(
    prompt_text: str,
    timeout_seconds: int = 180,
    default: bool = False
) -> tuple[bool, bool]:
    """
    Exibe um prompt de confirmação [S/N] com timer regressivo de timeout_seconds.
    Se o tempo esgotar sem resposta, assume 'default' (padrão: False / Não).
    Controles:
      - [S / Y]: Confirma imediatamente (Sim).
      - [N / C / Q]: Recusa imediatamente (Não).
      - [ENTER]: Aceita o valor padrão imediatamente.
      - [Timeout]: Adota o valor padrão automaticamente ao expirar o tempo.
    Retorna: (confirmed: bool, timed_out: bool)
    """
    default_char = "S" if default else "N"

    # Se stdin não for terminal interativo ou msvcrt não estiver disponível (ex: pytest, scripts batch)
    if not sys.stdin.isatty() or msvcrt is None:
        try:
            resp = input(f"{prompt_text}: ").strip().lower()
            if resp in ("s", "sim", "y", "yes"):
                return True, False
            elif resp in ("n", "nao", "não", "no"):
                return False, False
            elif not resp:
                return default, False
        except (EOFError, Exception):
            pass
        return default, True

    print(f"\n❓ {prompt_text}")
    print(f"⏳ Responda em até {timeout_seconds}s (Padrão ao expirar: [{'SIM' if default else 'NÃO'}])")

    start = time.time()
    while True:
        elapsed = int(time.time() - start)
        remaining = timeout_seconds - elapsed
        if remaining <= 0:
            print(f"\n⏰ [TEMPO ESGOTADO ({timeout_seconds}s)] Assumindo [{'SIM' if default else 'NÃO'}] por padrão.")
            return default, True

        sys.stdout.write(f"\r⏳ Tempo restante: {remaining // 60:02d}:{remaining % 60:02d} | [S] Sim / [N] Não (Padrão: {default_char}): ")
        sys.stdout.flush()

        if msvcrt and msvcrt.kbhit():
            ch = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            if ch in ("s", "y"):
                print("\n✅ [SIM] Confirmado pelo usuário.")
                return True, False
            elif ch in ("n", "c", "q"):
                print("\n❌ [NÃO] Recusado pelo usuário.")
                return False, False
            elif ch in ("\r", "\n", " "):
                print(f"\nℹ️  [PADRÃO] Assumindo [{'SIM' if default else 'NÃO'}].")
                return default, False

        time.sleep(0.5)

