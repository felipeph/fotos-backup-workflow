# 📸 Fotos Backup Workflow - Pipeline em 7 Etapas por Projeto 🚀

Pipeline automatizado, modular e resiliente em Python para ingestão, classificação inteligente, renomeação padronizada, organização cronológica, backup e limpeza segura de fotos e vídeos com garantia de **Perda Zero (Zero-Loss)**.

Projetado especialmente para fluxos mistos de câmeras dedicadas:
- **Canon PowerShot SX60 HS / SX50 HS**: Fotografia de pássaros (teleobjetiva máxima, rajadas rápidas), vídeos 1080p a 60fps, paisagens e astrofotografia da Lua em RAW (`.CR2`).
- **Canon EOS Rebel T6 (50mm f/1.8)**: Retratos e eventos sociais.
- **GoPro**: Sequências diárias de timelapses e integração com `timelapse_studio.py`.

---

## 🎯 As 7 Etapas do Workflow

Cada lote de fotos/vídeos é gerenciado como um **Projeto/Sessão** independente, salvando seu estado no arquivo `projects/<project_id>/project_plan.json`. Você pode executar etapa por etapa de forma avulsa ou rodar tudo na sequência.

```text
[Cartão SD]
    │
    ▼ (Etapa 1: Cópia Bruta + SHA-256 por arquivo -> Apaga SD apenas se 100% OK)
[SSD Staging: staging/<projeto>/raw/]
    │
    ▼ (Etapa 2: Scan EXIF/Vídeo -> Gera project_plan.json com mapeamento completo)
[Plano JSON]
    │
    ▼ (Etapa 3: Executa renomeação e organização física nos destinos definitivos)
[Biblioteca / Astrofotografia / Timelapses]
    │
    ├─► (Etapa 4: Upload das fotos normais no perfil Economia de Armazenamento do Google Fotos)
    │        │
    │        ▼
    ├─► (Etapa 5: Move fotos enviadas com sucesso para a pasta UPLOADED/)
    │        │
    │        ▼
    ├─► (Etapa 7: Limpeza segura no SSD dos arquivos em UPLOADED/ com base no log)
    │
    └─► (Etapa 6: Detecção de timelapses e renderização direta via timelapse_studio.py)
```

### 1. Ingestão Bruta SD $\to$ SSD com Verificação SHA-256 e Limpeza do SD
- Copia os arquivos brutos do cartão SD para a pasta temporária no SSD (`staging/<project_id>/raw/`).
- Registra log detalhado arquivo por arquivo com conferência de hash SHA-256 e tamanho.
- **Apaga os arquivos do cartão SD** com segurança após confirmar 100% de integridade no SSD.

### 2. Leitura, Classificação & Criação do Plano (`project_plan.json`)
- Lê os arquivos copiados no SSD e extrai metadados (EXIF e codecs de vídeo).
- Classifica automaticamente em:
  - 🌕 `astro_lua`: RAW `.CR2` em zoom máximo na SX60/SX50.
  - ⏱️ `timelapse_gopro`: fotos sequenciais GoPro.
  - 🦅 `rajada`: disparos com intervalo $\le 3\text{s}$ (pastas `rajada_HH-mm-SS`).
  - 📷 `avulsa`: fotos isoladas (pasta `avulsas`).
  - 🎥 `video`: vídeos das câmeras (pasta `videos`).
- Gera o plano de renomeação completo e grava o log da etapa.

### 3. Execução da Renomeação e Organização Física
- Move os arquivos do staging para suas pastas definitivas conforme o plano gravado.
- Aplica a nomenclatura compacto-inteligente sem pontos na abertura (`f1-8`, `f6-5`).
- Marca cada item como organizado no plano.

