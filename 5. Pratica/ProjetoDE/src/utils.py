import pandas as pd
import requests
import logging
import numpy as np
import sqlite3
import re
from typing import Dict, List, Any
from pathlib import Path
from pydantic import BaseModel, ValidationError

# Configurar estrutura de diretórios para logs
assets_dir = Path(__file__).parent.parent / "assets"
assets_dir.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename=str(assets_dir / "app.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Schema de validação para dados da API randomuser.me
class UserSchema(BaseModel):
    """Schema para validar dados de usuários"""
    email: str
    phone: str
    cell: str
    gender: str
    nat: str


class UserListSchema(BaseModel):
    """Schema para validar lista de usuários"""
    users: List[UserSchema]


def ingestion(configs) -> pd.DataFrame:
    """Consome dados da API randomuser.me e retorna um DataFrame.

    Faz uma requisição GET para a API randomuser.me com parâmetros
    definidos nas configurações, retornando um DataFrame com os
    usuários obtidos.

    Args:
        configs: Objeto Config contendo configurações da API
            (url, timeout, default_results_per_page, etc.)

    Returns:
        pd.DataFrame: DataFrame com registros de usuários da API.
            Colunas: todos os campos retornados pela randomuser.me API.

    Raises:
        ValueError: Se houver erro de requisição ou processamento dos dados.

    """
    try:
        url: str = configs.api.url
        params: Dict[str, int] = {
            "page": 1,
            "results": configs.api.default_results_per_page,
        }

        response: requests.Response = requests.get(
            url,
            params=params,
            timeout=configs.api.timeout,
        )
        response.raise_for_status()

        data: Dict[str, Any] = response.json()
        users: List[Dict[str, Any]] = data.get("results", [])

        df: pd.DataFrame = pd.DataFrame(users)
        logging.info(
            f"Ingestão bem-sucedida: {len(df)} registros obtidos"
        )
        return df
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao ingerir dados da API: {str(e)}")
        print(f"Erro na API: {e}")
        raise ValueError("Falha na ingestão de dados da API")
    except Exception as e:
        logging.error(f"Erro inesperado na ingestão: {str(e)}")
        print(f"Erro inesperado na ingestão: {e}")
        raise ValueError("Erro inesperado na ingestão de dados")


def validation_inputs(df, configs) -> bool:
    """Valida dados de entrada conforme configurações e schemas Pydantic.

    Verifica se o DataFrame não está vazio, se contém os campos
    obrigatórios especificados nas configurações, se não há valores
    nulos nos campos requeridos e valida contra o schema Pydantic.

    Args:
        df (pd.DataFrame): DataFrame a ser validado.
        configs: Objeto Config contendo regras de validação
            (required_fields, etc.)

    Returns:
        bool: True se validação passou com sucesso.

    Raises:
        ValueError: Se DataFrame está vazio, faltam campos obrigatórios,
            há valores nulos ou falham na validação Pydantic.

    """
    try:
        # Verificar se o DataFrame está vazio
        if df is None or df.empty:
            logging.error("Validação falhou: DataFrame vazio ou nulo")
            raise ValueError("DataFrame vazio ou nulo")
        
        # Verificar campos obrigatórios da configuração
        missing_fields: List[str] = []
        for field in configs.validation.required_fields:
            if field not in df.columns:
                missing_fields.append(field)
        
        if missing_fields:
            err_msg = (
                f"Validação falhou: campos obrigatórios faltando: "
                f"{missing_fields}"
            )
            logging.error(err_msg)
            raise ValueError(err_msg)
        
        # Verificar valores nulos nos campos obrigatórios
        for field in configs.validation.required_fields:
            if field in df.columns and df[field].isnull().any():
                err_msg = (
                    f"Validação falhou: valores nulos encontrados "
                    f"no campo obrigatório '{field}'"
                )
                logging.error(err_msg)
                raise ValueError(err_msg)
        
        # Validar usando Pydantic
        data_dict: Dict[str, List[Dict[str, Any]]] = {
            "users": df.replace({np.nan: None}).to_dict(orient="records")
        }
        
        users_data = []
        for user in data_dict["users"]:
            users_data.append(UserSchema(**user))

        UserListSchema(users=users_data)
        logging.info("Dados corretos")
        return True
        
    except ValidationError as validation_error:
        errors: str = validation_error.json()
        logging.error(f"Validação falhou: {errors}")
        print(f"Erro de validação: {errors}")
        raise ValueError(f"Validação pydantic falhou: {errors}")
    except Exception as exception_error:
        err_msg = f"Erro durante validação: {exception_error}"
        logging.error(err_msg)
        print(err_msg)
        raise ValueError(err_msg)


def preparation(df, configs) -> pd.DataFrame:
    """Prepara dados para persistência: renomeia, ajusta tipos e limpa.

    Realiza transformações no DataFrame incluindo:
    - Renomeação de colunas conforme mapeamento em configs
    - Ajuste de tipos de dados (conversão para string)
    - Remoção de caracteres especiais via regex
    - Persistência em banco SQLite

    Args:
        df (pd.DataFrame): DataFrame a ser preparado.
        configs: Objeto Config contendo mapeamento de colunas,
            tipos de dados, regex de limpeza e banco de dados.

    Returns:
        pd.DataFrame: DataFrame preparado e salvo em SQLite.

    Raises:
        ValueError: Se validação falha ou há erro ao salvar dados.

    """
    try:
        # Fazer uma cópia para não alterar o dataframe original
        df_prepared: pd.DataFrame = df.copy()
        
        # Validar dados antes de processar
        validation_inputs(df_prepared, configs)
        
        # Renomear colunas (usando configuração)
        existing_columns: List[str] = [
            col for col in configs.preparation.column_mapping.keys()
            if col in df_prepared.columns
        ]
        mapping = {
            col: configs.preparation.column_mapping[col]
            for col in existing_columns
        }
        df_prepared = df_prepared.rename(columns=mapping)
        
        # Ajustar tipos de dados
        for col in configs.preparation.data_types["text_columns"]:
            if col in df_prepared.columns:
                df_prepared[col] = df_prepared[col].astype(str)
        
        # Remover caracteres especiais
        selected_columns = df_prepared.select_dtypes(
            include=['object', 'string']
        ).columns
        for col in selected_columns:
            if col in df_prepared.columns:
                df_prepared[col] = df_prepared[col].apply(
                    lambda x: (
                        re.sub(
                            configs.preparation.clean_regex,
                            '',
                            str(x)
                        )
                        if pd.notna(x)
                        else x
                    )
                )
        
        # Salvar dados tratados em base SQLite
        db_path: Path = assets_dir / configs.database.filename
        conn: sqlite3.Connection = sqlite3.connect(str(db_path))
        
        df_prepared.to_sql(
            configs.database.table_name,
            conn,
            if_exists=configs.database.if_exists,
            index=False
        )
        conn.close()
        
        logging.info(f"Dados preparados e salvos: {len(df_prepared)} linhas")
        return df_prepared
        
    except Exception as ex:
        logging.error(f"Erro na preparação dos dados: {str(ex)}")
        print(f"Erro na preparação dos dados: {ex}")
        raise ValueError(f"Erro na preparação dos dados: {str(ex)}")
