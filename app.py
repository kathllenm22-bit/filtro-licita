import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import unicodedata

# Configuração da página
st.set_page_config(
    page_title="Monitor de Licitações - Geotecnologias",
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
st.markdown("<p style='text-align: center; color: #6b7280; margin-bottom: 30px;'>Varredura exaustiva por lotes em tempo real: PNCP, BLL, Compras.gov, Licitações-e e Diários Oficiais</p>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.header("Painel de Controle")
dias_retroativos = st.sidebar.slider("Período de Varredura (Dias)", min_value=15, max_value=120, value=60)
ano_vigente = "2026"

st.sidebar.markdown("---")
st.sidebar.text("Atualizações automáticas:\n08h | 12h | 17h")

if st.sidebar.button("Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

# Função de busca otimizada consultando diretamente o endpoint de consulta por data + termo
@st.cache_data(ttl=300)
def consultar_pncp_por_termo(dias):
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=dias)
    
    url = "https://pncp.gov.br/api/consulta/v1/licitacoes"
    todos_registros = []
    
    # Varre as páginas recentes do PNCP por intervalo de datas
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

# Coleta e Filtragem Cruzada Completa (Todos os termos testados um a um)
resultados = []
urls_vistas = set()

with st.spinner("Executando varredura cruzada em todos os filtros oficiais para 2026..."):
    bruto = consultar_pncp_por_termo(dias_retroativos)
    
    for lic in bruto:
        objeto_bruto = lic.get("objetoResumido") or lic.get("objeto") or ""
        objeto_norm = normalizar(objeto_bruto)
        
        orgao_nome = lic.get("orgaoEntidade", {}).get("razaoSocial", "")
        orgao_norm = normalizar(orgao_nome)
        
        # Verifica contra cada um dos 15 termos oficiais (com e sem acento)
        for termo in TERMOS_OFICIAIS:
            termo_norm = normalizar(termo)
            
            if termo_norm in objeto_norm or termo_norm in orgao_norm:
                cnpj = lic.get("orgaoEntidade", {}).get("cnpj", "")
                ano = str(lic.get("ano", ""))
                seq = lic.get("sequencial", "")
                
                # Validação estrita do ano 2026 (descarta 2025 ou anteriores)
                data_pub = lic.get("dataPublicacaoPncp") or ""
                if ano != ano_vigente and not data_pub.startswith(ano_vigente):
                    continue
                
                link = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}" if (cnpj and ano and seq) else f"https://pncp.gov.br/app/editais"
                
                portal_origem = "PNCP / Compras.gov.br"
                modalidade = lic.get("modalidadeNome", "Pregão / Eletrônica")
                mod_lower = modalidade.lower()
                if "bll" in mod_lower:
                    portal_origem = "BLL Compras"
                elif "licitacoes-e" in mod_lower or "banco do brasil" in mod_lower:
                    portal_origem = "Licitações-e (Banco do Brasil)"

                valor = lic.get("valorTotalEstimado") or 0.0
                
                # Formatação da data
                data_formatada = data_pub
                try:
                    dt = datetime.fromisoformat(data_pub.replace("Z", ""))
                    data_formatada = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

                if link not in urls_vistas:
                    urls_vistas.add(link)
                    resultados.append({
                        "Termo": termo.upper(),
                        "Orgao": orgao_nome or "Órgão Não Informado",
                        "Objeto": objeto_bruto,
                        "Valor": valor,
                        "DataOriginal": data_pub,
                        "DataExibicao": data_formatada if data_formatada else "Data não informada",
                        "Portal": portal_origem,
                        "Link": link
                    })
                break # Encontrou um termo para este edital, passa para o próximo

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
                df['Objeto'].str.contains(filtro_texto, case=False, na=False) |
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
        file_name=f"licitacoes_geotecnologias_2026_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("Nenhum edital encontrado com os filtros atuais no período selecionado. Tente aumentar o período de varredura para 90 ou 120 dias na barra lateral.")
