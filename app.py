import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
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
    .destaque-hoje { background-color: #e0f2fe; padding: 10px; border-radius: 6px; border-left: 5px solid #0284c7; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# Função para remover acentos para busca flexível
def normalizar(texto):
    if not texto:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
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
st.markdown("<p style='text-align: center; color: #6b7280; margin-bottom: 30px;'>Varredura em tempo real baseada estritamente na Data de Publicação</p>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("Painel de Controle")

# Filtro opcional de Ano baseado estritamente na Data de Publicação
ano_opcao = st.sidebar.selectbox(
    "Filtrar por Ano de Publicação",
    ["2026 (Ano Atual)", "2025", "Todos os Anos"],
    index=0
)

# Seleção de Categoria / Status
status_opcao = st.sidebar.selectbox(
    "Filtro de Fase / Status",
    ["Abertas / Recebendo Proposta", "Em Julgamento / Encerradas / Canceladas-Revogadas", "Todos os Status"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.text("Atualizações automáticas:\n08h | 12h | 17h")

if st.sidebar.button("Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

# Função de busca textual direta na API de pesquisa do PNCP
@st.cache_data(ttl=300)
def buscar_termo_pncp(termo):
    url = "https://pncp.gov.br/api/search/"
    params = {
        "q": termo,
        "tipos_documento": "edital",
        "pagina": 1,
        "tam_pagina": 40
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except Exception:
        return []

# Coleta de dados com foco rigoroso na Data de Publicação
resultados = []
urls_vistas = set()
hoje_str = date.today().strftime("%Y-%m-%d")

with st.spinner("Varrendo portais e filtrando por Data de Publicação oficial..."):
    for t_base in TERMOS_OFICIAIS:
        variacoes = set([t_base, normalizar(t_base)])
        for termo_busca in variacoes:
            itens = buscar_termo_pncp(termo_busca)
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
                
                # CAPTURA OFICIAL DA DATA DE PUBLICAÇÃO
                data_pub = item.get("data_publicacao") or item.get("dataPublicacaoPncp") or item.get("data_inclusao") or ""

                # Se não houver data de publicação clara, descartamos para evitar itens antigos lixo (2022, 2023)
                if not data_pub:
                    continue

                # Extração rigorosa do ano com base na Data de Publicação
                ano_detectado = ""
                data_formatada = ""
                try:
                    dt = datetime.fromisoformat(str(data_pub).replace("Z", ""))
                    ano_detectado = str(dt.year)
                    data_formatada = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    ano_detectado = str(data_pub)[:4]
                    data_formatada = str(data_pub)

                # Identificação de Status
                situacao_api = str(item.get("situacao_encontrada") or item.get("status") or "").lower()
                titulo_lower = titulo.lower()
                
                if "cancelada" in situacao_api or "revogada" in situacao_api or "cancelada" in titulo_lower or "revogada" in titulo_lower:
                    fase_atual = "Cancelada / Revogada"
                elif "julgamento" in situacao_api or "analise" in situacao_api or "habilitacao" in situacao_api:
                    fase_atual = "Em Julgamento"
                elif "encerrada" in situacao_api or "homologada" in situacao_api or "concluida" in situacao_api:
                    fase_atual = "Encerrada"
                else:
                    fase_atual = "Abertas / Recebendo Proposta"
                
                # Verifica se foi publicado hoje
                is_hoje = False
                if str(data_pub).startswith(hoje_str):
                    is_hoje = True

                if link not in urls_vistas:
                    urls_vistas.add(link)
                    resultados.append({
                        "Termo": t_base.upper(),
                        "Orgao": orgao,
                        "Objeto": titulo,
                        "Valor": valor,
                        "DataOriginal": data_pub,
                        "DataExibicao": data_formatada,
                        "Ano": ano_detectado,
                        "Portal": portal_origem,
                        "Fase": fase_atual,
                        "PublicadoHoje": is_hoje,
                        "Link": link
                    })

df = pd.DataFrame(resultados)

# Aplicação do Filtro Opcional de Ano baseado estritamente na Data de Publicação
if not df.empty:
    if ano_opcao == "2026 (Ano Atual)":
        df = df[df['Ano'] == "2026"]
    elif ano_opcao == "2025":
        df = df[df['Ano'] == "2025"]

# Aplicação do Filtro de Status
if not df.empty:
    if status_opcao == "Abertas / Recebendo Proposta":
        df = df[df['Fase'] == "Abertas / Recebendo Proposta"]
    elif status_opcao == "Em Julgamento / Encerradas / Canceladas-Revogadas":
        df = df[df['Fase'].isin(["Em Julgamento", "Encerrada", "Cancelada / Revogada"])]

# Ordenação Cronológica Estrita baseada na Data de Publicação (Mais recente no topo)
if not df.empty:
    df = df.sort_values(by="DataOriginal", ascending=False, na_position='last').reset_index(drop=True)

total_hoje = len(df[df['PublicadoHoje'] == True]) if not df.empty else 0

# Métricas Visuais
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Licitações Listadas", len(df))
col_m2.metric("Publicadas Hoje", total_hoje)
col_m3.metric("Filtro de Ano", ano_opcao)
col_m4.metric("Termos Monitorados", len(TERMOS_OFICIAIS))

st.markdown("---")

if not df.empty:
    # Seção de destaque para publicações de hoje
    df_hoje = df[df['PublicadoHoje'] == True]
    if not df_hoje.empty:
        st.subheader("🔥 Publicados Hoje (Data de Divulgação)")
        for idx, row in df_hoje.iterrows():
            valor_str = f"R$ {row['Valor']:,.2f}" if row['Valor'] > 0 else "Valor sob Consulta / Não Informado"
            st.markdown(f"""
                <div class="destaque-hoje">
                    <b>[{row['Termo']}] {row['Orgao']}</b><br>
                    📦 {row['Objeto']}<br>
                    📅 <b>Data de Publicação: {row['DataExibicao']}</b> | 💰 {valor_str} | 🌐 {row['Portal']} | 📌 <i>{row['Fase']}</i><br>
                    🔗 <a href="{row['Link']}" target="_blank">Acessar Edital Oficial</a>
                </div>
            """, unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("📋 Lista Geral de Editais e Avisos")
    
    filtro_texto = st.text_input("Filtrar resultados por palavra-chave, órgão ou portal:", "")
    if filtro_texto:
        df = df[df['Orgao'].str.contains(filtro_texto, case=False, na=False) | 
                df['Objeto'].str.contains(filtro_texto, case=False, na=False) |
                df['Portal'].str.contains(filtro_texto, case=False, na=False) |
                df['Fase'].str.contains(filtro_texto, case=False, na=False)]
    
    for idx, row in df.iterrows():
        valor_str = f"R$ {row['Valor']:,.2f}" if row['Valor'] > 0 else "Valor sob Consulta / Não Informado"
        badge_hoje = " 🔥 [PUBLICADO HOJE]" if row['PublicadoHoje'] else ""
        
        with st.expander(f"[{row['Termo']}] {row['Orgao']} — Pub: {row['DataExibicao']} — {row['Fase']}{badge_hoje} — {valor_str}"):
            st.markdown(f"**Órgão:** {row['Orgao']}")
            st.markdown(f"**Objeto:** {row['Objeto']}")
            st.markdown(f"**📅 Data de Publicação Oficial:** {row['DataExibicao']}")
            st.markdown(f"**Ano (Publicação):** {row['Ano']}")
            st.markdown(f"**Fase Atual:** {row['Fase']}")
            st.markdown(f"**Portal de Origem:** {row['Portal']}")
            st.markdown(f"**[Acessar Edital Oficial]({row['Link']})**", unsafe_allow_html=True)
            
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Baixar Relatório em Planilha (CSV)",
        data=csv,
        file_name=f"licitacoes_esteio_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("Nenhum edital encontrado com os filtros selecionados no momento.")
