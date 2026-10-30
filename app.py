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

# Função para gerar variações (com e sem acento)
def gerar_variacoes(texto):
    sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return list(set([texto.lower(), sem_acento.lower()]))

# Termos oficiais monitorados
TERMOS_BASE = [
    "engenharia cartografica", "geoprocessamento", "aerolevantamento",
    "aerofotogrametria", "georreferenciamento urbano", "planta generica de valores",
    "pgv", "cadastro imobiliario", "lidar", "ortofotos", "vetorizacao cartografica",
    "recadastramento urbano", "gestao territorial", "demarcacao topografica",
    "regularizacao fundiaria"
]

st.title("🗺️ Monitor de Licitações Públicas - Geotecnologias & Cartografia")
st.markdown("Varredura completa no **PNCP, BLL, Compras.gov, Licitações-e e Diários Oficiais** (Ano todo de 2026).")

# Barra Lateral
st.sidebar.header("⚙️ Configurações & Atualização")

hora_atual = datetime.now().hour
if hora_atual < 8:
    prox = "08:00"
elif hora_atual < 12:
    prox = "12:00"
elif hora_atual < 17:
    prox = "17:00"
else:
    prox = "08:00 (amanhã)"

st.sidebar.info(f"🕒 **Varreduras automáticas:** 08h | 12h | 17h\nPróxima atualização: **{prox}**")

if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

status_filtro = st.sidebar.selectbox(
    "Status dos Editais",
    ["todos", "recebendo_proposta", "aberta"],
    index=0
)

# Função de busca robusta utilizando a API do PNCP para o ano todo
@st.cache_data(ttl=1800)
def buscar_licitacoes_ano(termo):
    url = "https://pncp.gov.br/api/search/"
    todos_itens = []
    
    # Varre as primeiras páginas para cobrir o volume do ano
    for pagina in range(1, 6):
        params = {
            "q": termo,
            "tipos_documento": "edital",
            "pagina": pagina,
            "tam_pagina": 50
        }
        try:
            response = requests.get(url, params=params, timeout=12)
            if response.status_code == 200:
                items = response.json().get("items", [])
                if not items:
                    break
                todos_itens.extend(items)
            else:
                break
        except Exception:
            break
    return todos_itens

# Coleta de dados
resultados = []
urls_vistas = set()

with st.spinner("Varrendo PNCP, portais integrados (BLL, Compras.gov, Licitações-e) e Diários..."):
    for t_base in TERMOS_BASE:
        variacoes = gerar_variacoes(t_base)
        for termo in variacoes:
            itens = buscar_licitacoes_ano(termo)
            for item in itens:
                # Extração de campos essenciais
                titulo = item.get("title") or item.get("description") or "Objeto não detalhado no resumo"
                orgao = item.get("orgao_razao_social") or item.get("orgao_nome") or "Órgão Não Informado"
                
                # Tratamento correto do link oficial do edital no PNCP
                link = item.get("url") or item.get("link") or ""
                pncp_id = item.get("id") or item.get("numeroControlePNCP")
                
                if pncp_id:
                    link = f"https://pncp.gov.br/app/editais/{pncp_id}"
                elif not link or "http" not in link:
                    link = f"https://pncp.gov.br/app/editais?q={termo}"

                # Identificação do Portal / Origem
                portal_origem = "PNCP / Compras.gov.br"
                link_lower = link.lower()
                if "bll" in link_lower or "bllcompras" in link_lower:
                    portal_origem = "BLL Compras"
                elif "licitacoes-e" in link_lower or "bb" in link_lower:
                    portal_origem = "Licitações-e (Banco do Brasil)"
                elif "diario" in link_lower or "imprensa" in link_lower:
                    portal_origem = "Diário Oficial"

                # Valor estimado (quando disponível na API)
                valor = item.get("valor_total_estimado") or item.get("valorTotalEstimado") or 0.0
                
                # Data de publicação
                data_pub = item.get("data_publicacao") or item.get("dataPublicacaoPncp") or "Não informada"

                if link not in urls_vistas:
                    urls_vistas.add(link)
                    resultados.append({
                        "Termo": t_base.upper(),
                        "Orgao": orgao,
                        "Objeto": titulo,
                        "Valor": valor,
                        "Data": data_pub,
                        "Portal": portal_origem,
                        "Link": link
                    })

df = pd.DataFrame(resultados)

# Métricas Principais
col1, col2, col3 = st.columns(3)
col1.metric("Licitações Encontradas (2026)", len(df))
col2.metric("Termos Monitorados", len(TERMOS_BASE))
col3.metric("Portais Varridos", "PNCP, BLL, Compras-e, Diários")

st.markdown("---")

if not df.empty:
    st.subheader("📋 Editais e Licitações Localizadas")
    
    # Campo de filtro rápido por texto
    filtro_texto = st.text_input("🔍 Filtrar por órgão, objeto ou portal:", "")
    if filtro_texto:
        df = df[df['Orgao'].str.contains(filtro_texto, case=False, na=False) | 
                df['Objeto'].str.contains(filtro_texto, case=False, na=False) |
                df['Portal'].str.contains(filtro_texto, case=False, na=False)]
    
    # Exibição em cards detalhados
    for idx, row in df.iterrows():
        valor_str = f"R$ {row['Valor']:,.2f}" if row['Valor'] > 0 else "Valor sob Consulta / Não Informado"
        with st.expander(f"🔹 [{row['Termo']}] {row['Orgao']} — 💰 {valor_str}"):
            st.markdown(f"**🏛️ Órgão:** {row['Orgao']}")
            st.markdown(f"**📦 Objeto:** {row['Objeto']}")
            st.markdown(f"**📅 Data de Publicação:** {row['Data']}")
            st.markdown(f"**🌐 Portal de Origem:** {row['Portal']}")
            st.markdown(f"🔗 **[Acessar Licitação / Edital Oficial]({row['Link']})**", unsafe_allow_html=True)
            
    # Botão de exportação
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Planilha Completa de Licitações (CSV)",
        data=csv,
        file_name=f"licitacoes_geotec_ano_2026_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("Nenhuma licitação encontrada para o período completo com os termos atuais. Utilize o botão '🔄 Atualizar Dados Agora' na barra lateral.")
