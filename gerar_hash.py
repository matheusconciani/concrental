import bcrypt
import getpass

def generate_hash():
    """Pede ao usuário uma senha de forma segura e gera um hash bcrypt."""
    try:
        password = getpass.getpass("Digite a senha para gerar o hash: ")
        if not password:
            print("\nSenha não pode ser vazia.")
            return

        # Codifica a senha para bytes e gera o salt e o hash
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Decodifica o hash para string para que possa ser copiado
        print("\nHash gerado com sucesso!")
        print("Copie o texto abaixo e cole na coluna 'password_hash' do seu banco de dados:")
        print(f"\n{hashed_password.decode('utf-8')}\n")

    except Exception as e:
        print(f"\nOcorreu um erro: {e}")

if __name__ == "__main__":
    generate_hash()
