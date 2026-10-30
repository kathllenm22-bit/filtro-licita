import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Configuração da Página
st.set_page_config(
    page_title="Monitor de Licitações - Geotecnologias & Cartografia",
    page_icon="🗺️",
    layout="wide"
)

# Palavras-chave padrão
KEYWORDS_PADRAO = [
    "engenharia cartografica", "geoprocessamento", "aerolevantamento",
    "aerofotogrametria", "georreferenciamento urbano", "planta generica de valores",
    "pgv", "cadastro imobiliario", "lidar", "ortofotos", "vetorizacao cartografica",
    "recadastramento urbano", "gestao territorial", "demarcacao topografica",
    "regularizacao fundiaria"
]

st.title("🗺️ Monitor de Licitações Públicas - Geotecnologias")
st.markdown("Plataforma automatizada para varredura e filtro de editais no **PNCP (Portal Nacional de Contratações Públicas)**.")

# Barra Lateral (Filtros)
st.sidebar.header("⚙️ Configurações & Filtros")
dias_busca = st.sidebar.slider("Período de busca (Dias atrás)", min_value=1, max_value=30, value=7)

st.sidebar.subheader("Termos de Busca Selecionados")
termos_ativos = []
for kw in KEYWORDS_PADRAO:
    if st.sidebar.checkbox(kw.title(), value=True):
        termos_ativos.append(kw)

# Função para buscar dados da API do PNCP
@st.cache_data(ttl=3600)
def carregar_licitacoes(dias):
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=dias)
    
    base_url = "https://pncp.gov.br/api/consulta/v1/licitacoes"
    params = {
        "dataInicial": data_inicio.strftime("%Y%m%d"),
        "dataFinal": data_fim.strftime("%Y%m%d"),
        "pagina": 1,
        "tamanhoPagina": 100
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json().get("resultado", [])
    except Exception:
        pass
    return []

# Carregamento dos dados
with st.spinner("Consultando dados oficiais no PNCP..."):
    bruto = carregar_licitacoes(dias_busca)

# Processamento e Filtro
resultados = []
for lic in bruto:
    objeto = (lic.get("objetoResumido") or "").lower()
    for kw in termos_ativos:
        if kw in objeto:
            cnpj = lic.get("orgaoEntidade", {}).get("cnpj", "")
            ano = lic.get("ano", "")
            seq = lic.get("sequencial", "")
            link = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"
            
            resultados.append({
                "Orgao": lic.get("orgaoEntidade", {}).get("razaoSocial", "Órgão não informado"),
                "Objeto": lic.get("objetoResumido", ""),
                "DataPublicacao": lic.get("dataPublicacaoPncp", ""),
                "DataAbertura": lic.get("dataAberturaProposta", "Consulte Edital"),
                "ValorEstimado": lic.get("valorTotalEstimado") or 0.0,
                "Modalidade": lic.get("modalidadeNome", "Não informada"),
                "Link": link,
                "Termo": kw.upper()
            })
            break

df = pd.DataFrame(resultados)

# Métricas no Topo
col1, col2, col3 = st.columns(3)
col1.metric("Licitações Encontradas", len(df))
col2.metric("Termos Monitorados", len(termos_ativos))
col3.metric("Período Analisado", f"Últimos {dias_busca} dias")

st.markdown("---")

# Exibição dos Resultados
if not df.empty:
    st.subheader("📋 Editais Localizados")
    
    # Campo de busca extra na tela
    filtro_texto = st.text_input("🔍 Filtrar na tabela por órgão ou palavra-chave:", "")
    if filtro_texto:
        df = df[df['Orgao'].str.contains(filtro_texto, case=False, na=False) | 
                df['Objeto'].str.contains(filtro_texto, case=False, na=False)]
    
    # Tabela interativa
    for index, row in df.iterrows():
        with st.expander(f"🔹 [{row['Termo']}] {row['Orgao']} — R$ {row['ValorEstimado']:,.2f}" if row['ValorEstimado'] > 0 else f"🔹 [{row['Termo']}] {row['Orgao']} — Valor Sigiloso/Não Informado"):
            st.write(f"**Objeto Completo:** {row['Objeto']}")
            st.markdown(f"**Modalidade:** {row['Modalidade']}")
            st.markdown(f"**Abertura das Propostas:** {row['DataAbertura']}")
            st.markdown(f"🔗 **[Acessar Licitação Oficial no Portal do PNCP]({row['Link']})**", unsafe_allow_html=True)
            
    # Botão de Download CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Resultados em Planilha (CSV)",
        data=csv,
        file_name=f"licitacoes_geotecnologia_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.info("Nenhuma licitação encontrada no período selecionado com os termos ativos. Tente aumentar o período de busca na barra lateral.")
