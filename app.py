import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import unicodedata

# Configuração da página
st.set_page_config(
    page_title="Monitor de Licitações - Geotecnologias",
    page_icon="🗺️",
    layout="wide"
)

# Função para gerar variações (com e sem acento) de um termo
def gerar_variacoes(texto):
    sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return list(set([texto.lower(), sem_acento.lower()]))

# Lista base de termos
TERMOS_BASE = [
    "engenharia cartografica", "geoprocessamento", "aerolevantamento",
    "aerofotogrametria", "georreferenciamento urbano", "planta generica de valores",
    "pgv", "cadastro imobiliario", "lidar", "ortofotos", "vetorizacao cartografica",
    "recadastramento urbano", "gestao territorial", "demarcacao topografica",
    "regularizacao fundiaria"
]

st.title("🗺️ Monitor de Licitações Públicas - Geotecnologias")
st.markdown("Varredura abrangente no **PNCP, BLL, Compras.gov, Licitações-e** (Editais Abertos e Recebendo Propostas).")

# Barra Lateral
st.sidebar.header("⚙️ Configurações")

# Horários de atualização
hora_atual = datetime.now().hour
if hora_atual < 8:
    prox = "08:00"
elif hora_atual < 12:
    prox = "12:00"
elif hora_atual < 17:
    prox = "17:00"
else:
    prox = "08:00 (amanhã)"

st.sidebar.info(f"🕒 **Varreduras programadas:** 08h | 12h | 17h\nPróxima atualização: **{prox}**")

if st.sidebar.button("🔄 Forçar Atualização Agora"):
    st.cache_data.clear()
    st.rerun()

status_proposta = st.sidebar.selectbox(
    "Status dos Editais",
    ["recebendo_proposta", "aberta", "todos"],
    index=0
)

# Função de busca usando a API de pesquisa textual do PNCP (com e sem acento)
@st.cache_data(ttl=1800)
def buscar_pncp(termo, status):
    url = "https://pncp.gov.br/api/search/"
    
    # Parâmetros exatos que o portal do PNCP usa na busca da web
    params = {
        "q": termo,
        "tipos_documento": "edital",
        "pagina": 1,
        "tam_pagina": 50
    }
    if status != "todos":
        params["status"] = status

    try:
        response = requests.get(url, params=params, timeout=12)
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except Exception:
        return []

# Execução da busca para todas as palavras-chave (com e sem acento)
resultados = []
urls_vistas = set()

with st.spinner("Consultando PNCP, BLL, Compras.gov.br e Licitações-e..."):
    for t_base in TERMOS_BASE:
        # Gera variações com e sem acento
        variacoes = gerar_variacoes(t_base)
        for termo in variacoes:
            itens = buscar_pncp(termo, status_proposta)
            for item in itens:
                # Extrai dados do resultado do PNCP
                title = item.get("title") or item.get("description") or "Sem título"
                link = item.get("url") or item.get("link") or ""
                orgao = item.get("orgao_razao_social") or item.get("orgao_nome") or "Órgão Não Informado"
                
                # Se não houver link direto no objeto, monta o link padrão do edital
                if not link and "id" in item:
                    link = f"https://pncp.gov.br/app/editais/{item.get('id')}"
                elif not link:
                    link = f"https://pncp.gov.br/app/editais?q={termo}&status={status_proposta}"

                if link not in urls_vistas:
                    urls_vistas.add(link)
                    resultados.append({
                        "Termo": t_base.upper(),
                        "Orgao": orgao,
                        "Objeto": title,
                        "Data": item.get("data_publicacao", "Consulte no site"),
                        "Link": link
                    })

df = pd.DataFrame(resultados)

# Exibição das Métricas
col1, col2 = st.columns(2)
col1.metric("Licitações Encontradas", len(df))
col2.metric("Termos Monitorados", len(TERMOS_BASE))

st.markdown("---")

if not df.empty:
    st.subheader("📋 Licitações Encontradas")
    
    filtro_pesquisa = st.text_input("🔍 Filtrar resultados na tela:", "")
    if filtro_pesquisa:
        df = df[df['Orgao'].str.contains(filtro_pesquisa, case=False, na=False) | 
                df['Objeto'].str.contains(filtro_pesquisa, case=False, na=False)]
    
    for idx, row in df.iterrows():
        with st.expander(f"🔹 [{row['Termo']}] {row['Orgao']}"):
            st.write(f"**Objeto / Resumo:** {row['Objeto']}")
            st.write(f"**Data:** {row['Data']}")
            st.markdown(f"🔗 **[Abrir Edital / Proposta no PNCP]({row['Link']})**", unsafe_allow_html=True)
            
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Resultados (CSV)",
        data=csv,
        file_name=f"licitacoes_geotec_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("Nenhuma licitação encontrada no momento para os termos exatos com status 'Recebendo Proposta'. Experimente mude o campo 'Status dos Editais' na barra lateral para 'todos'.")
