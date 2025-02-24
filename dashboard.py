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

# Reordenar a tabela geral de compras mensais
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
    y=[2022, 2023, 2024],  # Ajuste conforme os anos disponíveis
    title="Comparação Mensal de Compras",
    labels={"index": "Mês", "value": "Total Comprado (R$)", "variable": "Ano"},
    markers=True
)
st.plotly_chart(fig_compras_mes)

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

# 3.4 Criar pivot: Soma de "Valor Nota" por MÊS e ANO
resumo_pivot = (
    df_fornecedor_loja
    .groupby(["MÊS", "ANO"])["Valor Nota"]
    .sum()
    .unstack("ANO")
    .fillna(0)
    .reindex(ordem_meses, fill_value=0)  # Ordenar meses
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
        .melt(id_vars="MÊS", var_name="ANO", value_name="Total")
    )

    fig_resumo_mes_ano = px.bar(
        resumo_reset,
        x="MÊS",
        y="Total",
        color="ANO",
        barmode="group",
        title="Resumo de Compras por Mês e Ano (Fornecedor + Lojas)",
        labels={"MÊS": "Mês", "Total": "Total Comprado (R$)", "ANO": "Ano"}
    )
    st.plotly_chart(fig_resumo_mes_ano)

# --------------------------------
# SEÇÃO 4: RANKING DE FORNECEDORES
# --------------------------------
st.subheader("🏆 Ranking de Fornecedores por Ano (≥ 0,3% do total)")

# 4.1 Selecionar o ano para o ranking
anos_disponiveis = sorted(df_filtrado["ANO"].unique())
ano_selecionado = st.selectbox("Selecione o ano para Ranking:", anos_disponiveis)

# 4.2 Filtrar somente as notas do ano selecionado
df_ano = df_filtrado[df_filtrado["ANO"] == ano_selecionado]

# 4.3 Agrupar por fornecedor e calcular valor total e porcentagem
ranking = (
    df_ano
    .groupby(["Fornecedor", "Razão Social"])["Valor Nota"]
    .sum()
    .reset_index()
)

valor_total_ano = ranking["Valor Nota"].sum()
ranking["Porcentagem"] = (ranking["Valor Nota"] / valor_total_ano) * 100

# 4.4 Filtrar somente quem tem ≥ 1%
ranking = ranking[ranking["Porcentagem"] >= 0.3]

# Ordenar por maior Valor Nota
ranking = ranking.sort_values(by="Valor Nota", ascending=False)

# Criar coluna de Rank (1 = maior valor)
ranking["Rank"] = ranking["Valor Nota"].rank(method="first", ascending=False).astype(int)

# Opcional: arredondar porcentagem
ranking["Porcentagem"] = ranking["Porcentagem"].round(2)

# Reordenar colunas para exibir
ranking = ranking[["Rank", "Fornecedor", "Razão Social", "Valor Nota", "Porcentagem"]]

# 4.5 Exibir tabela
st.write(f"Fornecedores com pelo menos 1% das compras em {ano_selecionado}")
st.dataframe(ranking)
