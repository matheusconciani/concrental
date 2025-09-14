import streamlit as st
from filestack import Client
import os

def get_filestack_client():
    """Inicializa e retorna o cliente do FileStack com a API Key dos segredos."""
    try:
        api_key = st.secrets.filestack.api_key
        if not api_key:
            st.error("API Key do FileStack não encontrada no arquivo secrets.toml.")
            return None
        return Client(api_key)
    except Exception as e:
        st.error(f"Erro na configuração do FileStack. Verifique o arquivo secrets.toml. Detalhes: {e}")
        return None

def upload_file(file_to_upload):
    """
    Faz o upload de um arquivo para o FileStack salvando-o temporariamente no disco.
    """
    client = get_filestack_client()
    if not client:
        return None

    # Criar um caminho temporário para o arquivo
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, file_to_upload.name)

    try:
        # Salvar o arquivo carregado em um local temporário
        with open(temp_filepath, "wb") as f:
            f.write(file_to_upload.getvalue())
        
        # Fazer o upload a partir do caminho do arquivo
        filelink = client.upload(filepath=temp_filepath)
        return filelink.url

    except Exception as e:
        st.error(f"Erro ao fazer upload do arquivo para o FileStack: {e}")
        return None
        
    finally:
        # Garantir que o arquivo temporário seja sempre removido
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)