import streamlit as st
import pandas as pd
import plotly.express as px
import os, sys

# ----------------------------
# 1) Carregar e preparar dados
# ----------------------------
file_path = "compras.xlsx"  # Ajuste o caminho do seu arquivo
df = pd.read_excel(file_path, sheet_name="Sheet0")

# Converter colunas de data
df["Data Entra"] = pd.to_datetime(df["Data Entra"], errors="coerce")

# Filtrar apenas notas finalizadas e somente para 2024
df_filtrado = df[(df["Situação"] == "FINALIZADO") & (df["ANO"] == 2024)]

# Agrupar compras por fornecedor (visão geral)
compras_por_fornecedor = (
    df_filtrado
    .groupby(["Fornecedor", "Razão Social"])["Valor Nota"]
    .sum()
    .reset_index()
    .sort_values(by="Valor Nota", ascending=False)
)

# Agrupar compras por mês para 2024 (visão geral)
compras_por_mes = df_filtrado.groupby(["ANO", "MÊS"])["Valor Nota"].sum().unstack(level=0)

# Lista de meses para ordenar
ordem_meses = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

# Reordenar a tabela geral de compras mensais
if compras_por_mes is not None:
    compras_por_mes = compras_por_mes.reindex(ordem_meses, fill_value=0)

# ------------------------
# 2) Iniciar o app Streamlit
# ------------------------
st.title("📊 Dashboard de Compras - Ano 2024")

# --------------------------------
# SEÇÃO 1: TOP 10 FORNECEDORES
# --------------------------------
st.subheader("🔝 Top 10 Fornecedores (Valor Total)")
fig_fornecedores = px.bar(
    compras_por_fornecedor.head(10),
    x="Razão Social",
    y="Valor Nota",
    title="Top 10 Fornecedores - Total de Compras 2024",
    labels={"Valor Nota": "Total Comprado (R$)", "Razão Social": "Fornecedor"},
    text_auto=".2s"
)
fig_fornecedores.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_fornecedores)

# ------------------------------------------------
# SEÇÃO 2: COMPRAS MENSAL - LINHA PARA 2024
# ------------------------------------------------
st.subheader("📅 Compras Mensais - 2024")
if 2024 in compras_por_mes.columns:
    fig_compras_mes = px.line(
        compras_por_mes,
        x=compras_por_mes.index,
        y=[2024],
        title="Compras Mensais - 2024",
        labels={"index": "Mês", "2024": "Total Comprado (R$)"},
        markers=True
    )
    st.plotly_chart(fig_compras_mes)
else:
    st.warning("Não há dados para o ano 2024.")

# ----------------------------------------------------------
# SEÇÃO 3: DETALHAMENTO POR FORNECEDOR E LOJAS (Pivot + Total)
# ----------------------------------------------------------
st.subheader("📋 Detalhamento por Fornecedor e Lojas")

# 3.1 Selecionar Fornecedor
fornecedores_unicos = df_filtrado["Razão Social"].unique()
fornecedor_selecionado = st.selectbox("Selecione um fornecedor:", fornecedores_unicos)

# 3.2 Selecionar múltiplas Lojas
lojas_unicas = df_filtrado["Loja"].unique()
lojas_selecionadas = st.multiselect(
    "Selecione uma ou mais lojas:",
    options=lojas_unicas,
    default=lojas_unicas  # Se quiser começar mostrando todas
)

# 3.3 Filtrar dados (Fornecedor + Lojas selecionadas)
df_fornecedor_loja = df_filtrado[
    (df_filtrado["Razão Social"] == fornecedor_selecionado)
    & (df_filtrado["Loja"].isin(lojas_selecionadas))
]

# 3.4 Criar pivot: Soma de "Valor Nota" por MÊS
resumo_pivot = (
    df_fornecedor_loja
    .groupby(["MÊS"])["Valor Nota"]
    .sum()
    .reset_index()
    .set_index("MÊS")
    .reindex(ordem_meses, fill_value=0)
)

# 3.5 Adicionar coluna e linha de TOTAL
if not resumo_pivot.empty:
    resumo_pivot["TOTAL"] = resumo_pivot.sum(axis=1)
    resumo_pivot.loc["TOTAL"] = resumo_pivot.sum(numeric_only=True)

# Exibir a tabela final
st.write(f"**Resumo de Compras (Fornecedor: {fornecedor_selecionado} | Lojas: {lojas_selecionadas})**")
if not resumo_pivot.empty:
    st.dataframe(resumo_pivot)
else:
    st.warning("Não há dados para este fornecedor e as lojas selecionadas.")

# 3.6 Gráfico (barras agrupadas) sem a linha/coluna 'TOTAL'
if not resumo_pivot.empty:
    # Remover linha e coluna 'TOTAL' antes de plotar
    resumo_pivot_sem_total = resumo_pivot.drop(index="TOTAL", errors="ignore")
    if "TOTAL" in resumo_pivot_sem_total.columns:
        resumo_pivot_sem_total = resumo_pivot_sem_total.drop(columns="TOTAL")
        
    # Converter pivot para formato longo
    resumo_reset = (
        resumo_pivot_sem_total
        .reset_index()
        .melt(id_vars="MÊS", var_name="Variável", value_name="Total")
    )

    fig_resumo_mes = px.bar(
        resumo_reset,
        x="MÊS",
        y="Total",
        color="Variável",
        barmode="group",
        title="Resumo de Compras por Mês (Fornecedor + Lojas)",
        labels={"MÊS": "Mês", "Total": "Total Comprado (R$)"}
    )
    st.plotly_chart(fig_resumo_mes)

# --------------------------------
# SEÇÃO 4: RANKING DE FORNECEDORES
# --------------------------------
st.subheader("🏆 Ranking de Fornecedores em 2024 (≥ 0,3% do total)")

# Para ranking, utilizamos apenas os dados de 2024 (df_filtrado já é filtrado)
ranking = (
    df_filtrado
    .groupby(["Fornecedor", "Razão Social"])["Valor Nota"]
    .sum()
    .reset_index()
)

valor_total_ano = ranking["Valor Nota"].sum()
ranking["Porcentagem"] = (ranking["Valor Nota"] / valor_total_ano) * 100

# Filtrar somente quem tem ≥ 0,3%
ranking = ranking[ranking["Porcentagem"] >= 0.3]

# Ordenar por maior Valor Nota
ranking = ranking.sort_values(by="Valor Nota", ascending=False)

# Criar coluna de Rank (1 = maior valor)
ranking["Rank"] = ranking["Valor Nota"].rank(method="first", ascending=False).astype(int)

# Arredondar porcentagem
ranking["Porcentagem"] = ranking["Porcentagem"].round(2)

# Reordenar colunas para exibir
ranking = ranking[["Rank", "Fornecedor", "Razão Social", "Valor Nota", "Porcentagem"]]

# Exibir tabela
st.write("Fornecedores com pelo menos 0,3% das compras em 2024")
st.dataframe(ranking)
