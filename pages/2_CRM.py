
import streamlit as st
import pandas as pd
import os
import re
from streamlit_cookies_manager import CookieManager
from db_management import (
    get_all_customers,
    add_customer_to_db,
    update_customer_in_db,
    delete_customer_from_db,
    is_authenticated,
    logout,
    geocode_and_update_customer
)
from validate_docbr import CPF, CNPJ
from file_management import upload_file

st.set_page_config(page_title="ConcRental - CRM de Clientes", layout="wide")

cookies = CookieManager()

# --- Autenticação ---
if not is_authenticated(cookies):
    st.error("Por favor, faça o login para acessar esta página.")
    st.stop()

# --- Sidebar ---
st.sidebar.title(f"Bem-vindo, {st.session_state.get('username', 'Usuário')}!")
if st.sidebar.button("Sair"):
    logout(cookies)

st.title("CRM de Clientes")

# --- Load Data from DB ---
user_id = st.session_state.user_id
customers_df = get_all_customers(user_id)

# --- Funções de Callback ---
def handle_doc_upload(customer_id, uploader_key):
    uploaded_file = st.session_state.get(uploader_key)
    if uploaded_file:
        with st.spinner("Fazendo upload do arquivo para a nuvem..."):
            file_url = upload_file(uploaded_file)
        
        if file_url:
            update_customer_in_db(customer_id, {'document_path': file_url})
            st.success("Documento salvo na nuvem com sucesso!")
        else:
            st.error("O upload para a nuvem falhou. Verifique sua conexão e o tamanho do arquivo.")

# --- UI ---
if 'form_success' not in st.session_state:
    st.session_state.form_success = False

st.header("Ações")
col1, col2 = st.columns(2)

with col1:
    with st.expander("Adicionar Novo Cliente", expanded=False):
        if st.session_state.form_success:
            st.success("Cliente adicionado com sucesso!")
            if st.button("Adicionar Outro Cliente"):
                st.session_state.form_success = False
                st.rerun()
        else:
            with st.form(key="add_customer_form"):
                st.subheader("Detalhes do Novo Cliente")
                new_full_name = st.text_input("Nome Completo", placeholder="João da Silva")
                new_company_name = st.text_input("Nome da Empresa (Opcional)", placeholder="Silva Construções Ltda")
                doc_type = st.radio("Tipo de Documento", ["CPF", "CNPJ"], horizontal=True)
                new_doc_number = st.text_input("Número do Documento", placeholder="12345678900")
                new_phone = st.text_input("Telefone", placeholder="(41) 99999-8888")
                new_email = st.text_input("Email", placeholder="joao.silva@email.com")
                new_address = st.text_input("Endereço", placeholder="Rua das Flores, 123, Bairro, Curitiba, PR")

                if st.form_submit_button("Adicionar Cliente"):
                    if not all([new_full_name, new_email, new_doc_number]):
                        st.warning("Por favor, preencha todos os campos obrigatórios (Nome, Email, Documento).")
                    else:
                        doc_number_clean = re.sub(r'\D', '', new_doc_number)
                        is_valid = False
                        if doc_type == "CPF": is_valid = CPF().validate(doc_number_clean)
                        elif doc_type == "CNPJ": is_valid = CNPJ().validate(doc_number_clean)

                        if not is_valid:
                            st.error(f"{doc_type} inválido. Por favor, verifique o número.")
                        else:
                            success, message = add_customer_to_db(user_id, new_full_name, new_company_name, new_phone, new_email, new_address, doc_type, doc_number_clean)
                            if success:
                                st.session_state.form_success = True
                                st.rerun()
                            else:
                                st.error(message)

with col2:
    with st.expander("Deletar Cliente"):
        if not customers_df.empty:
            customer_list = customers_df["full_name"].tolist()
            selected_customer_name_to_delete = st.selectbox("Selecione um cliente para deletar", options=customer_list, index=None)
            if selected_customer_name_to_delete:
                customer_id_to_delete = customers_df[customers_df["full_name"] == selected_customer_name_to_delete]["customer_id"].iloc[0]
                if st.button("Deletar Cliente Selecionado", type="primary"):
                    success, message = delete_customer_from_db(customer_id_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Nenhum cliente para deletar.")

with st.expander("Ações do Cliente (Contratos, Documentos e Coordenadas)"):
    if not customers_df.empty:
        customer_list_actions = customers_df["full_name"].tolist()
        selected_customer_name_actions = st.selectbox("Selecione um cliente para mais ações", options=customer_list_actions, index=None, key="actions_select")

        if selected_customer_name_actions:
            selected_customer_row = customers_df[customers_df["full_name"] == selected_customer_name_actions].iloc[0]
            selected_customer_id = selected_customer_row["customer_id"]
            
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                st.subheader("Contratos")
                if st.button("Ver Contratos do Cliente"):
                    st.session_state.customer_id_filter = selected_customer_id
                    st.switch_page("pages/3_Contratos.py")
            
            with action_col2:
                st.subheader("Documentos")
                doc_url = selected_customer_row.get('document_path')
                if doc_url and isinstance(doc_url, str):
                    st.link_button("Ver Documento Salvo", doc_url)
                else:
                    st.info("Nenhum documento cadastrado.")
                uploader_key = f"uploader_{selected_customer_id}"
                st.file_uploader("Carregar novo documento", type=['pdf', 'png', 'jpg', 'jpeg'], key=uploader_key, on_change=handle_doc_upload, args=(selected_customer_id, uploader_key))

            with action_col3:
                st.subheader("Geolocalização")
                if st.button("Atualizar Coordenadas"):
                    address_to_geocode = selected_customer_row.get('address')
                    with st.spinner("Buscando coordenadas..."):
                        success, message = geocode_and_update_customer(selected_customer_id, address_to_geocode)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("Nenhum cliente cadastrado para selecionar ações.")

st.divider()

st.header("Lista de Clientes")

if customers_df.empty:
    st.info("Nenhum cliente encontrado. Adicione um novo cliente para começar.")
else:
    display_cols = [col for col in customers_df.columns if col not in ['document_path', 'latitude', 'longitude']]
    st.session_state['original_customers_df'] = customers_df.copy()

    edited_df = st.data_editor(
        customers_df,
        use_container_width=True,
        column_order=display_cols,
        column_config={
            "customer_id": st.column_config.TextColumn("ID Cliente", disabled=True),
            "full_name": st.column_config.TextColumn("Nome Completo", required=True),
            "company_name": st.column_config.TextColumn("Nome da Empresa"),
            "phone_number": st.column_config.TextColumn("Telefone"),
            "email_address": st.column_config.TextColumn("Endereço de Email"),
            "address": st.column_config.TextColumn("Endereço"),
            "document_type": st.column_config.TextColumn("Tipo Doc."),
            "document_number": st.column_config.TextColumn("Núm. Doc."),
            "document_path": None,
            "latitude": None,
            "longitude": None
        },
        key="customer_editor"
    )

    if st.button("Salvar Alterações na Lista"):
        original_df = st.session_state.original_customers_df.set_index("customer_id")
        edited_df = edited_df.set_index("customer_id")
        updates_found = False
        for idx in edited_df.index:
            if not original_df.loc[idx].equals(edited_df.loc[idx]):
                updates = edited_df.loc[idx].to_dict()
                update_customer_in_db(idx, updates)
                updates_found = True
        
        if updates_found:
            st.success("Dados dos clientes atualizados com sucesso!")
            st.rerun()
        else:
            st.info("Nenhuma alteração detectada.")
