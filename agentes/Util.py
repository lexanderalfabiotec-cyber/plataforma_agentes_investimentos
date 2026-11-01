from pathlib import Path
import yaml
import os
import shutil
import base64

def carregar_config(path_yaml: str = "config.yaml") -> dict:
    """
    Função para carregar dados de configuração
    """
    with open(path_yaml, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def img_b64(path: Path) -> str:
    '''
    Converte imagem em string codificada em base 64
    Formato necessário para Imagens para Modelos Multi-Modal
    '''
    return base64.b64encode(path.read_bytes()).decode()

def limpar_pastas():
    '''
    Limpa todos os dados gerados pela aplicação ao final da execução    
    '''
    pastas = ["LSTMOutput", "NoticiasOutput", "TecnicoOutput", "DocsAnaliseFund"]
    for pasta in pastas:
        if os.path.exists(pasta):
            for nome_arquivo in os.listdir(pasta):
                caminho_arquivo = os.path.join(pasta, nome_arquivo)
                try:
                    if os.path.isfile(caminho_arquivo):
                        os.remove(caminho_arquivo)
                    elif os.path.isdir(caminho_arquivo):
                        shutil.rmtree(caminho_arquivo)
                except Exception as e:
                    print(f"Erro ao remover {caminho_arquivo}: {e}")
        else:
            print(f"Pasta não encontrada: {pasta}")


    

