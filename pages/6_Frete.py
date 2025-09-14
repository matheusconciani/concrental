import streamlit as st
from db_management import (
    is_authenticated,
    logout,
    get_user_settings,
    update_user_settings,
    get_user_addresses,
    add_user_address,
    delete_user_address
)
from streamlit_cookies_manager import CookieManager
from geopy.distance import geodesic
import pandas as pd

st.set_page_config(page_title="ConcRental - Frete", layout="wide")

cookies = CookieManager()

# --- Autenticação ---
if not is_authenticated(cookies):
    st.error("Por favor, faça o login para acessar esta página.")
    st.stop()

# --- Sidebar ---
st.sidebar.title(f"Bem-vindo, {st.session_state.get('username', 'Usuário')}!")
if st.sidebar.button("Sair"):
    logout(cookies)

st.title("Cálculo de Frete")

user_id = st.session_state.user_id

# --- Seção de Configurações ---
with st.expander("Configurações de Cálculo de Frete", expanded=True):
    st.subheader("Defina seus custos e consumo")
    user_settings = get_user_settings(user_id)

    with st.form("settings_form"):
        fuel_consumption = st.number_input(
            "Consumo de combustível do veículo (Km/L)",
            min_value=0.1,
            value=user_settings.get("fuel_consumption", 10.0),
            format="%.2f"
        )
        fuel_cost = st.number_input(
            "Custo do combustível (R$/L)",
            min_value=0.01,
            value=user_settings.get("fuel_cost", 5.50),
            format="%.2f"
        )
        if st.form_submit_button("Salvar Configurações"):
            success, message = update_user_settings(user_id, fuel_consumption, fuel_cost)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# --- Seção de Endereços ---
with st.expander("Gerenciar Endereços de Partida"):
    st.subheader("Seus endereços fixos")
    
    # Adicionar Endereço
    with st.form("add_address_form", clear_on_submit=True):
        address_name = st.text_input("Nome do Endereço", placeholder="Ex: Unidade São José dos Pinhais")
        address = st.text_input("Endereço Completo", placeholder="Ex: Rua das Flores, 123, São José dos Pinhais, PR")
        if st.form_submit_button("Adicionar Endereço"):
            if address_name and address:
                success, message = add_user_address(user_id, address_name, address)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Por favor, preencha todos os campos.")

    st.divider()

    # Listar e Deletar Endereços
    user_addresses = get_user_addresses(user_id)
    if not user_addresses.empty:
        st.write("Endereços Cadastrados:")
        for index, row in user_addresses.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"{row['address_name']}: {row['address']}")
            with col2:
                if st.button("Deletar", key=f"delete_{row['id']}"):
                    success, message = delete_user_address(row['id'])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("Nenhum endereço de partida cadastrado.")


# --- Seção da Calculadora ---
with st.expander("Calculadora de Frete", expanded=True):
    st.subheader("Calcular valor para o contrato")
    user_addresses = get_user_addresses(user_id)

    if user_addresses.empty or user_settings.get("fuel_consumption") == 0.0:
        st.warning("Por favor, cadastre pelo menos um endereço de partida e configure o consumo de combustível para usar a calculadora.")
    else:
        with st.form("freight_form"):
            start_address_name = st.selectbox(
                "Escolha o endereço de partida",
                options=user_addresses["address_name"].tolist()
            )
            customer_address = st.text_input("Endereço do Cliente", placeholder="Digite o endereço de entrega/coleta")
            
            if st.form_submit_button("Calcular Frete"):
                if customer_address:
                    try:
                        start_address_row = user_addresses[user_addresses["address_name"] == start_address_name].iloc[0]
                        start_coords = (start_address_row["latitude"], start_address_row["longitude"])
                        
                        from geopy.geocoders import Nominatim
                        geolocator = Nominatim(user_agent="concrental_app_v3")
                        customer_location = geolocator.geocode(customer_address)

                        if customer_location:
                            customer_coords = (customer_location.latitude, customer_location.longitude)
                            
                            # Calcular distância
                            distance_one_way = geodesic(start_coords, customer_coords).kilometers
                            total_distance = distance_one_way * 4
                            
                            # Calcular custo
                            total_fuel = total_distance / user_settings["fuel_consumption"]
                            freight_cost = total_fuel * user_settings["fuel_cost"]
                            
                            st.session_state.calculated_freight_cost = freight_cost

                            st.success(f"Cálculo concluído com sucesso!")
                            st.info(f"Distância de ida: {distance_one_way:.2f} km")
                            st.info(f"Percurso total (4x): {total_distance:.2f} km")
                            st.metric("Custo do Frete", f"R$ {freight_cost:.2f}")

                        else:
                            st.error("Não foi possível encontrar as coordenadas para o endereço do cliente.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro ao calcular a distância: {e}")
                else:
                    st.warning("Por favor, insira o endereço do cliente.")

    if "calculated_freight_cost" in st.session_state:
        if st.button("Enviar Valor do Frete para o Contrato"):
            st.session_state.freight_cost_to_contract = st.session_state.calculated_freight_cost
            st.success("Valor do frete foi salvo e será adicionado ao próximo contrato que você criar.")
            # Optional: clear the calculated value after sending
            # del st.session_state.calculated_freight_cost
