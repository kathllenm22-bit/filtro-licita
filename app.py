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

# Controlo do período de varredura em dias
dias_busca = st.sidebar.slider("Período de Varredura (Dias)", min_value=15, max_value=90, value=60)

# Filtro opcional de Ano baseado estritamente na Data de Publicação
ano_opcao = st.sidebar.selectbox(
    "Filtrar por Ano de Publicação",
    ["2026 (Ano Atual)", "2025", "Todos os Anos"],
    index=0
)

# Seleção de Categoria / Status
status_opcao = st.sidebar.selectbox(
    "Fase / Status",
    ["Abertas / Recebendo Proposta", "Em Julgamento / Encerradas / Canceladas-Revogadas", "Todos os Status"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.text("Atualizações automáticas:\n08h | 12h | 17h")

if st.sidebar.button("Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

# Função de busca fiável baseada no endpoint de consulta por intervalo de datas do PNCP
@st.cache_data(ttl=300)
def buscar_licitacoes_pncp(dias):
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=dias)
    url = "https://pncp.gov.br/api/consulta/v1/licitacoes"
    todos_registros = []
    
    for pagina in range(1, 6):
        params = {
            "dataInicial": data_inicio.strftime("%Y%m%d"),
            "dataFinal": data_fim.strftime("%Y%m%d"),
            "pagina": pagina,
            "tamanhoPagina": 100
        }
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                dados = response.json().get("resultado", [])
                if not dados:
                    break
                todos_registros.extend(dados)
            else:
                break
        except Exception:
            break
    return todos_registros

# Coleta de dados com foco rigoroso na Data de Publicação e nos 15 termos
resultados = []
urls_vistas = set()
hoje_str = date.today().strftime("%Y-%m-%d")

with st.spinner("A consultar a API oficial do PNCP e a filtrar por Data de Publicação..."):
    bruto = buscar_licitacoes_pncp(dias_busca)
    
    for lic in bruto:
        objeto_bruto = lic.get("objetoResumido") or lic.get("objeto") or ""
        objeto_norm = normalizar(objeto_bruto)
        orgao_nome = lic.get("orgaoEntidade", {}).get("razaoSocial", "") or lic.get("orgaoNome", "")
        orgao_norm = normalizar(orgao_nome)
        
        # Validação cruzada com os 15 termos oficiais
        encontrou_termo = False
        termo_encontrado = ""
        for termo in TERMOS_OFICIAIS:
            t_norm = normalizar(termo)
            if t_norm in objeto_norm or t_norm in orgao_norm:
                encontrou_termo = True
                termo_encontrado = termo.upper()
                break
        
        if not encontrou_termo:
            continue
            
        cnpj = lic.get("orgaoEntidade", {}).get("cnpj", "")
        ano_reg = str(lic.get("ano", ""))
        seq = lic.get("sequencial", "")
        
        link = f"https://pncp.gov.br/app/editais/{cnpj}/{ano_reg}/{seq}" if (cnpj and ano_reg and seq) else f"https://pncp.gov.br/app/editais"
        
        portal_origem = "PNCP / Compras.gov.br"
        modalidade = str(lic.get("modalidadeNome", "")).lower()
        if "bll" in modalidade:
            portal_origem = "BLL Compras"
        elif "licitacoes-e" in modalidade or "banco do brasil" in modalidade:
            portal_origem = "Licitações-e (Banco do Brasil)"
            
        valor = lic.get("valorTotalEstimado") or 0.0
        
        # CAPTURA DA DATA DE PUBLICAÇÃO REAL
        data_pub = lic.get("dataPublicacaoPncp") or lic.get("dataInclusao") or ""
        if not data_pub:
            continue
            
        try:
            dt = datetime.fromisoformat(str(data_pub).replace("Z", ""))
            ano_detectado = str(dt.year)
            data_formatada = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            ano_detectado = str(data_pub)[:4]
            data_formatada = str(data_pub)
            
        situacao = str(lic.get("situacaoCompraNome") or lic.get("status") or "").lower()
        if "cancelada" in situacao or "revogada" in situacao:
            fase_atual = "Cancelada / Revogada"
        elif "julgamento" in situacao or "análise" in situacao or "habilitação" in situacao:
            fase_atual = "Em Julgamento"
        elif "encerrada" in situacao or "homologada" in situacao or "concluída" in situacao:
            fase_atual = "Encerrada"
        else:
            fase_atual = "Abertas / Recebendo Proposta"
            
        is_hoje = str(data_pub).startswith(hoje_str)
        
        if link not in urls_vistas:
            urls_vistas.add(link)
            resultados.append({
                "Termo": termo_encontrado,
                "Orgao": orgao_nome or "Órgão Não Informado",
                "Objeto": objeto_bruto,
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

# Aplicação do Filtro Opcional de Ano
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
    st.warning("Nenhum edital encontrado para os filtros selecionados no momento. Tente aumentar o período de varredura (dias) na barra lateral.")