### 4. Confirmação de Upload no Google Fotos Web (Storage Saver)
- Filtra apenas as mídias da biblioteca (`avulsas`, `rajadas` e `vídeos`), isolando astrofotografia e timelapses.
- Exibe o caminho local da pasta no SSD e oferece a abertura direta no Explorador de Arquivos para você arrastar para o [Google Fotos Web](https://photos.google.com).
- Ao realizar o upload no navegador, o Google Fotos aplica nativamente o modo **Economia de Armazenamento** (Storage Saver) sem necessidade de credenciais complexas de API ou OAuth.
- Pergunta ao usuário se o upload foi concluído com sucesso e grava o status `uploaded_at` no `project_plan.json`.

### 5. Transferência dos Enviados para a Pasta `UPLOADED/`
- Para cada arquivo (foto ou vídeo) cujo upload foi confirmado com sucesso, move de `Biblioteca/` para `UPLOADED/Biblioteca/ANO/MES/DIA/...`.
- Mantém na `Biblioteca/` apenas o que ainda não foi enviado ou mídias que você preferiu manter locais.

### 6. Renderização de Timelapses com `timelapse_studio.py`
- Detecta as pastas de timelapse GoPro organizadas no projeto.
- Aciona automaticamente o script configurado no `config.json` (`"timelapse_studio_path": "C:/code/timelapse/timelapse_studio.py"`), renderizando os timelapses em 4K.

### 7. Limpeza Segura no SSD dos Arquivos Enviados
- Cruza os logs da Etapa 4 e confirma os arquivos (fotos e vídeos) presentes na pasta `UPLOADED/`.
- Exibe o total de arquivos e espaço em MB/GB que será liberado no SSD.
- Solicita confirmação explícita antes de apagar as cópias locais das mídias já salvas na nuvem.

---

## 💻 Como Operar o Pipeline

### Modo Interativo no Terminal (TUI)
Dê um duplo clique no arquivo **`run_pipeline.bat`** ou execute:
```powershell
python main.py
```

O menu interativo será exibido:
```text
==========================================================================
        📸 FOTOS BACKUP WORKFLOW - PIPELINE EM 7 ETAPAS 🚀
   Projeto Ativo: [2026-09-06_sessao_01] | Status: [Etapa 2 Concluída]
==========================================================================
 [ENTER] 🚀 EXECUTAR TUDO (Sequencial 1 a 7 com pausas de 180s e alertas)
--------------------------------------------------------------------------
  1. 📥 Etapa 1: Ingestão SD -> SSD (Verificação SHA-256 e limpeza do SD)
  2. 📝 Etapa 2: Scan dos arquivos e criação do plano (project_plan.json)
  3. 🏷️  Etapa 3: Executar renomeação e organização física
  4. ☁️  Etapa 4: Confirmação de Upload Web (Google Fotos - Storage Saver)
  5. 📦 Etapa 5: Mover fotos enviadas para pasta UPLOADED
  6. ⏱️  Etapa 6: Renderizar Timelapses (timelapse_studio.py)
  7. 🧹 Etapa 7: Limpeza de fotos enviadas no SSD (Baseado no log)
--------------------------------------------------------------------------
  P. 📂 Selecionar / Criar Projeto
  C. ⚙️  Configurações (Caminhos, Notificações, Timer)
  0. 🚪 Sair
--------------------------------------------------------------------------
```

### Modo Sequencial Automático (`[ENTER]` ou CLI `--run-all`)
- Executa todas as etapas pendentes do projeto sequencialmente (1 a 7).
- Dispara notificações multicanal (Toast Windows, som e push `ntfy.sh`) ao término de cada etapa.
- Pausa com timer interativo de **180 segundos** entre cada etapa:
  - `[ENTER]`: avança imediatamente para a próxima etapa.
  - `[P]`: pausa para você inspecionar as fotos com calma.
  - `[C]`: cancela a sequência.
  - Se o tempo expirar (overnight), avança automaticamente.

### Modo Linha de Comando Direta (CLI)
- **Executar tudo de um projeto:**
  ```powershell
  python main.py run-all --project "2026-09-06_sessao_01" --source "E:\DCIM"
  ```
- **Executar uma etapa específica:**
  ```powershell
  python main.py stage 1 --project "2026-09-06_sessao_01" --source "E:\DCIM"
  python main.py stage 2 --project "2026-09-06_sessao_01"
  python main.py stage 3 --project "2026-09-06_sessao_01"
  python main.py stage 4 --project "2026-09-06_sessao_01"
  python main.py stage 5 --project "2026-09-06_sessao_01"
  python main.py stage 6 --project "2026-09-06_sessao_01"
  python main.py stage 7 --project "2026-09-06_sessao_01"
  ```
- **Verificar ambiente:**
  ```powershell
  python main.py preflight
  ```

---

## 🧪 Testes Automatizados

Para executar os testes unitários cobrindo todas as etapas e a persistência de projetos:
```powershell
python -m pytest tests/ -v
```

---

## ⚙️ Configurações (`config.json`)

```json
{
  "destination_root": "D:/Fotos_Organizadas",
  "staging_dir": "D:/Fotos_Organizadas/staging",
  "uploaded_dir": "D:/Fotos_Organizadas/UPLOADED",
  "timelapse_studio_path": "C:/code/timelapse/timelapse_studio.py",
  "burst_interval_seconds": 3.0,
  "moon_zoom_threshold_mm": 1200.0,
  "countdown_seconds": 180,
  "naming": {
    "photo_pattern": "{date}_{time}_{camera}_{focal}_{aperture}_{shutter}_{iso}_{original}.{ext}",
    "video_pattern": "{date}_{time}_{camera}_{resolution}_{fps}_{duration}_{original}.{ext}"
  },
  "notifications": {
    "toast_enabled": true,
    "sound_enabled": true,
    "ntfy_topic": "seu-topico-aqui"
  }
}
```
