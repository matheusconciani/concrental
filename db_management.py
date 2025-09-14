import streamlit as st
import psycopg2
import bcrypt
import pandas as pd
from geopy.geocoders import Nominatim

# --- Configuração Inicial ---
geolocator = Nominatim(user_agent="concrental_app_v3")

# --- Funções de Conexão ---
@st.cache_resource
def get_db_connection():
    """
    Estabelece e armazena em cache uma conexão com o banco de dados PostgreSQL
    usando as credenciais do secrets.toml do Streamlit.
    """
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["host"],
            port=st.secrets["postgres"]["port"],
            dbname=st.secrets["postgres"]["dbname"],
            user=st.secrets["postgres"]["user"],
            password=st.secrets["postgres"]["password"],
            sslmode='require'
        )
        return conn
    except psycopg2.Error as e:
        st.error(f"Erro detalhado ao conectar: {e}")
        return None
    except (psycopg2.OperationalError, KeyError) as e:
        st.error(f"Erro ao conectar ao banco dedados. Verifique suas configurações em .streamlit/secrets.toml. Detalhe: {e}")
        return None

# --- Funções de Autenticação ---
def logout(cookie_manager):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_id = None
    if 'user_id' in cookie_manager:
        del cookie_manager['user_id']
    st.cache_data.clear()
    st.cache_resource.clear() # Limpa o cache de conexão também
    st.rerun()

def is_authenticated(cookies):
    if not st.session_state.get("logged_in"):
        user_id_from_cookie = cookies.get('user_id')
        if user_id_from_cookie:
            username = get_user_by_id(user_id_from_cookie)
            if username:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_id = user_id_from_cookie
                return True
    return st.session_state.get("logged_in", False)

def verify_user(username, password):
    conn = get_db_connection()
    if conn is None: return False, None, None
    user_found = False
    user_id = None
    db_username = None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, password_hash, username FROM users WHERE username ILIKE %s", (username,))
            result = cursor.fetchone()
            if result:
                user_id, stored_hash, db_username = result
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    user_found = True
    except psycopg2.Error as e:
        st.error(f"Erro ao verificar usuário: {e}")
    return user_found, user_id, db_username


def get_user_id_by_username(username):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            return result[0] if result else None
    except psycopg2.Error as e:
        st.error(f"Erro ao buscar ID do usuário: {e}")
        return None


def get_user_by_id(user_id):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    except psycopg2.Error as e:
        st.error(f"Erro ao buscar usuário por ID: {e}")
        return None


# --- Funções de Equipamento ---
@st.cache_data
def get_all_equipments(user_id):
    conn = get_db_connection()
    if conn is None: return pd.DataFrame()
    return pd.read_sql('SELECT * FROM equipments WHERE user_id = %s ORDER BY equipment_id ASC', conn, params=(user_id,))


def add_equipment_to_db(user_id, name, category, serial, acq_date, purchase_status):
    conn = get_db_connection()
    if conn is None: return False, "Falha na conexão."
    sql = "INSERT INTO equipments (user_id, equipment_id, name, category, serial_number, acquisition_date, status, purchase_status, times_rented) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT equipment_id FROM equipments ORDER BY equipment_id DESC LIMIT 1")
            last_id = cursor.fetchone()
            last_num = 0
            if last_id: last_num = int(last_id[0].replace("EQ", ""))
            new_id = f"EQ{last_num + 1:03d}"
            cursor.execute(sql, (user_id, new_id, name, category, serial, acq_date, "Disponível", purchase_status, 0))
            conn.commit()
        st.cache_data.clear()
        return True, "Equipamento adicionado com sucesso!"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, f"Erro: Equipamento com número de série '{serial}' já existe."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Erro no banco de dados: {e}"

def update_equipment_in_db(equipment_id, updates):
    conn = get_db_connection()
    if conn is None: return
    try:
        with conn.cursor() as cursor:
            set_clause = ", ".join([f'{key} = %s' for key in updates.keys()])
            query = f'UPDATE equipments SET {set_clause} WHERE equipment_id = %s'
            params = list(updates.values()) + [equipment_id]
            cursor.execute(query, params)
            conn.commit()
        st.cache_data.clear()
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"Erro ao atualizar equipamento: {e}")

def delete_equipment_from_db(equipment_id):
    conn = get_db_connection()
    if conn is None: return False, "Falha na conexão."
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM equipments WHERE equipment_id = %s', (equipment_id,))
            conn.commit()
        st.cache_data.clear()
        return True, "Equipamento deletado com sucesso."
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        return False, "Este equipamento não pode ser deletado pois está associado a um ou mais aluguéis."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Erro no banco de dados: {e}"

# --- Funções de Cliente ---
@st.cache_data
def get_all_customers(user_id):
    conn = get_db_connection()
    if conn is None: return pd.DataFrame()
    return pd.read_sql('SELECT * FROM customers WHERE user_id = %s ORDER BY customer_id ASC', conn, params=(user_id,))

