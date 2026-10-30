import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
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
    .destaque-hoje { background-color: #e0f2fe; padding: 12px; border-radius: 6px; border-left: 5px solid #0284c7; margin-bottom: 10px; }
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
st.markdown("<p style='text-align: center; color: #6b7280; margin-bottom: 30px;'>Varredura oficial e filtragem exata por Data de Divulgação no PNCP</p>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("Painel de Controle")

# Filtro simplificado de Data de Divulgação
filtro_data_opcao = st.sidebar.selectbox(
    "Filtrar por Período de Divulgação",
    ["Ano Atual (2026)", "Últimos 30 Dias", "Últimos 7 Dias", "Apenas Hoje", "Todos os Registros"],
    index=0
)

# Filtro de Status / Fase
status_opcao = st.sidebar.selectbox(
    "Fase / Status",
    ["Todos os Status", "Abertas / Recebendo Proposta", "Em Julgamento / Encerradas / Canceladas-Revogadas"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.text("Atualizações automáticas:\n08h | 12h | 17h")

if st.sidebar.button("Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

# Função de busca fiável na API textual do PNCP
@st.cache_data(ttl=300)
def buscar_por_termo(termo):
    url = "https://pncp.gov.br/api/search/"
    itens_totais = []
    
    for pagina in range(1, 4):
        params = {
            "q": termo,
            "tipos_documento": "edital",
            "pagina": pagina,
            "tam_pagina": 50
        }
        try:
            response = requests.get(url, params=params, timeout=12)
            if response.status_code == 200:
                dados = response.json().get("items", [])
                if not dados:
                    break
                itens_totais.extend(dados)
            else:
                break
        except Exception:
            break
    return itens_totais

# Coleta de dados
resultados = []
urls_vistas = set()
hoje = date.today()

with st.spinner("A consultar portais e a aplicar filtros de divulgação..."):
    for termo_base in TERMOS_OFICIAIS:
        variacoes = set([termo_base, normalizar(termo_base)])
        
        for t in variacoes:
            itens = buscar_por_termo(t)
            for item in itens:
                titulo = item.get("title") or item.get("description") or "Objeto não detalhado"
                orgao = item.get("orgao_razao_social") or item.get("orgao_nome") or "Órgão Não Informado"
                
                link = item.get("url") or item.get("link") or ""
                pncp_id = item.get("id") or item.get("numeroControlePNCP")
                
                if pncp_id:
                    link = f"https://pncp.gov.br/app/editais/{pncp_id}"
                elif not link or "http" not in link:
                    link = f"https://pncp.gov.br/app/editais?q={t}"

                portal_origem = "PNCP / Compras.gov.br"
                link_lower = link.lower()
                if "bll" in link_lower or "bllcompras" in link_lower:
                    portal_origem = "BLL Compras"
                elif "licitacoes-e" in link_lower or "bb" in link_lower:
                    portal_origem = "Licitações-e (Banco do Brasil)"
                elif "diario" in link_lower or "imprensa" in link_lower:
                    portal_origem = "Diário Oficial"

                valor = item.get("valor_total_estimado") or item.get("valorTotalEstimado") or 0.0
                
                # Captura limpa da Data de Divulgação (conforme imagem de referência do PNCP)
                data_raw = item.get("data_publicacao") or item.get("dataPublicacaoPncp") or item.get("dataInclusao") or ""
                
                dt_divulgacao = None
                if data_raw:
                    try:
                        dt_divulgacao = datetime.fromisoformat(str(data_raw).replace("Z", ""))
                    except Exception:
                        try:
                            dt_divulgacao = datetime.strptime(str(data_raw)[:10], "%Y-%m-%d")
                        except Exception:
                            pass

                # Se não encontrar uma data válida, assume a data atual para não perder o edital recente
                if not dt_divulgacao:
                    dt_divulgacao = datetime.now()

                data_formatada = dt_divulgacao.strftime("%d/%m/%Y %H:%M")
                ano_detectado = str(dt_divulgacao.year)
                
                # Identificação de Status / Fase
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
                
                is_hoje = (dt_divulgacao.date() == hoje)

                if link not in urls_vistas:
                    urls_vistas.add(link)
                    resultados.append({
                        "Termo": termo_base.upper(),
                        "Orgao": orgao,
                        "Objeto": titulo,
                        "Valor": valor,
                        "DataObj": dt_divulgacao,
                        "DataExibicao": data_formatada,
                        "Ano": ano_detectado,
                        "Portal": portal_origem,
                        "Fase": fase_atual,
                        "PublicadoHoje": is_hoje,
                        "Link": link
                    })

df = pd.DataFrame(resultados)

# --- APLICAÇÃO DOS FILTROS ---
if not df.empty:
    # Filtro por Período de Divulgação
    if filtro_data_opcao == "Apenas Hoje":
        df = df[df['DataObj'].dt.date == hoje]
    elif filtro_data_opcao == "Últimos 7 Dias":
        limite_7 = datetime.now() - timedelta(days=7)
        df = df[df['DataObj'] >= limite_7]
    elif filtro_data_opcao == "Últimos 30 Dias":
        limite_30 = datetime.now() - timedelta(days=30)
        df = df[df['DataObj'] >= limite_30]
    elif filtro_data_opcao == "Ano Atual (2026)":
        df = df[df['Ano'] == "2026"]

    # Filtro por Status
    if status_opcao == "Abertas / Recebendo Proposta":
        df = df[df['Fase'] == "Abertas / Recebendo Proposta"]
    elif status_opcao == "Em Julgamento / Encerradas / Canceladas-Revogadas":
        df = df[df['Fase'].isin(["Em Julgamento", "Encerrada", "Cancelada / Revogada"])]

# Ordenação Cronológica Estrita (Mais recente no topo)
if not df.empty:
    df = df.sort_values(by="DataObj", ascending=False, na_position='last').reset_index(drop=True)

total_hoje = len(df[df['PublicadoHoje'] == True]) if not df.empty else 0

# Métricas Visuais no Topo
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Licitações Listadas", len(df))
col_m2.metric("Divulgadas Hoje", total_hoje)
col_m3.metric("Filtro Ativo", filtro_data_opcao)
col_m4.metric("Termos Monitorados", len(TERMOS_OFICIAIS))

st.markdown("---")

if not df.empty:
    # Seção de destaque para itens publicados hoje
    df_hoje = df[df['PublicadoHoje'] == True]
    if not df_hoje.empty:
        st.subheader("🔥 Divulgados Hoje no PNCP")
        for idx, row in df_hoje.iterrows():
            valor_str = f"R$ {row['Valor']:,.2f}" if row['Valor'] > 0 else "Valor sob Consulta / Não Informado"
            st.markdown(f"""
                <div class="destaque-hoje">
                    <b>[{row['Termo']}] {row['Orgao']}</b><br>
                    📦 {row['Objeto']}<br>
                    📅 <b>Data de Divulgação: {row['DataExibicao']}</b> | 💰 {valor_str} | 🌐 {row['Portal']} | 📌 <i>{row['Fase']}</i><br>
                    🔗 <a href="{row['Link']}" target="_blank">Acessar Edital Oficial no PNCP</a>
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
        badge_hoje = " 🔥 [DIVULGADO HOJE]" if row['PublicadoHoje'] else ""
        
        with st.expander(f"[{row['Termo']}] {row['Orgao']} — Divulgação: {row['DataExibicao']} — {row['Fase']}{badge_hoje} — {valor_str}"):
            st.markdown(f"**Órgão:** {row['Orgao']}")
            st.markdown(f"**Objeto:** {row['Objeto']}")
            st.markdown(f"**📅 Data de Divulgação no PNCP:** {row['DataExibicao']}")
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
    st.warning("Nenhum edital encontrado para o filtro selecionado. Experimente alterar o filtro na barra lateral para 'Ano Atual (2026)' ou 'Todos os Registros'.")
