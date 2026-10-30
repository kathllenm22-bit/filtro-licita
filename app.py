import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import unicodedata

# Configuração da Página
st.set_page_config(
    page_title="Monitor de Licitações - Geotecnologias",
    page_icon="🗺️",
    layout="wide"
)

# Função para remover acentos e normalizar texto para comparação flexível
def normalizar_texto(texto):
    if not texto:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto.lower())
        if unicodedata.category(c) != 'Mn'
    )

# Palavras-chave oficiais de Geotecnologias e Engenharia Cartográfica
KEYWORDS_ORIGINAIS = [
    "engenharia cartografica", "geoprocessamento", "aerolevantamento",
    "aerofotogrametria", "georreferenciamento urbano", "planta generica de valores",
    "pgv", "cadastro imobiliario", "lidar", "ortofotos", "vetorizacao cartografica",
    "recadastramento urbano", "gestao territorial", "demarcacao topografica",
    "regularizacao fundiaria"
]

st.title("🗺️ Monitor de Licitações Públicas - Geotecnologias")
st.markdown("Plataforma automatizada para varredura e filtro de editais no **PNCP (Portal Nacional de Contratações Públicas)**.")

# Barra Lateral (Filtros e Atualização)
st.sidebar.header("⚙️ Configurações & Filtros")

# Controle de horário de atualização programada (8h, 12h, 17h)
agora = datetime.now()
hora_atual = agora.hour
if hora_atual < 12:
    proxima_atualizacao = "12:00"
elif hora_atual < 17:
    proxima_atualizacao = "17:00"
else:
    proxima_atualizacao = "08:00 (amanhã)"

st.sidebar.info(f"🕒 **Horários deVarredura:** 08h, 12h, 17h\nPróxima atualização programada: **{proxima_atualizacao}**")

dias_busca = st.sidebar.slider("Período de busca (Dias atrás)", min_value=1, max_value=90, value=60)

if st.sidebar.button("🔄 Atualizar Dados Agora"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.subheader("Termos Monitorados")
termos_ativos = []
for kw in KEYWORDS_ORIGINAIS:
    if st.sidebar.checkbox(kw.title(), value=True):
        termos_ativos.append(normalizar_texto(kw))

# Função para buscar dados da API do PNCP de forma abrangente
@st.cache_data(ttl=3600)
def carregar_licitacoes(dias):
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=dias)
    
    base_url = "https://pncp.gov.br/api/consulta/v1/licitacoes"
    
    todos_resultados = []
    # Busca páginas para garantir um volume robusto de editais recentes
    for pagina in range(1, 6): # Varre até 5 páginas
        params = {
            "dataInicial": data_inicio.strftime("%Y%m%d"),
            "dataFinal": data_fim.strftime("%Y%m%d"),
            "pagina": pagina,
            "tamanhoPagina": 100
        }
        try:
            response = requests.get(base_url, params=params, timeout=15)
            if response.status_code == 200:
                dados = response.json().get("resultado", [])
                if not dados:
                    break
                todos_resultados.extend(dados)
            else:
                break
        except Exception:
            break
            
    return todos_resultados

# Carregamento dos dados com spinner
with st.spinner("Varredura ativa no PNCP em busca de editais de geotecnologia..."):
    bruto = carregar_licitacoes(dias_busca)

# Processamento e Filtro Flexível (ignora acentos e maiúsculas/minúsculas)
resultados = []
for lic in bruto:
    objeto_bruto = lic.get("objetoResumido") or lic.get("objeto") or ""
    objeto_norm = normalizar_texto(objeto_bruto)
    
    orgao_nome = lic.get("orgaoEntidade", {}).get("razaoSocial", "")
    
    for kw in termos_ativos:
        # Verifica se o termo normalizado está contido no objeto ou no nome do órgão
        if kw in objeto_norm or kw in normalizar_texto(orgao_nome):
            cnpj = lic.get("orgaoEntidade", {}).get("cnpj", "")
            ano = lic.get("ano", "")
            seq = lic.get("sequencial", "")
            link = f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"
            
            if not any(r['Link'] == link for r in resultados):
                resultados.append({
                    "Orgao": orgao_nome or "Órgão não informado",
                    "Objeto": objeto_bruto,
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
col2.metric("Termos Ativos", len(termos_ativos))
col3.metric("Período Analisado", f"Últimos {dias_busca} dias")

st.markdown("---")

# Exibição dos Resultados
if not df.empty:
    st.subheader("📋 Editais Localizados")
    
    filtro_texto = st.text_input("🔍 Filtrar na tabela por órgão ou palavra-chave:", "")
    if filtro_texto:
        df = df[df['Orgao'].str.contains(filtro_texto, case=False, na=False) | 
                df['Objeto'].str.contains(filtro_texto, case=False, na=False)]
    
    for index, row in df.iterrows():
        valor_str = f"R$ {row['ValorEstimado']:,.2f}" if row['ValorEstimado'] > 0 else "Valor Sigiloso / Não Informado"
        with st.expander(f"🔹 [{row['Termo']}] {row['Orgao']} — {valor_str}"):
            st.write(f"**Objeto Completo:** {row['Objeto']}")
            st.markdown(f"**Modalidade:** {row['Modalidade']}")
            st.markdown(f"**Abertura das Propostas:** {row['DataAbertura']}")
            st.markdown(f"🔗 **[Acessar Licitação Oficial no Portal do PNCP]({row['Link']})**", unsafe_allow_html=True)
            
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Resultados em Planilha (CSV)",
        data=csv,
        file_name=f"licitacoes_geotecnologia_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.info("Nenhuma licitação encontrada com os termos selecionados no período atual. A API do PNCP pode estar a retornar poucos editais públicos exatos para estes termos específicos nos últimos dias. Tente usar o botão '🔄 Atualizar Dados Agora' na barra lateral ou aumentar o período para 90 dias.")
