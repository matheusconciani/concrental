
import streamlit as st
import pandas as pd
from streamlit_cookies_manager import CookieManager
from db_management import (
    get_all_equipments, 
    add_equipment_to_db, 
    update_equipment_in_db, 
    delete_equipment_from_db,
    is_authenticated,
    logout
)

st.set_page_config(page_title="ConcRental - Inventário", layout="wide")

cookies = CookieManager()

# --- Autenticação ---
if not is_authenticated(cookies):
    st.error("Por favor, faça o login para acessar esta página.")
    st.stop()

# --- Sidebar ---
st.sidebar.title(f"Bem-vindo, {st.session_state.get('username', 'Usuário')}!")
if st.sidebar.button("Sair"):
    logout(cookies)

st.title("Gestor de Inventário")

# --- Load Data from DB ---
user_id = st.session_state.user_id
equipment_df = get_all_equipments(user_id)

# --- Display Inventory --- 
st.header("Editar Inventário de Equipamentos")

if equipment_df.empty:
    st.info("Nenhum equipamento encontrado. Adicione um novo equipamento abaixo.")
else:
    st.session_state['original_equipment_df'] = equipment_df.copy()

    edited_df = st.data_editor(
        equipment_df,
        use_container_width=True,
        column_order=("equipment_id", "name", "category", "status", "purchase_status", "times_rented", "serial_number", "acquisition_date"),
        column_config={
            "equipment_id": st.column_config.TextColumn("ID Equipamento", disabled=True),
            "name": st.column_config.TextColumn("Nome", required=True),
            "category": st.column_config.TextColumn("Categoria", required=True),
            "serial_number": st.column_config.TextColumn("Número de Série", required=True),
            "acquisition_date": st.column_config.DateColumn("Data de Aquisição", format="DD/MM/YYYY", required=True),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["Disponível", "Alugado", "Em Manutenção"],
                required=True,
            ),
            "purchase_status": st.column_config.SelectboxColumn(
                "Status da Compra",
                options=["Quitado", "Não Quitado"],
                required=True,
            ),
            "times_rented": st.column_config.NumberColumn("Vezes Alugado", disabled=True)
        },
        key="inventory_editor"
    )

    if st.button("Salvar Alterações no Inventário"):
        original_df = st.session_state.original_equipment_df.set_index("equipment_id")
        edited_df = edited_df.set_index("equipment_id")
        
        updates_found = False
        for idx in edited_df.index:
            if not original_df.loc[idx].equals(edited_df.loc[idx]):
                updates = edited_df.loc[idx].to_dict()
                updates['acquisition_date'] = pd.to_datetime(updates['acquisition_date']).date()
                update_equipment_in_db(idx, updates)
                updates_found = True
        
        if updates_found:
            st.success("Inventário atualizado com sucesso!")
            st.rerun()
        else:
            st.info("Nenhuma alteração detectada.")

st.divider()

# --- Actions Section ---
col1, col2 = st.columns(2)

with col1:
    with st.expander("Adicionar Novo Equipamento"):
        with st.form(key="add_equipment_form", clear_on_submit=True):
            st.subheader("Detalhes do Novo Equipamento")
            new_name = st.text_input("Nome", placeholder="Ex: Betoneira 500L")
            new_category = st.text_input("Categoria", placeholder="Ex: Maquinário Pesado")
            new_serial = st.text_input("Número de Série", placeholder="Ex: SN-12345ABC")
            new_acq_date = st.date_input("Data de Aquisição")
            new_purchase_status = st.selectbox("Status da Compra", ["Não Quitado", "Quitado"])

            if st.form_submit_button("Adicionar Equipamento"):
                if new_name and new_serial and new_category:
                    success, message = add_equipment_to_db(user_id, new_name, new_category, new_serial, new_acq_date, new_purchase_status)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Por favor, preencha todos os campos.")

with col2:
    with st.expander("Deletar Equipamento"):
        if not equipment_df.empty:
            equipment_list = equipment_df["name"] + " (" + equipment_df["serial_number"] + ")"
            selected_equipment = st.selectbox("Selecione um equipamento para deletar", options=equipment_list, index=None)
            
            if selected_equipment:
                equipment_id_to_delete = equipment_df[equipment_list == selected_equipment]["equipment_id"].iloc[0]
                
                if st.button("Deletar Equipamento Selecionado", type="primary"):
                    success, message = delete_equipment_from_db(equipment_id_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Nenhum equipamento para deletar.")
