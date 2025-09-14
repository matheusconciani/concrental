import streamlit as st
import pandas as pd
from streamlit_cookies_manager import CookieManager
from db_management import (
    get_all_rentals,
    get_all_customers,
    get_all_equipments,
    is_authenticated,
    logout
)

st.set_page_config(page_title="ConcRental - Mapa", layout="wide")

cookies = CookieManager()

# --- Autenticação ---
if not is_authenticated(cookies):
    st.error("Por favor, faça o login para acessar esta página.")
    st.stop()

# --- Sidebar ---
st.sidebar.title(f"Bem-vindo, {st.session_state.get('username', 'Usuário')}!")
if st.sidebar.button("Sair"):
    logout(cookies)

st.title("Mapa de Equipamentos")
st.markdown("Localização em tempo real dos equipamentos que estão atualmente alugados.")

# --- Load Data ---
user_id = st.session_state.user_id
rentals_df = get_all_rentals(user_id)
customers_df = get_all_customers(user_id)
equipment_df = get_all_equipments(user_id)

if rentals_df.empty or customers_df.empty:
    st.info("Não há dados de aluguéis ou clientes para exibir no mapa.")
    st.stop()

# --- Data Processing ---
active_rentals_df = rentals_df[rentals_df['status'] == 'Ativo']

if active_rentals_df.empty:
    st.info("Nenhum equipamento alugado no momento para exibir no mapa.")
else:
    map_data_df = active_rentals_df.merge(customers_df, on="customer_id")
    map_data_df.dropna(subset=['latitude', 'longitude'], inplace=True)

    if map_data_df.empty:
        st.warning("Nenhum dos clientes com aluguéis ativos possui um endereço geolocalizado. Verifique os endereços no CRM.")
    else:
        # Renomear colunas para o formato exigido pelo st.map
        map_data_df.rename(columns={'latitude': 'lat', 'longitude': 'lon'}, inplace=True)
        
        # Usando o st.map básico que é garantido de funcionar.
        st.map(map_data_df, zoom=11)