def add_customer_to_db(user_id, full_name, company_name, phone, email, address, doc_type, doc_number):
    conn = get_db_connection()
    if conn is None: return False, "Falha na conexão."
    sql = "INSERT INTO customers (user_id, customer_id, full_name, company_name, phone_number, email_address, address, document_type, document_number) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT customer_id FROM customers ORDER BY customer_id DESC LIMIT 1")
            last_id = cursor.fetchone()
            last_num = 0
            if last_id: last_num = int(last_id[0].replace("CUST", ""))
            new_id = f"CUST{last_num + 1:03d}"
            cursor.execute(sql, (user_id, new_id, full_name, company_name, phone, email, address, doc_type, doc_number))
            conn.commit()
        st.cache_data.clear()
        return True, "Cliente adicionado com sucesso!"
    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "Erro: Cliente com este CPF/CNPJ já existe."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Erro no banco de dados: {e}"

def update_customer_in_db(customer_id, updates):
    conn = get_db_connection()
    if conn is None: return
    try:
        with conn.cursor() as cursor:
            set_clause = ", ".join([f'{key} = %s' for key in updates.keys()])
            query = f'UPDATE customers SET {set_clause} WHERE customer_id = %s'
            params = list(updates.values()) + [customer_id]
            cursor.execute(query, params)
            conn.commit()
        st.cache_data.clear()
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"Erro ao atualizar cliente: {e}")

def geocode_and_update_customer(customer_id, address):
    if not address:
        return False, "Endereço vazio."
    try:
        location = geolocator.geocode(address + ", Curitiba, Brazil", timeout=10)
        if location:
            updates = {'latitude': location.latitude, 'longitude': location.longitude}
            update_customer_in_db(customer_id, updates)
            return True, "Coordenadas atualizadas com sucesso!"
        else:
            return False, "Endereço não encontrado."
    except Exception as e:
        return False, f"Erro de geolocalização: {e}"

def delete_customer_from_db(customer_id):
    conn = get_db_connection()
    if conn is None: return False, "Falha na conexão."
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM customers WHERE customer_id = %s', (customer_id,))
            conn.commit()
        st.cache_data.clear()
        return True, "Cliente deletado com sucesso."
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        return False, "Este cliente não pode ser deletado pois está associado a um ou mais aluguéis."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Erro no banco de dados: {e}"

# --- Funções de Aluguel ---
@st.cache_data
def get_all_rentals(user_id):
    conn = get_db_connection()
    if conn is None: return pd.DataFrame()
    query = """
        SELECT r.* FROM rentals r
        JOIN customers c ON r.customer_id = c.customer_id
        WHERE c.user_id = %s
        ORDER BY r.start_date DESC
    """
    return pd.read_sql(query, conn, params=(user_id,))

def add_rentals_to_db(user_id, customer_id, equipment_ids, start_date, end_date, valor):
    conn = get_db_connection()
    if conn is None: return False, "Falha na conexão."
    sql = "INSERT INTO rentals (user_id, rental_id, customer_id, equipment_id, start_date, end_date, status, payment_status, valor) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT rental_id FROM rentals ORDER BY rental_id DESC LIMIT 1')
            last_id = cursor.fetchone()
            last_num = 0
            if last_id:
                last_num = int(last_id[0].replace("RENT", ""))
            for i, equipment_id in enumerate(equipment_ids):
                new_rental_id = f"RENT{last_num + 1 + i:03d}"
                cursor.execute(sql, (user_id, new_rental_id, customer_id, equipment_id, start_date, end_date, "Ativo", "Em Aberto", valor))
                cursor.execute('UPDATE equipments SET status = %s, times_rented = times_rented + 1 WHERE equipment_id = %s', ("Alugado", equipment_id))
            conn.commit()
        st.cache_data.clear()
        return True, "Aluguel criado com sucesso!"
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Erro no banco de dados: {e}"

def complete_rental_in_db(rental_id, equipment_id):
    conn = get_db_connection()
    if conn is None: return False, "Falha na conexão."
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE rentals SET status = %s WHERE rental_id = %s', ("Concluído", rental_id))
            cursor.execute('UPDATE equipments SET status = %s WHERE equipment_id = %s', ("Disponível", equipment_id))
            conn.commit()
        st.cache_data.clear()
        return True, "Aluguel marcado como concluído."
    except psycopg2.Error as e:
        conn.rollback()
        return False, f"Erro no banco de dados: {e}"

def update_rental_in_db(rental_id, column, value):
    conn = get_db_connection()
    if conn is None: return
    try:
        with conn.cursor() as cursor:
            query = f'UPDATE rentals SET {column} = %s WHERE rental_id = %s'
            cursor.execute(query, (value, rental_id))
            conn.commit()
        st.cache_data.clear()
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"Erro ao atualizar aluguel: {e}")