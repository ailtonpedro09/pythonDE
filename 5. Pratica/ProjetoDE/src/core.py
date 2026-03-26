"""
Configuração centralizada do projeto
"""

import logging
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel
from strictyaml import load

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
ASSETS_PATH = PACKAGE_ROOT / "assets"
CONFIG_FILE_PATH = ASSETS_PATH / "config.yml"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APIConfig(BaseModel):
    """Configurações da API"""
    url: str
    timeout: int
    default_results_per_page: int
    max_results_per_page: int


class ValidationConfig(BaseModel):
    """Configurações de validação"""
    required_fields: List[str]


class PreparationConfig(BaseModel):
    """Configurações de preparação dos dados"""
    column_mapping: Dict[str, str]
    data_types: Dict[str, List[str]]
    clean_regex: str


class DatabaseConfig(BaseModel):
    """Configurações do banco de dados"""
    filename: str
    table_name: str
    if_exists: str


class LoggingConfig(BaseModel):
    """Configurações de logging"""
    level: str
    format: str


class Config(BaseModel):
    """Configuração master"""
    api: APIConfig
    validation: ValidationConfig
    preparation: PreparationConfig
    database: DatabaseConfig
    logging: LoggingConfig


def create_and_validate_config(cfg_path: Path = CONFIG_FILE_PATH) -> Config:
    """Carrega e valida configurações do arquivo YAML.

    Lê arquivo de configuração em formato YAML usando strictyaml,
    valida cada seção contra modelos Pydantic e retorna objeto
    Config consolidado.

    Args:
        cfg_path (Path, optional): Caminho para arquivo config.yml.
            Padrão: {ASSETS_PATH / 'config.yml'}.

    Returns:
        Config: Objeto com configurações validadas de API, validação,
            preparação, banco de dados e logging.

    Raises:
        FileNotFoundError: Se arquivo de configuração não existir.
        ValueError: Se há erro ao carregar ou validar configurações.

    """

    parsed_config = None
    try:
        with open(cfg_path, "r", encoding="utf-8") as conf_file:
            parsed_config = load(conf_file.read())
    except FileNotFoundError:
        msg = f"Arquivo de configuração não encontrado: {cfg_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)
    except Exception as e:
        err_msg = f"Erro ao carregar configuração: {e}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Criar configuração validada
    _config = Config(
        api=APIConfig(
            **parsed_config.data.get('api', {})
        ),
        validation=ValidationConfig(
            **parsed_config.data.get('validation', {})
        ),
        preparation=PreparationConfig(
            **parsed_config.data.get('preparation', {})
        ),
        database=DatabaseConfig(
            **parsed_config.data.get('database', {})
        ),
        logging=LoggingConfig(
            **parsed_config.data.get('logging', {})
        ),
    )

    return _config


# Instância global da configuração
config = create_and_validate_config()

if __name__ == '__main__':
    logger.info("Configuração carregada com sucesso")
    logger.info(f"API URL: {config.api.url}")
    logger.info(f"Campos obrigatórios: {config.validation.required_fields}")
    logger.info(f"Banco de dados: {config.database.filename}")
