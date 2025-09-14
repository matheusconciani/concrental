import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_cookies_manager import CookieManager
from db_management import (
    verify_user, 
    get_all_equipments, 
    get_all_customers, 
    get_all_rentals,
    update_rental_in_db,
    is_authenticated,
    logout,
    get_user_by_id
)

# --- Page Configuration ---
st.set_page_config(
    page_title="ConcRental - Dashboard",
    layout="wide",
    initial_sidebar_state="auto",
)

# --- Cookie Manager ---
cookies = CookieManager()

# --- Login Logic ---
def login_form():
    """Displays the login form and handles submission."""
    st.title("ConcRental")
    st.subheader("Acesso ao Sistema de Gestão")

    with st.form("login_form"):
        username = st.text_input("Usuário", placeholder="Digite seu usuário")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            user_found, user_id = verify_user(username, password)
            if user_found:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_id = user_id
                cookies['user_id'] = user_id
                cookies.save()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# --- Main Application ---
def main_dashboard():
    """The main dashboard page, shown after login."""
    st.sidebar.title(f"Bem-vindo, {st.session_state.get('username', 'Usuário')}!")
    if st.sidebar.button("Sair"):
        logout(cookies)
    
    st.title("Dashboard Principal")
    st.markdown("Use o menu na barra lateral para navegar pelas seções.")
    st.divider()

    # --- Load live data from DB ---
    user_id = st.session_state.user_id
    equipment_df = get_all_equipments(user_id)
    customers_df = get_all_customers(user_id)
    rentals_df = get_all_rentals(user_id)

    # --- KPIs ---
    st.header("Indicadores de Performance")
    total_items = len(equipment_df)
    rented_items = len(equipment_df[equipment_df['status'] == 'Alugado'])
    available_items = len(equipment_df[equipment_df['status'] == 'Disponível'])
    
    rentals_due_this_week = 0
    if not rentals_df.empty:
        rentals_df['end_date'] = pd.to_datetime(rentals_df['end_date'])
        today = datetime.now().date()
        end_of_week = today + timedelta(days=7)
        rentals_due_this_week = len(rentals_df[
            (rentals_df['end_date'].dt.date >= today) &
            (rentals_df['end_date'].dt.date <= end_of_week) &
            (rentals_df['status'] == 'Ativo')
        ])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Equipamentos Totais", total_items)
    col2.metric("Itens Alugados", rented_items)
    col3.metric("Itens Disponíveis", available_items)
    col4.metric("Devoluções Nesta Semana", rentals_due_this_week)

    st.divider()

    # --- Active Rentals ---
    st.header("Aluguéis Ativos")
    if rentals_df.empty or customers_df.empty or equipment_df.empty:
        st.info("Não há dados suficientes para exibir os aluguéis ativos.")
    else:
        active_rentals = rentals_df[rentals_df['status'] == 'Ativo']
        if not active_rentals.empty:
            merged_df = active_rentals.merge(customers_df, on="customer_id").merge(equipment_df, on="equipment_id")

            for index, row in merged_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Equipamento:** {row['name']} ({row['serial_number']})")
                        st.markdown(f"**Cliente:** {row['full_name']}")
                        st.markdown(f"**Localização:** {row['address']}")
                        st.markdown(f"**Valor:** R$ {row['valor']:.2f}")
                    with c2:
                        payment_options = ["Em Aberto", "Cartão", "Dinheiro", "Parcelado", "Pix"]
                        selected_payment = st.selectbox(
                            "Status Pagamento", options=payment_options, 
                            index=payment_options.index(row['payment_status']),
                            key=f"payment_{row['rental_id']}"
                        )
                        if selected_payment != row['payment_status']:
                            update_rental_in_db(row['rental_id'], 'payment_status', selected_payment)
                            st.rerun()

                        new_end_date = st.date_input(
                            "Data de Devolução", value=pd.to_datetime(row['end_date']).date(),
                            key=f"end_date_{row['rental_id']}"
                        )
                        if new_end_date != pd.to_datetime(row['end_date']).date():
                            update_rental_in_db(row['rental_id'], 'end_date', new_end_date.strftime("%Y-%m-%d %H:%M:%S"))
                            st.rerun()
        else:
            st.info("Nenhum aluguel ativo no momento.")

if __name__ == "__main__":
    if is_authenticated(cookies):
        main_dashboard()
    else:
        login_form()