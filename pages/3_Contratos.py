import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_cookies_manager import CookieManager
from db_management import (
    get_all_rentals,
    get_all_customers,
    get_all_equipments,
    add_rentals_to_db,
    complete_rental_in_db,
    update_rental_in_db,
    is_authenticated,
    logout
)
from pdf_generator import create_contract_pdf
from file_management import upload_file

st.set_page_config(page_title="ConcRental - Contratos", layout="wide")

cookies = CookieManager()

# --- Autenticação ---
if not is_authenticated(cookies):
    st.error("Por favor, faça o login para acessar esta página.")
    st.stop()

# --- Sidebar ---
st.sidebar.title(f"Bem-vindo, {st.session_state.get('username', 'Usuário')}!")
if st.sidebar.button("Sair"):
    logout(cookies)

st.title("Contratos de Aluguel")

# --- Load Data from DB ---
user_id = st.session_state.user_id
rentals_df = get_all_rentals(user_id)
customers_df = get_all_customers(user_id)
equipment_df = get_all_equipments(user_id)

# --- Funções de Callback ---
def handle_contract_upload(rental_id, uploader_key):
    uploaded_file = st.session_state.get(uploader_key)
    if uploaded_file:
        with st.spinner("Fazendo upload do contrato para a nuvem..."):
            file_url = upload_file(uploaded_file)
        
        if file_url:
            update_rental_in_db(rental_id, 'signed_contract_path', file_url)
            st.success("Contrato assinado salvo na nuvem com sucesso!")
        else:
            st.error("O upload para a nuvem falhou. Verifique sua conexão e o tamanho do arquivo.")

# --- Page Filtering ---
customer_id_filter = st.session_state.get("customer_id_filter")

if customer_id_filter:
    rentals_df = rentals_df[rentals_df["customer_id"] == customer_id_filter]
    if not customers_df.empty:
        customer_name = customers_df[customers_df["customer_id"] == customer_id_filter]["full_name"].iloc[0]
        st.info(f"Mostrando contratos para o cliente: {customer_name}")
        if st.button("Mostrar Todos os Contratos"):
            del st.session_state.customer_id_filter
            st.rerun()

# --- Create New Rental Form ---
if not customer_id_filter:
    with st.expander("Criar Novo Aluguel"):
        freight_cost_from_session = st.session_state.get("freight_cost_to_contract", 0.0)
        with st.form(key="new_rental_form", clear_on_submit=True):
            st.subheader("Detalhes do Novo Contrato")
            if not customers_df.empty:
                customer_list = customers_df['full_name'].tolist()
                selected_customer_name = st.selectbox("Escolha um Cliente", options=customer_list, index=None, placeholder="Selecione...")
            else:
                selected_customer_name = None
            available_equipment = equipment_df[equipment_df['status'] == 'Disponível']
            selected_equipment_names = st.multiselect("Escolha o(s) Equipamento(s)", options=available_equipment['name'].tolist(), placeholder="Selecione...")
            col1, col2 = st.columns(2)
            valor_total = col1.number_input("Valor Total do Aluguel (R$)", min_value=0.01, placeholder="0.00", format="%.2f")
            freight_cost = col2.number_input("Custo do Frete (R$)", min_value=0.0, value=float(freight_cost_from_session), format="%.2f")
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Data de Início")
            end_date = col2.date_input("Data de Fim")
            if st.form_submit_button("Criar Contrato"):
                if selected_customer_name and selected_equipment_names and valor_total > 0:
                    if end_date < start_date:
                        st.warning("A data final não pode ser anterior à data de início.")
                    else:
                        customer_id = customers_df[customers_df['full_name'] == selected_customer_name]['customer_id'].iloc[0]
                        equipment_ids_to_rent = available_equipment[available_equipment['name'].isin(selected_equipment_names)]['equipment_id'].tolist()
                        valor_per_item = valor_total / len(equipment_ids_to_rent)
                        success, message = add_rentals_to_db(user_id, customer_id, equipment_ids_to_rent, start_date, end_date, valor_per_item, freight_cost)
                        if success:
                            if "freight_cost_to_contract" in st.session_state:
                                del st.session_state.freight_cost_to_contract
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.warning("Por favor, preencha todos os campos.")

# --- View Rentals ---
st.header("Gerenciar Aluguéis")

def display_rentals(df, title):
    st.subheader(title)
    if not df.empty:
        for index, row in df.iterrows():
            is_overdue = pd.to_datetime(row['end_date']).date() < datetime.now().date() and row['status_rental'] == 'Ativo'
            with st.container(border=True):
                c1, c2, c3 = st.columns([2,1,1])
                with c1:
                    st.markdown(f"**Equipamento:** {row['name']} | **Cliente:** {row['full_name']}")
                    st.markdown(f"**Valor do Aluguel:** R$ {row['valor']:.2f} | **Custo do Frete:** R$ {float(row['freight_cost'] or 0.0):.2f}")
                    st.markdown(f"**Devolução:** {pd.to_datetime(row['end_date']).strftime('%d/%m/%Y')} {'<span style=\'color:red;\'><b>(ATRASADO)</b></span>' if is_overdue else ''}", unsafe_allow_html=True)
                with c2:
                    pdf_bytes = create_contract_pdf(row)
                    st.download_button(label="Gerar Contrato", data=pdf_bytes, file_name=f"contrato_{row['rental_id']}.pdf", mime="application/pdf", key=f"pdf_{row['rental_id']}", use_container_width=True)
                with c3:
                    if row['status_rental'] == 'Ativo':
                        if st.button("Marcar como Devolvido", key=f"return_{row['rental_id']}", use_container_width=True):
                            success, message = complete_rental_in_db(row['rental_id'], row['equipment_id'])
                            if success: st.success(message); st.rerun()
                            else: st.error(message)
                
                st.markdown("---")
                st.markdown("**Contrato Assinado:**")
                doc_url = row.get('signed_contract_path')
                if doc_url and isinstance(doc_url, str):
                    st.link_button("Ver Contrato Assinado", doc_url)
                else:
                    st.info("Nenhum contrato assinado foi enviado para este aluguel.")
                
                uploader_key = f"signed_{row['rental_id']}"
                st.file_uploader("Carregar Contrato Assinado", type=['pdf', 'png', 'jpg', 'jpeg'], key=uploader_key, on_change=handle_contract_upload, args=(row['rental_id'], uploader_key))
    else:
        st.info(f"Nenhum aluguel na seção '{title}'.")

if rentals_df.empty:
    st.info("Nenhum contrato encontrado para a seleção atual.")
else:
    all_rentals_merged = rentals_df.merge(customers_df, on="customer_id").merge(equipment_df, on="equipment_id", suffixes=('_rental', '_equip'))
    active_rentals = all_rentals_merged[all_rentals_merged['status_rental'] == 'Ativo']
    completed_rentals = all_rentals_merged[all_rentals_merged['status_rental'] == 'Concluído']
    
    display_rentals(active_rentals, "Aluguéis Ativos e Atrasados")
    display_rentals(completed_rentals, "Histórico de Aluguéis Concluídos")
