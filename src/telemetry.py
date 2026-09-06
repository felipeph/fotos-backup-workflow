from datetime import datetime, timedelta
from typing import Optional
from rich.console import Console
from rich.progress import (
    Progress,
    ProgressColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
    DownloadColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
    SpinnerColumn,
)
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

console = Console()

class EstimatedEndTimeColumn(ProgressColumn):
    """Exibe o horário previsto de término no relógio do sistema (ex: Término: 19:45:10)."""
    
    def __init__(self, table_column=None):
        super().__init__(table_column=table_column)

    def render(self, task) -> Text:
        remaining = task.time_remaining
        if remaining is None:
            return Text("Término: --:--:--", style="dim")
        eta_time = datetime.now() + timedelta(seconds=int(remaining))
        return Text(f"Término: {eta_time.strftime('%H:%M:%S')}", style="cyan bold")

class SpeedPerSecondColumn(ProgressColumn):
    """Exibe a taxa em itens/segundo (ex: 24.5 arqs/s)."""
    
    def __init__(self, unit: str = "arqs/s", table_column=None):
        self.unit = unit
        super().__init__(table_column=table_column)

    def render(self, task) -> Text:
        speed = task.speed
        if speed is None:
            return Text(f"--.- {self.unit}", style="dim")
        return Text(f"{speed:.1f} {self.unit}", style="magenta")

def create_byte_progress() -> Progress:
    """Barra de progresso para transferência de arquivos e I/O em bytes."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        TextColumn("•"),
        EstimatedEndTimeColumn(),
        console=console,
        transient=False,
    )

def create_item_progress(unit: str = "arqs/s") -> Progress:
    """Barra de progresso para contagem de arquivos e metadados."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        SpeedPerSecondColumn(unit=unit),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        TextColumn("•"),
        EstimatedEndTimeColumn(),
        console=console,
        transient=False,
    )

def print_stage_header(stage_name: str, total_items: int = 0, total_bytes: int = 0):
    """Exibe cabeçalho moderno e padronizado no início de cada etapa."""
    now_str = datetime.now().strftime("%H:%M:%S")
    info_parts = [f"[bold green]Início:[/bold green] {now_str}"]
    
    if total_items > 0:
        info_parts.append(f"[bold cyan]Arquivos:[/bold cyan] {total_items:,}")
    if total_bytes > 0:
        gb = total_bytes / (1024 ** 3)
        if gb >= 1.0:
            info_parts.append(f"[bold yellow]Volume:[/bold yellow] {gb:.2f} GB")
        else:
            mb = total_bytes / (1024 ** 2)
            info_parts.append(f"[bold yellow]Volume:[/bold yellow] {mb:.1f} MB")
            
    header_text = "  |  ".join(info_parts)
    console.print(Panel(
        f"[bold white]{stage_name}[/bold white]\n{header_text}",
        border_style="bright_blue",
        expand=False,
    ))

def print_stage_summary(stage_name: str, start_time: datetime, success: bool, items_done: int = 0, bytes_done: int = 0):
    """Exibe resumo no término da etapa com tempo total e velocidade média."""
    elapsed = datetime.now() - start_time
    total_sec = max(elapsed.total_seconds(), 0.001)
    
    m, s = divmod(int(total_sec), 60)
    h, m = divmod(m, 60)
    dur_str = f"{h:02d}h{m:02d}s" if h == 0 else f"{h:02d}h{m:02d}m{s:02d}s"
    
    details = [f"Duração: [bold]{dur_str}[/bold]"]
    if bytes_done > 0:
        avg_speed_mb = (bytes_done / (1024 * 1024)) / total_sec
        details.append(f"Média: [bold cyan]{avg_speed_mb:.1f} MB/s[/bold cyan]")
    elif items_done > 0:
        avg_items_s = items_done / total_sec
        details.append(f"Média: [bold magenta]{avg_items_s:.1f} arqs/s[/bold magenta]")
        
    status_icon = "✅" if success else "⚠️"
    status_style = "green" if success else "yellow"
    detail_str = " | ".join(details)
    
    console.print(f"\n{status_icon} [{status_style}]{stage_name} finalizada![/{status_style}] ({detail_str})\n")
