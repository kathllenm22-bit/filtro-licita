import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import unicodedata

# Configuração da página
st.set_page_config(
    page_title="Monitor de Licitações - Esteio",
    page_icon="🗺️",
    layout="wide"
)

# Estilização corporativa limpa
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stExpander { border: 1px solid #d1d5db; border-radius: 6px; margin-bottom: 8px; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    h1 { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 700; color: #1f2937; }
    </style>
""", unsafe_allow_html=True)

# Função para remover acentos para busca flexível
def normalizar(texto):
    if not texto:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()

# Os 15 termos oficiais obrigatórios
TERMOS_OFICIAIS = [
    "engenharia cartografica", "geoprocessamento", "aerolevantamento",
    "aerofotogrametria", "georreferenciamento urbano", "planta generica de valores",
    "pgv", "cadastro imobiliario", "lidar", "ortofotos", "vetorizacao cartografica",
    "recadastramento urbano", "gestao territorial", "demarcacao topografica",
    "regularizacao fundiaria"
]

# --- CABEÇALHO CORPORATIVO COM LOGÓTIPO CENTRALIZADO ---
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    try:
        st.image("logo.png", use_container_width=True)
    except Exception:
        st.info("Envie o ficheiro 'logo.png' para a raiz do repositório no GitHub para exibir o logótipo centralizado.")

st.markdown("<h1 style='text-align: center; font-size: 28px; margin-bottom: 0px;'>Monitor de Licitações & Geotecnologias</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6b7280; margin-bottom: 30px;'>Varredura em tempo real: PNCP, BLL, Compras.gov, Licitações-e e Diários Oficiais</p>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("Painel de Controle")
ano_vigente = "2026"

status_edital = st.sidebar.selectbox(
    "Status dos Editais",
    ["todos", "recebendo_proposta", "aberta"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.text("Atualizações automáticas:\n08h | 12h | 17h")

if st.sidebar.button("Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

# Função de busca textual direta na API de pesquisa do PNCP
@st.cache_data(ttl=300)
def buscar_termo_pncp(termo, status):
    url = "https://pncp.gov.br/api/search/"
    params = {
        "q": termo,
        "tipos_documento": "edital",
        "pagina": 1,
        "tam_pagina": 30
    }
    if status != "todos":
        params["status"] = status

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except Exception:
        return []

# Coleta de dados via pesquisa textual cruzada para 2026
resultados = []
urls_vistas = set()

with st.spinner("Varrendo portais em busca de licitações de 2026..."):
    for t_base in TERMOS_OFICIAIS:
        # Testa a palavra-chave original e a versão sem acento
        variacoes = set([t_base, normalizar(t_base)])
        for termo_busca in variacoes:
            itens = buscar_termo_pncp(termo_busca, status_edital)
            for item in itens:
                titulo = item.get("title") or item.get("description") or "Objeto não detalhado"
                orgao = item.get("orgao_razao_social") or item.get("orgao_nome") or "Órgão Não Informado"
                
                link = item.get("url") or item.get("link") or ""
                pncp_id = item.get("id") or item.get("numeroControlePNCP")
                
                if pncp_id:
                    link = f"https://pncp.gov.br/app/editais/{pncp_id}"
                elif not link or "http" not in link:
                    link = f"https://pncp.gov.br/app/editais?q={termo_busca}"

                portal_origem = "PNCP / Compras.gov.br"
                link_lower = link.lower()
                if "bll" in link_lower or "bllcompras" in link_lower:
                    portal_origem = "BLL Compras"
                elif "licitacoes-e" in link_lower or "bb" in link_lower:
                    portal_origem = "Licitações-e (Banco do Brasil)"
                elif "diario" in link_lower or "imprensa" in link_lower:
                    portal_origem = "Diário Oficial"

                valor = item.get("valor_total_estimado") or item.get("valorTotalEstimado") or 0.0
                data_pub = item.get("data_publicacao") or item.get("dataPublicacaoPncp") or ""

                # Filtro estrito para garantir apenas o ano de 2026
                ano_pub = ano_vigente
                data_formatada = data_pub
                if data_pub:
                    try:
                        dt = datetime.fromisoformat(data_pub.replace("Z", ""))
                        ano_pub = str(dt.year)
                        data_formatada = dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        if len(data_pub) >= 4:
                            ano_pub = data_pub[:4]

                # Rejeita explicitamente 2025 ou anos anteriores
                if ano_pub != ano_vigente:
                    continue

                if link not in urls_vistas:
                    urls_vistas.add(link)
                    resultados.append({
                        "Termo": t_base.upper(),
                        "Orgao": orgao,
                        "Objeto": titulo,
                        "Valor": valor,
                        "DataOriginal": data_pub,
                        "DataExibicao": data_formatada if data_formatada else "Data não informada",
                        "Portal": portal_origem,
                        "Link": link
                    })

df = pd.DataFrame(resultados)

# Ordenação Cronológica Estrita (Do mais recente para o mais antigo - Hoje no topo)
if not df.empty:
    df = df.sort_values(by="DataOriginal", ascending=False, na_position='last').reset_index(drop=True)

# Métricas Visuais
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Licitações 2026 Encontradas", len(df))
col_m2.metric("Termos Monitorados", len(TERMOS_OFICIAIS))
col_m3.metric("Ano de Referência", ano_vigente)

st.markdown("---")

if not df.empty:
    st.subheader("Editais e Avisos Vigentes (2026)")
    
    filtro_texto = st.text_input("Filtrar resultados por palavra-chave, órgão ou portal:", "")
    if filtro_texto:
        df = df[df['Orgao'].str.contains(filtro_texto, case=False, na=False) | 
                df['Objeto'].str.contains(fil_texto, case=False, na=False) |
                df['Portal'].str.contains(filtro_texto, case=False, na=False)]
    
    for idx, row in df.iterrows():
        valor_str = f"R$ {row['Valor']:,.2f}" if row['Valor'] > 0 else "Valor sob Consulta / Não Informado"
        with st.expander(f"[{row['Termo']}] {row['Orgao']} — {row['DataExibicao']} — {valor_str}"):
            st.markdown(f"**Órgão:** {row['Orgao']}")
            st.markdown(f"**Objeto:** {row['Objeto']}")
            st.markdown(f"**Data de Publicação:** {row['DataExibicao']}")
            st.markdown(f"**Portal de Origem:** {row['Portal']}")
            st.markdown(f"**[Acessar Edital Oficial]({row['Link']})**", unsafe_allow_html=True)
            
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Baixar Relatório em Planilha (CSV)",
        data=csv,
        file_name=f"licitacoes_esteio_2026_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("Nenhum edital de 2026 retornado com o status selecionado. Experimente alterar o campo 'Status dos Editais' na barra lateral para 'todos' para ampliar a captura.")
