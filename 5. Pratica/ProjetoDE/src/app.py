import utils as utils
import logging
import pandas as pd
from core import config

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    logging.info("Iniciando processo de ingestão")
    try:
        df: pd.DataFrame = utils.ingestion(config)
        logging.info(f"DataFrame de ingestão:\n{df.head()}")
    except Exception as e:
        logging.error(f"Erro de ingestão de dados: {str(e)}")
    try:
        utils.preparation(df, config)
        logging.info("Fim do processo de ingestão")
        print("Processo de ingestão concluído com sucesso.")
    except Exception as e:
        logging.error(f"Erro de preparação: {str(e)}")
        print("Processo de ingestão falhou.")
