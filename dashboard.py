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

# Filtrar apenas notas finalizadas
df_filtrado = df[df["Situação"] == "FINALIZADO"]

# Agrupar compras por fornecedor (visão geral)
compras_por_fornecedor = (
    df_filtrado
    .groupby(["Fornecedor", "Razão Social"])["Valor Nota"]
    .sum()
    .reset_index()
    .sort_values(by="Valor Nota", ascending=False)
)

# Agrupar compras por mês e ano (visão geral)
compras_por_mes = df_filtrado.groupby(["ANO", "MÊS"])["Valor Nota"].sum().unstack(level=0)

# Lista de meses para ordenar
ordem_meses = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

# Reordenar a tabela geral de compras mensais (pode usar fill_value=0 se quiser preencher vazios)
if compras_por_mes is not None:
    compras_por_mes = compras_por_mes.reindex(ordem_meses, fill_value=0)

# ------------------------
# 2) Iniciar o app Streamlit
# ------------------------
st.title("📊 Dashboard de Compras")

# --------------------------------
# SEÇÃO 1: TOP 10 FORNECEDORES
# --------------------------------
st.subheader("🔝 Top 10 Fornecedores (Valor Total)")
fig_fornecedores = px.bar(
    compras_por_fornecedor.head(10),
    x="Razão Social",
    y="Valor Nota",
    title="Top 10 Fornecedores - Total de Compras",
    labels={"Valor Nota": "Total Comprado (R$)", "Razão Social": "Fornecedor"},
    text_auto=".2s"
)
fig_fornecedores.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_fornecedores)

# ------------------------------------------------
# SEÇÃO 2: COMPARAÇÃO GERAL (2022 - 2024) - LINHAS
# ------------------------------------------------
st.subheader("📅 Comparação de Compras Mensais (2022-2024)")
fig_compras_mes = px.line(
    compras_por_mes,
    x=compras_por_mes.index,
    y=[2022, 2023, 2024],  # Ajuste conforme os anos desejados
    title="Comparação Mensal de Compras",
    labels={"index": "Mês", "value": "Total Comprado (R$)", "variable": "Ano"},
    markers=True
)
st.plotly_chart(fig_compras_mes)

# ----------------------------------------------------------
# SEÇÃO 3: DETALHAMENTO POR FORNECEDOR E LOJA (Pivot + Total)
# ----------------------------------------------------------
st.subheader("📋 Detalhamento por Fornecedor e Loja")

# 3.1 Selecionar Fornecedor
fornecedores_unicos = df_filtrado["Razão Social"].unique()
fornecedor_selecionado = st.selectbox("Selecione um fornecedor:", fornecedores_unicos)

# 3.2 Selecionar Loja
lojas_unicas = df_filtrado["Loja"].unique()
loja_selecionada = st.selectbox("Selecione a loja:", lojas_unicas)

# 3.3 Filtrar dados
df_fornecedor_loja = df_filtrado[
    (df_filtrado["Razão Social"] == fornecedor_selecionado)
    & (df_filtrado["Loja"] == loja_selecionada)
]

# 3.4 Criar pivot: Soma de "Valor Nota" por MÊS e ANO
resumo_pivot = (
    df_fornecedor_loja
    .groupby(["MÊS", "ANO"])["Valor Nota"]
    .sum()
    .unstack("ANO")
    .fillna(0)
    .reindex(ordem_meses, fill_value=0)  # Ordenar meses
)

# 3.5 Adicionar coluna de TOTAL (soma das colunas)
if not resumo_pivot.empty:
    resumo_pivot["TOTAL"] = resumo_pivot.sum(axis=1)

    # Adicionar linha de TOTAL (soma das linhas)
    resumo_pivot.loc["TOTAL"] = resumo_pivot.sum(numeric_only=True)

# Exibir a tabela final (meses em linhas, anos em colunas + TOTAL)
st.write(f"**Resumo de Compras (Fornecedor: {fornecedor_selecionado} | Loja: {loja_selecionada})**")
if not resumo_pivot.empty:
    st.dataframe(resumo_pivot)
else:
    st.warning("Não há dados para este fornecedor e loja selecionados.")

# 3.6 Gráfico (barras agrupadas) sem a linha/coluna 'TOTAL'
if not resumo_pivot.empty:
    # Remover linha 'TOTAL' antes de plotar
    resumo_pivot_sem_total = resumo_pivot.drop(index="TOTAL", errors="ignore")
    # Remover coluna 'TOTAL' antes de plotar
    if "TOTAL" in resumo_pivot_sem_total.columns:
        resumo_pivot_sem_total = resumo_pivot_sem_total.drop(columns="TOTAL")

    # Converter pivot para formato longo (para Plotly)
    resumo_reset = (
        resumo_pivot_sem_total
        .reset_index()  # MÊS vira coluna
        .melt(id_vars="MÊS", var_name="ANO", value_name="Total")
    )

    fig_resumo_mes_ano = px.bar(
        resumo_reset,
        x="MÊS",
        y="Total",
        color="ANO",
        barmode="group",
        title="Resumo de Compras por Mês e Ano (Fornecedor + Loja)",
        labels={"MÊS": "Mês", "Total": "Total Comprado (R$)", "ANO": "Ano"}
    )
    st.plotly_chart(fig_resumo_mes_ano)
