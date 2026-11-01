"""Funções utilitárias compartilhadas pelos agentes."""

import base64
import shutil
from pathlib import Path

import yaml

AGENT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORIES = (
    "LSTMOutput",
    "NoticiasOutput",
    "TecnicoOutput",
    "DocsAnaliseFund",
)


def carregar_config(path_yaml: str | Path | None = None) -> dict:
    """Carrega o YAML informado ou ``config/settings.yaml`` por padrão."""
    config_path = Path(path_yaml) if path_yaml else AGENT_ROOT / "config" / "settings.yaml"
    with config_path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


def img_b64(path: Path) -> str:
    """Codifica uma imagem em base64 para modelos multimodais."""
    return base64.b64encode(path.read_bytes()).decode()


def limpar_pastas() -> None:
    """Remove os arquivos gerados nos diretórios de saída conhecidos."""
    for directory_name in OUTPUT_DIRECTORIES:
        directory = AGENT_ROOT / directory_name
        if directory.is_dir():
            for item in directory.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
