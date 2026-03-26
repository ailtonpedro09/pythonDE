"""Testes básicos para validação da estrutura do projeto."""

import sys
from pathlib import Path

# Adicionar src ao path para importações
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def test_imports():
    """Valida que todos os módulos principais importam sem erro."""
    try:
        import core  # noqa: F401
        import utils  # noqa: F401
        import app  # noqa: F401
        assert True
    except ImportError as e:
        assert False, f"Erro ao importar módulo: {e}"


def test_config_loading():
    """Valida carregamento e validação de configurações."""
    from core import config

    assert config is not None
    assert hasattr(config, 'api')
    assert hasattr(config, 'validation')
    assert hasattr(config, 'preparation')
    assert hasattr(config, 'database')
    assert hasattr(config, 'logging')


def test_config_api_settings():
    """Valida configurações da API."""
    from core import config

    assert config.api.url is not None
    assert config.api.timeout > 0
    assert config.api.default_results_per_page > 0


def test_config_validation_settings():
    """Valida configurações de validação."""
    from core import config

    assert config.validation.required_fields is not None
    assert len(config.validation.required_fields) > 0


def test_schemas_exist():
    """Valida que schemas Pydantic estão definidos."""
    from utils import UserSchema, UserListSchema
    from pydantic import BaseModel

    assert issubclass(UserSchema, BaseModel)
    assert issubclass(UserListSchema, BaseModel)


def test_user_schema_validation():
    """Valida que schema UserSchema funciona corretamente."""
    from utils import UserSchema

    valid_user = {
        "email": "test@example.com",
        "phone": "+1234567890",
        "cell": "+0987654321",
        "gender": "male",
        "nat": "US",
    }

    user = UserSchema(**valid_user)
    assert user.email == "test@example.com"
    assert user.nat == "US"
