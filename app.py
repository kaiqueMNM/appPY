import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import time

# Configuração da página
st.set_page_config(
    page_title="Sistema de Monitoramento de Produtividade",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
    }
    .metric-card {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem;
    }
    .login-container {
        max-width: 400px;
        margin: auto;
        padding: 20px;
        border-radius: 10px;
        background-color: #262730;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 20px;
    }
    .stTextInput>div>div>input {
        background-color: #1E1E1E;
        color: white;
        border: 1px solid #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)

# Inicialização do estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login(username, password):
    if username == "adm" and password == "adm":
        st.session_state.logged_in = True
        return True
    return False

def show_login_page():
    st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <h1>🔐 Login</h1>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            if login(username, password):
                st.success("Login realizado com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos!")

# Lista de colunas esperadas
EXPECTED_COLUMNS = [
    "Id", "Categoria", "Data da ultima movimentação", "Data de abertura",
    "Data de solução", "Título", "Nome do solicitante", "E-mail do solicitante",
    "CPF do solicitante", "Responsável", "Status", "Organização",
    "Departamento", "Times", "Localização", "Tempo de atendimento(horas)",
    "Sla de atendimento", "Sla de solução", "Houve mal uso?",
    "Situação no encerramento"
]

def clean_numeric_column(df, column):
    """Limpa e converte colunas numéricas, tratando diferentes formatos."""
    if column not in df.columns:
        return pd.Series([0.0] * len(df), index=df.index)
    
    def convert_value(x):
        if pd.isna(x):
            return 0.0
        try:
            if isinstance(x, str):
                x = ''.join(c for c in x if c.isdigit() or c in '.,')
                x = x.replace(',', '.')
            return float(x)
        except:
            return 0.0
    
    return df[column].apply(convert_value)

def processar_dados(df):
    try:
        # Limpar e converter colunas numéricas
        df['Tempo de atendimento(horas)'] = clean_numeric_column(df, 'Tempo de atendimento(horas)')
        df['Sla de atendimento'] = clean_numeric_column(df, 'Sla de atendimento')
        df['Sla de solução'] = clean_numeric_column(df, 'Sla de solução')
        
        # Calcular métricas por responsável
        grouped = df.groupby('Responsável')
        
        # Total de chamados
        total_chamados = grouped.size()
        
        # Chamados encerrados
        status_encerrado = df['Status'].str.lower().str.contains('fechado|encerrado|resolvido', 
                                                                case=False, 
                                                                na=False)
        chamados_encerrados = df[status_encerrado].groupby('Responsável').size()
        
        # Garantir que todos os responsáveis tenham valores
        todos_responsaveis = df['Responsável'].unique()
        for resp in todos_responsaveis:
            if resp not in chamados_encerrados:
                chamados_encerrados[resp] = 0
        
        # Calcular taxa de produtividade
        taxa_produtividade = (chamados_encerrados / total_chamados * 100).fillna(0).round(2)
        
        # Tempo médio de atendimento
        tempo_medio = grouped['Tempo de atendimento(horas)'].mean().round(2)
        
        # Criar DataFrame de resultados
        resultados = pd.DataFrame({
            'Total de Chamados': total_chamados,
            'Chamados Encerrados': chamados_encerrados,
            'Taxa de Produtividade (%)': taxa_produtividade,
            'Tempo Médio (horas)': tempo_medio
        })
        
        return resultados
    
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return None

def criar_grafico_status(df, responsavel=None):
    try:
        if responsavel and responsavel != "Todos":
            df = df[df['Responsável'] == responsavel]
        
        status_count = df['Status'].value_counts()
        fig = px.bar(
            x=status_count.index,
            y=status_count.values,
            title='Distribuição de Chamados por Status',
            labels={'x': 'Status', 'y': 'Quantidade'},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    except Exception as e:
        st.error(f"Erro ao criar gráfico: {str(e)}")
        return None

# Verificar login antes de mostrar o conteúdo principal
if not st.session_state.logged_in:
    show_login_page()
else:
    # Título principal
    st.title("🎯 Dashboard de Produtividade")
    
    # Sidebar com upload e filtros
    with st.sidebar:
        st.header("🔧 Configurações")
        
        uploaded_file = st.file_uploader(
            "📤 Carregar planilha Excel",
            type=['xlsx'],
            help="Selecione um arquivo Excel (.xlsx)"
        )
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    if uploaded_file is not None:
        try:
            # Carregar dados
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            
            # Verificar colunas necessárias
            missing_columns = [col for col in EXPECTED_COLUMNS if col not in df.columns]
            if missing_columns:
                st.error(f"⚠️ Colunas ausentes na planilha: {', '.join(missing_columns)}")
            else:
                # Processar dados
                with st.spinner('Processando dados...'):
                    resultados = processar_dados(df)
                
                if resultados is not None:
                    # Filtros na sidebar
                    with st.sidebar:
                        st.subheader("🔍 Filtros")
                        responsavel_selecionado = st.selectbox(
                            "Selecionar Responsável",
                            ["Todos"] + list(df['Responsável'].unique())
                        )
                    
                    # Layout principal
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📊 Métricas de Produtividade")
                        st.dataframe(
                            resultados.style.background_gradient(
                                subset=['Taxa de Produtividade (%)'],
                                cmap='RdYlGn'
                            ),
                            use_container_width=True
                        )
                    
                    with col2:
                        st.subheader("📈 Distribuição de Status")
                        fig = criar_grafico_status(df, responsavel_selecionado)
                        if fig is not None:
                            st.plotly_chart(fig, use_container_width=True)
                    
                    # Métricas resumidas
                    st.subheader("🎯 Resumo Geral")
                    col3, col4, col5 = st.columns(3)
                    
                    with col3:
                        st.metric(
                            "Taxa Média de Produtividade",
                            f"{resultados['Taxa de Produtividade (%)'].mean():.2f}%"
                        )
                    
                    with col4:
                        st.metric(
                            "Tempo Médio de Atendimento",
                            f"{resultados['Tempo Médio (horas)'].mean():.2f}h"
                        )
                    
                    with col5:
                        st.metric(
                            "Total de Chamados",
                            f"{int(resultados['Total de Chamados'].sum())}"
                        )
                    
                    # Exportar relatório
                    with st.sidebar:
                        st.subheader("📑 Exportar Dados")
                        if st.button("Gerar Relatório Excel"):
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                resultados.to_excel(writer, sheet_name='Produtividade')
                                if responsavel_selecionado != "Todos":
                                    df_filtered = df[df['Responsável'] == responsavel_selecionado]
                                else:
                                    df_filtered = df
                                df_filtered.to_excel(writer, sheet_name='Dados Detalhados')
                            
                            output.seek(0)
                            st.download_button(
                                label="📥 Baixar Relatório",
                                data=output,
                                file_name=f"relatorio_produtividade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
        
        except Exception as e:
            st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
            st.error("Por favor, verifique se o arquivo está no formato correto e tente novamente.")
    else:
        # Tela inicial
        st.info("👋 Bem-vindo ao Dashboard de Produtividade!")
        st.markdown("""
            #### Como usar:
            1. Use o botão de upload no menu lateral para carregar sua planilha Excel
            2. A planilha deve conter as seguintes colunas principais:
               - Responsável
               - Status
               - Data de abertura
               - Tempo de atendimento(horas)
            3. Após o upload, você poderá:
               - Visualizar métricas de produtividade
               - Filtrar dados por responsável
               - Exportar relatórios detalhados
        """)
        
        # Exemplo de formato
        st.subheader("📝 Colunas necessárias:")
        st.code("\n".join(EXPECTED_COLUMNS))

eu preciso apenas que você trabalhe no frontend sem influenciar no funcionamento do sistema
