# -*- coding: utf-8 -*-
"""
Conciliação Empréstimo x RAOC x Saldo — arquivo único.

Uso (rodar na pasta onde está este arquivo):
  python conciliacao.py autoteste                 testa tudo com dados inventados
  python conciliacao.py modelo                    cria config_local/config.xlsx + dados de exemplo
  python conciliacao.py diagnostico               confere ambiente e colunas das fontes
  python conciliacao.py conciliar [AAAA-MM-DD]    gera saidas/conciliacao_<data>.xlsx
  python conciliacao.py baseline AAAA-MM-DD       grava a foto das diferenças daquela data

Opcional em todos: --config <caminho do config.xlsx>
Saída das checagens (só OK/FALHOU, nunca valores): resumo_verificacao.txt
Regras de negócio: _ai_context/01-doc-mestre-contexto.md
"""
import argparse
import shutil
import sys
import tempfile
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

VERSAO = "0.1.0"
PASTA_SCRIPT = Path(__file__).resolve().parent
CONFIG_PADRAO = PASTA_SCRIPT / "config_local" / "config.xlsx"

# ---------------------------------------------------------------------------
# Definições
# ---------------------------------------------------------------------------
ABAS_CONFIG = {
    "PARAMETROS": ["nome", "valor"],
    "FONTES": ["apelido", "sistema", "tipo", "caminho_ou_conexao", "aba_ou_consulta"],
    "COLUNAS": ["apelido", "sistema", "coluna_canonica", "coluna_origem"],
    "CONTAS": ["conta_operacional", "conta_emprestimo", "conta_raoc", "grupo",
               "sinal_emprestimo", "sinal_raoc", "ativa"],
    "INDEXADORES": ["valor_origem", "tipo"],
    "FAIXAS_ATRASO": ["faixa", "de_dias", "ate_dias"],
}

CANONICO = {
    "saldo_contabil": {"obrig": ["conta", "saldo"], "opc": ["data_base"]},
    "parcelas": {"obrig": ["operacao", "num_parcela", "conta_operacional", "vencimento",
                           "valor_vencimento"],
                 "opc": ["data_base", "multa", "mora", "raoc_informado", "saldo_parcela",
                         "indexador", "congelada"]},
    "posicao": {"obrig": ["operacao", "conta_operacional", "saldo_devedor"],
                "opc": ["data_base", "indexador", "congelada", "juros_congelados"]},
    "conciliacao_atual": {"obrig": ["conta", "diferenca"], "opc": ["data_base"]},
}

TIPO_COLUNA = {
    "data_base": "data", "vencimento": "data",
    "saldo": "num", "valor_vencimento": "num", "multa": "num", "mora": "num",
    "raoc_informado": "num", "saldo_parcela": "num", "saldo_devedor": "num",
    "diferenca": "num", "juros_congelados": "num",
}
COLUNAS_CONTA = ("conta", "conta_operacional")

PARAM_PADRAO = {
    "data_base": "",
    "tolerancia_conta": 0,
    "tolerancia_operacao": 0,
    "fonte_saldo_devedor": "posicao",        # posicao | parcelas
    "saldo_inclui_multa_mora": "sim",        # o saldo devedor já contém multa e mora?
    "indexador_padrao": "PRE",               # usado quando a fonte não traz indexador
    "sinal_conciliacao_atual": 1,            # 1 ou -1, conforme o sinal da conciliação atual
    "pasta_saidas": "saidas",
    "arquivo_baseline": "baseline/baseline.xlsx",
}

FAIXAS_PADRAO = [
    ("Em dia", 0, 0), ("1-60", 1, 60), ("61-90", 61, 90), ("91-180", 91, 180),
    ("181-360", 181, 360), ("361-3 anos", 361, 1095), ("Mais de 3 anos", 1096, 999999),
]

CHECAGENS = {
    "C1": "Empréstimo contábil x (Σ parcelas no vencimento + multa + mora)",
    "C2": "RAOC contábil x RAOC implícito (Empréstimo da base − saldo devedor)",
    "C2b": "RAOC contábil x coluna de RAOC da base",
    "C3": "Saldo líquido contábil (Empréstimo − RAOC) x saldo devedor da base",
}
ORDEM_STATUS = {"NOVA": 0, "MUDOU": 1, "CONHECIDA": 2, "OK": 3}
COR_STATUS = {"NOVA": "F8CBAD", "MUDOU": "FFD966", "CONHECIDA": "FFF2CC", "OK": "C6EFCE"}
EPS = 1e-9


class ErroConfig(Exception):
    pass


# ---------------------------------------------------------------------------
# Checagens OK/FALHOU (nunca valores)
# ---------------------------------------------------------------------------
class Verificacao:
    def __init__(self, eco=True):
        self.linhas = []
        self.falhas = 0
        self.eco = eco

    def check(self, descricao, ok, diferenca=None):
        txt = f"CHECK {descricao}: {'OK' if ok else 'FALHOU'}"
        if not ok and diferenca is not None:
            txt += f" (diferença {_sinal(diferenca)})"
        if not ok:
            self.falhas += 1
        self.linhas.append(txt)
        if self.eco:
            print(txt)
        return ok

    def info(self, texto):
        self.linhas.append(texto)
        if self.eco:
            print(texto)

    def salvar(self, caminho):
        cabecalho = [f"conciliacao.py v{VERSAO} — {datetime.now():%Y-%m-%d %H:%M}"]
        rodape = [f"RESULTADO: {'TUDO OK' if self.falhas == 0 else 'HÁ CHECAGENS FALHOU'}"]
        Path(caminho).write_text("\n".join(cabecalho + self.linhas + rodape) + "\n",
                                 encoding="utf-8")


def _sinal(x):
    return "positiva" if x > 0 else ("negativa" if x < 0 else "zero")


# ---------------------------------------------------------------------------
# Conversões
# ---------------------------------------------------------------------------
def _s(v):
    """Célula de config -> texto limpo."""
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    t = str(v).strip()
    return t[:-2] if t.endswith(".0") and t[:-2].lstrip("-").isdigit() else t


def _texto(serie):
    out = serie.map(_s)
    return out.astype(object)


def _conta(serie):
    return _texto(serie).str.replace(r"[^0-9A-Za-z]", "", regex=True)


def _numero(serie):
    if pd.api.types.is_numeric_dtype(serie) and not pd.api.types.is_bool_dtype(serie):
        return pd.to_numeric(serie, errors="coerce").astype(float)
    t = serie.map(_s)
    com_virgula = t.str.contains(",", regex=False)
    t = t.where(~com_virgula,
                t.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    t = t.replace("", np.nan)
    return pd.to_numeric(t, errors="coerce").astype(float)


def _data(serie):
    if pd.api.types.is_datetime64_any_dtype(serie):
        out = serie
    else:
        valores = serie.map(lambda v: np.nan if _s(v) == "" else v)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if int(pd.__version__.split(".")[0]) >= 2:
                out = pd.to_datetime(valores, dayfirst=True, errors="coerce", format="mixed")
            else:
                out = pd.to_datetime(valores, dayfirst=True, errors="coerce")
    out = pd.to_datetime(out, errors="coerce")
    if getattr(out.dt, "tz", None) is not None:
        out = out.dt.tz_localize(None)
    return out.dt.normalize().astype("datetime64[ns]")


def _data_param(v, nome):
    if isinstance(v, (pd.Timestamp, datetime)):
        return pd.Timestamp(v).normalize()
    t = _s(v)
    if not t:
        raise ErroConfig(f"Parâmetro {nome} vazio. Informe AAAA-MM-DD.")
    fmt = "%Y-%m-%d" if len(t) >= 10 and t[4] == "-" else "%d/%m/%Y"
    try:
        return pd.Timestamp(datetime.strptime(t[:10], fmt)).normalize()
    except ValueError:
        raise ErroConfig(f"Parâmetro {nome} inválido: use AAAA-MM-DD.")


def _num_param(P, nome):
    try:
        return float(_s(P[nome]).replace(",", "."))
    except ValueError:
        raise ErroConfig(f"Parâmetro {nome} não é número.")


def _sim(v):
    return _s(v).lower() in ("sim", "s", "1", "true", "verdadeiro", "yes", "y")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def ler_config(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroConfig(f"Config não encontrado: {caminho}. Rode: python conciliacao.py modelo")
    abas = pd.read_excel(caminho, sheet_name=None, dtype=object)
    cfg = {}
    for aba, colunas in ABAS_CONFIG.items():
        if aba not in abas:
            raise ErroConfig(f"Aba {aba} não existe no config.")
        df = abas[aba]
        df.columns = [str(c).strip().lower() for c in df.columns]
        faltam = [c for c in colunas if c not in df.columns]
        if faltam:
            raise ErroConfig(f"Aba {aba}: faltam as colunas {faltam}.")
        cfg[aba] = df[colunas].dropna(how="all").reset_index(drop=True)
    P = dict(PARAM_PADRAO)
    for nome, valor in cfg["PARAMETROS"][["nome", "valor"]].itertuples(index=False):
        if _s(nome) and _s(valor) != "":
            P[_s(nome)] = valor
    return cfg, P


def mapa_colunas(cfg, apelido, sistema):
    m = {}
    for a, s, canon, origem in cfg["COLUNAS"].itertuples(index=False):
        if _s(a) == apelido and _s(s) == sistema and _s(origem):
            m[_s(canon)] = _s(origem)
    return m


def preparar_contas(cfg, v):
    c = cfg["CONTAS"].copy()
    for col in ("conta_operacional", "conta_emprestimo", "conta_raoc"):
        c[col] = _conta(c[col])
    c["grupo"] = _texto(c["grupo"])
    c.loc[c["grupo"] == "", "grupo"] = c["conta_emprestimo"]
    c["ativa"] = c["ativa"].map(lambda x: _s(x).lower() not in ("nao", "não", "n", "0", "false"))
    for col in ("sinal_emprestimo", "sinal_raoc"):
        c[col] = _numero(c[col]).fillna(1.0)
    c = c[c["ativa"]].reset_index(drop=True)

    v.check("CONTAS: conta operacional não se repete", not c["conta_operacional"].duplicated().any())
    v.check("CONTAS: conta Empréstimo e RAOC preenchidas",
            not ((c["conta_emprestimo"] == "") | (c["conta_raoc"] == "")).any())
    unico = True
    for conta_col, sinal_col in (("conta_emprestimo", "sinal_emprestimo"), ("conta_raoc", "sinal_raoc")):
        g = c.groupby(conta_col).agg(n_grupo=("grupo", "nunique"), n_sinal=(sinal_col, "nunique"))
        unico &= bool((g <= 1).all().all())
    v.check("CONTAS: cada conta contábil tem um só grupo e um só sinal", unico)
    v.check("CONTAS: nenhuma conta é Empréstimo e RAOC ao mesmo tempo",
            not (set(c["conta_emprestimo"]) & set(c["conta_raoc"])))
    return c


def preparar_indexadores(cfg, v):
    m = {_s(o).upper(): _s(t).upper() for o, t in cfg["INDEXADORES"].itertuples(index=False) if _s(o)}
    v.check("INDEXADORES: tipo é PRE ou POS", all(t in ("PRE", "POS") for t in m.values()))
    return m


def preparar_faixas(cfg, v):
    f = cfg["FAIXAS_ATRASO"].copy()
    if f.empty:
        f = pd.DataFrame(FAIXAS_PADRAO, columns=ABAS_CONFIG["FAIXAS_ATRASO"])
    f["faixa"] = _texto(f["faixa"])
    f["de_dias"] = _numero(f["de_dias"])
    f["ate_dias"] = _numero(f["ate_dias"])
    v.check("FAIXAS_ATRASO: de/até numéricos", not f[["de_dias", "ate_dias"]].isna().any().any())
    return f.sort_values("de_dias").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Leitura das fontes -> modelo canônico
# ---------------------------------------------------------------------------
def _resolver(caminho, raiz):
    p = Path(_s(caminho))
    return p if p.is_absolute() else Path(raiz) / p


def ler_fonte(tipo, caminho, alvo, data_base, raiz, amostra=None):
    tipo = tipo.lower()
    if tipo == "excel":
        return pd.read_excel(_resolver(caminho, raiz), sheet_name=alvo if alvo else 0, nrows=amostra)
    if tipo == "csv":
        arq = _resolver(caminho, raiz)
        for enc in ("utf-8-sig", "latin-1"):
            try:
                return pd.read_csv(arq, sep=";", encoding=enc, dtype=str, nrows=amostra)
            except UnicodeDecodeError:
                continue
    if tipo == "odbc":
        import pyodbc  # só precisa existir se alguma fonte for odbc
        sql = (alvo.replace("{data_base}", data_base.strftime("%Y-%m-%d"))
                   .replace("{data_base_br}", data_base.strftime("%d/%m/%Y")))
        con = pyodbc.connect(caminho)
        try:
            cur = con.cursor()
            cur.execute(sql)
            nomes = [d[0] for d in cur.description]
            linhas = cur.fetchmany(amostra) if amostra else cur.fetchall()
            return pd.DataFrame.from_records([tuple(r) for r in linhas], columns=nomes)
        finally:
            con.close()
    raise ErroConfig(f"Tipo de fonte desconhecido: '{tipo}'. Use excel, csv ou odbc.")


def _vazio(canon, n):
    tipo = TIPO_COLUNA.get(canon, "texto")
    if tipo == "num":
        return pd.Series(np.zeros(n), dtype=float)
    if tipo == "data":
        return pd.Series(pd.NaT, index=range(n), dtype="datetime64[ns]")
    return pd.Series([""] * n, dtype=object)


def _converter(serie, canon, obrigatoria, rotulo, v):
    tipo = TIPO_COLUNA.get(canon, "texto")
    if tipo == "texto":
        out = _conta(serie) if canon in COLUNAS_CONTA else _texto(serie)
        return out.str.upper() if canon == "indexador" else out
    preenchido = serie.map(_s) != ""
    out = _numero(serie) if tipo == "num" else _data(serie)
    v.check(f"{rotulo} valores válidos em {canon}", not bool((preenchido & out.isna()).any()))
    if tipo == "num" and not obrigatoria:
        out = out.fillna(0.0)
    return out


def canonizar(bruto, apelido, sistema, mapa, data_base, v):
    esp = CANONICO[apelido]
    rotulo = f"{apelido}[{sistema or '-'}]"
    faltam = [c for c in esp["obrig"] if c not in mapa]
    nomes = {str(c).strip().upper(): c for c in bruto.columns}
    ausentes = [o for o in mapa.values() if o.strip().upper() not in nomes]
    v.check(f"{rotulo} colunas obrigatórias mapeadas", not faltam)
    v.check(f"{rotulo} colunas mapeadas existem na fonte", not ausentes)
    if faltam or ausentes:
        raise ErroConfig(f"{rotulo}: sem mapeamento para {faltam}; não achadas na fonte {ausentes}.")
    bruto = bruto.reset_index(drop=True)
    df = pd.DataFrame(index=bruto.index)
    for canon in esp["obrig"] + esp["opc"]:
        if canon in mapa:
            df[canon] = _converter(bruto[nomes[mapa[canon].strip().upper()]], canon,
                                   canon in esp["obrig"], rotulo, v).values
        else:
            df[canon] = _vazio(canon, len(bruto)).values
    df["sistema"] = sistema
    if "data_base" in mapa:
        df = df[df["data_base"] == data_base]
        v.check(f"{rotulo} tem linhas na data-base", len(df) > 0)
    for canon in esp["obrig"]:
        if TIPO_COLUNA.get(canon, "texto") == "texto":
            vazio = bool((df[canon] == "").any())
        else:
            vazio = bool(df[canon].isna().any())
        v.check(f"{rotulo} sem vazios em {canon}", not vazio)
    return df.reset_index(drop=True)


def carregar_fontes(cfg, P, data_base, raiz, v):
    partes = {}
    for apelido, sistema, tipo, caminho, alvo in cfg["FONTES"].itertuples(index=False):
        apelido, sistema = _s(apelido), _s(sistema)
        if apelido not in CANONICO:
            raise ErroConfig(f"FONTES: apelido '{apelido}' desconhecido. Use {list(CANONICO)}.")
        bruto = ler_fonte(_s(tipo), _s(caminho), _s(alvo), data_base, raiz)
        df = canonizar(bruto, apelido, sistema, mapa_colunas(cfg, apelido, sistema), data_base, v)
        partes.setdefault(apelido, []).append(df)
    dados = {}
    for apelido, esp in CANONICO.items():
        if apelido in partes:
            dados[apelido] = pd.concat(partes[apelido], ignore_index=True)
        else:
            cols = esp["obrig"] + esp["opc"] + ["sistema"]
            dados[apelido] = pd.DataFrame({c: _vazio(c, 0) for c in cols})
    obrigatorias = ["saldo_contabil", "parcelas"]
    if _s(P["fonte_saldo_devedor"]).lower() == "posicao":
        obrigatorias.append("posicao")
    for apelido in obrigatorias:
        if apelido not in partes:
            raise ErroConfig(f"FONTES: falta uma fonte com apelido '{apelido}'.")
    return dados


# ---------------------------------------------------------------------------
# Cálculo por operação
# ---------------------------------------------------------------------------
def calcular_operacoes(dados, contas, indexadores, faixas, P, data_base, v):
    chave = ["sistema", "operacao"]
    parc = dados["parcelas"].copy()
    pos = dados["posicao"].copy()
    usa_posicao = _s(P["fonte_saldo_devedor"]).lower() == "posicao"
    inclui_encargos = _sim(P["saldo_inclui_multa_mora"])
    tol_op = _num_param(P, "tolerancia_operacao")

    v.check("parcelas sem parcela repetida (sistema, operação, parcela)",
            not parc.duplicated(chave + ["num_parcela"]).any())
    v.check("posição sem operação repetida (sistema, operação)", not pos.duplicated(chave).any())

    parc["encargos"] = parc["multa"] + parc["mora"]
    parc["cong"] = parc["congelada"].map(_sim)
    pos["cong"] = pos["congelada"].map(_sim)
    g = parc.groupby(chave, as_index=False).agg(
        conta_parc=("conta_operacional", "first"),
        n_contas=("conta_operacional", "nunique"),
        qtd_parcelas=("num_parcela", "size"),
        soma_vencimento=("valor_vencimento", "sum"),
        multa_mora=("encargos", "sum"),
        raoc_coluna=("raoc_informado", "sum"),
        soma_saldo_parcela=("saldo_parcela", "sum"),
        idx_parc=("indexador", "first"),
        cong_parc=("cong", "max"),
    )
    vencidas = parc[parc["vencimento"] < data_base]
    antigo = vencidas.groupby(chave, as_index=False).agg(vencimento_mais_antigo=("vencimento", "min"))
    g = g.merge(antigo, on=chave, how="left")

    pg = pos.groupby(chave, as_index=False).agg(
        conta_pos=("conta_operacional", "first"),
        saldo_devedor=("saldo_devedor", "sum"),
        idx_pos=("indexador", "first"),
        cong_pos=("cong", "max"),
        juros_congelados=("juros_congelados", "sum"),
    )
    if usa_posicao:
        ops = g.merge(pg, on=chave, how="outer", indicator=True)
    else:
        ops = g.merge(pg, on=chave, how="left", indicator=True)
    ops["origem"] = ops["_merge"].astype(str).map(
        {"both": "ambas", "left_only": "so_parcelas", "right_only": "so_posicao"})
    ops = ops.drop(columns="_merge")
    for col in ("conta_parc", "conta_pos", "idx_parc", "idx_pos"):
        ops[col] = ops[col].map(_s)
    for col in ("qtd_parcelas", "soma_vencimento", "multa_mora", "raoc_coluna",
                "soma_saldo_parcela", "saldo_devedor", "juros_congelados"):
        ops[col] = pd.to_numeric(ops[col], errors="coerce").fillna(0.0)

    ops["congelada"] = (ops["cong_parc"].fillna(False).astype(bool)
                        | ops["cong_pos"].fillna(False).astype(bool))
    ops["conta_operacional"] = ops["conta_parc"].where(ops["conta_parc"] != "", ops["conta_pos"])
    conflito_conta = ((ops["conta_parc"] != "") & (ops["conta_pos"] != "")
                      & (ops["conta_parc"] != ops["conta_pos"])) | (ops["n_contas"].fillna(1) > 1)

    idx = ops["idx_parc"].where(ops["idx_parc"] != "", ops["idx_pos"])
    idx = idx.where(idx != "", _s(P["indexador_padrao"]).upper())
    ops["indexador"] = idx
    ops["regra"] = idx.map(lambda x: indexadores.get(x, x if x in ("PRE", "POS") else "DESCONHECIDO"))
    idx_desconhecido = ops["regra"] == "DESCONHECIDO"
    v.check("todos os indexadores estão na aba INDEXADORES", not idx_desconhecido.any())

    saldo = ops["saldo_devedor"] if usa_posicao else ops["soma_saldo_parcela"]
    ops["saldo_op"] = saldo + (0.0 if inclui_encargos else ops["multa_mora"])
    # PRE: Empréstimo = parcelas no vencimento + multa + mora; RAOC = Empréstimo − saldo.
    #      Congelada não muda a fórmula: o saldo da base para de crescer e o RAOC implícito cresce junto.
    # POS: juros contratuais vão a D Empréstimo / C Rendas -> Empréstimo = saldo, RAOC = 0.
    #      Congelada: juros vão a D Empréstimo / C RAOC -> Empréstimo = saldo + juros congelados.
    pos_fixada = ops["regra"] == "POS"
    juros_cong = np.where(pos_fixada & ops["congelada"], ops["juros_congelados"], 0.0)
    ops["emprestimo_op"] = np.where(pos_fixada, ops["saldo_op"] + juros_cong,
                                    ops["soma_vencimento"] + ops["multa_mora"])
    ops["raoc_implicito"] = np.where(pos_fixada, juros_cong, ops["emprestimo_op"] - ops["saldo_op"])
    ops["erro_coluna_raoc"] = ops["raoc_coluna"] - ops["raoc_implicito"]
    tem_cruzado = usa_posicao and (ops["soma_saldo_parcela"] != 0).any()
    ops["dif_saldo_cruzado"] = np.where(ops["origem"] == "ambas",
                                        ops["soma_saldo_parcela"] - ops["saldo_devedor"], 0.0) \
        if tem_cruzado else 0.0
    ops["regra"] = np.where(ops["congelada"] & pos_fixada, "POS congelada (provisória)",
                            np.where(ops["congelada"], ops["regra"] + " congelada", ops["regra"]))

    ops["dias_atraso"] = (data_base - ops["vencimento_mais_antigo"]).dt.days.fillna(0).astype(int)
    ops["faixa_atraso"] = "fora das faixas"
    for faixa, de, ate in faixas[["faixa", "de_dias", "ate_dias"]].itertuples(index=False):
        dentro = (ops["dias_atraso"] >= de) & (ops["dias_atraso"] <= ate) & \
                 (ops["faixa_atraso"] == "fora das faixas")
        ops.loc[dentro, "faixa_atraso"] = faixa
    v.check("FAIXAS_ATRASO cobrem todos os dias de atraso",
            not (ops["faixa_atraso"] == "fora das faixas").any())

    mapa = contas[["conta_operacional", "conta_emprestimo", "conta_raoc", "grupo"]]
    ops = ops.merge(mapa, on="conta_operacional", how="left")
    sem_mapa = ops["conta_emprestimo"].isna()
    for col in ("conta_emprestimo", "conta_raoc", "grupo"):
        ops[col] = ops[col].fillna("")
    v.check("todas as contas operacionais estão na aba CONTAS", not sem_mapa.any())

    alertas = {
        "SO_PARCELAS": (ops["origem"] == "so_parcelas") & usa_posicao,
        "SO_POSICAO": ops["origem"] == "so_posicao",
        "CONTA_DIVERGENTE": conflito_conta,
        "SEM_MAPA": sem_mapa,
        "INDEXADOR_DESCONHECIDO": idx_desconhecido,
        "RAOC_NEGATIVO": ops["raoc_implicito"] < -(tol_op + EPS),
        "SALDO_CRUZADO": ops["dif_saldo_cruzado"].abs() > tol_op + 0.005,
    }
    ops["alertas"] = ""
    for nome, mascara in alertas.items():
        ops.loc[mascara, "alertas"] = ops.loc[mascara, "alertas"] + nome + " "
    ops["alertas"] = ops["alertas"].str.strip()
    v.check("operações casadas entre parcelas e posição",
            not (alertas["SO_PARCELAS"] | alertas["SO_POSICAO"]).any())
    v.check("operação na mesma conta em parcelas e posição", not conflito_conta.any())
    if tem_cruzado:
        v.check("saldo da posição = Σ saldo das parcelas (por operação)",
                not alertas["SALDO_CRUZADO"].any())
    v.check("Σ valor no vencimento preservado (fonte x operações)",
            abs(parc["valor_vencimento"].sum() - ops["soma_vencimento"].sum()) < 0.005,
            parc["valor_vencimento"].sum() - ops["soma_vencimento"].sum())

    colunas = ["sistema", "operacao", "conta_operacional", "conta_emprestimo", "conta_raoc", "grupo",
               "indexador", "regra", "congelada", "origem", "qtd_parcelas", "dias_atraso", "faixa_atraso",
               "vencimento_mais_antigo", "soma_vencimento", "multa_mora", "emprestimo_op",
               "saldo_devedor", "soma_saldo_parcela", "saldo_op", "juros_congelados", "raoc_implicito", "raoc_coluna",
               "erro_coluna_raoc", "dif_saldo_cruzado", "alertas"]
    return ops[colunas].sort_values(chave).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Conciliação por conta / grupo
# ---------------------------------------------------------------------------
def conciliar_contas(ops, contabil, contas, v):
    saldo_raw = contabil.groupby("conta")["saldo"].sum()
    ok = ops[ops["conta_emprestimo"] != ""]

    emp = contas.drop_duplicates("conta_emprestimo")[["conta_emprestimo", "grupo", "sinal_emprestimo"]]
    raoc = contas.drop_duplicates("conta_raoc")[["conta_raoc", "grupo", "sinal_raoc"]]
    contas_mapa = set(emp["conta_emprestimo"]) | set(raoc["conta_raoc"])
    faltam_contabil = sorted(contas_mapa - set(saldo_raw.index))
    v.check("toda conta da aba CONTAS existe no saldo contábil", not faltam_contabil)

    def contab(conta, sinal):
        return float(saldo_raw.get(conta, 0.0)) * sinal

    linhas = []
    base_emp = ok.groupby("conta_emprestimo")["emprestimo_op"].sum()
    for conta, grupo, sinal in emp.itertuples(index=False):
        linhas.append(("C1", conta, grupo, contab(conta, sinal), float(base_emp.get(conta, 0.0))))
    base_impl = ok.groupby("conta_raoc")["raoc_implicito"].sum()
    base_col = ok.groupby("conta_raoc")["raoc_coluna"].sum()
    for conta, grupo, sinal in raoc.itertuples(index=False):
        linhas.append(("C2", conta, grupo, contab(conta, sinal), float(base_impl.get(conta, 0.0))))
        linhas.append(("C2b", conta, grupo, contab(conta, sinal), float(base_col.get(conta, 0.0))))
    base_saldo = ok.groupby("grupo")["saldo_op"].sum()
    for grupo in sorted(contas["grupo"].unique()):
        c_emp = sum(contab(c, s) for c, g, s in emp.itertuples(index=False) if g == grupo)
        c_raoc = sum(contab(c, s) for c, g, s in raoc.itertuples(index=False) if g == grupo)
        linhas.append(("C3", grupo, grupo, c_emp - c_raoc, float(base_saldo.get(grupo, 0.0))))

    res = pd.DataFrame(linhas, columns=["checagem", "chave", "grupo", "contabil", "base_operacional"])
    res["diferenca"] = res["contabil"] - res["base_operacional"]

    # identidade: no grupo, C3 = Σ C1 − Σ C2
    por_grupo = res.pivot_table(index="grupo", columns="checagem", values="diferenca",
                                aggfunc="sum").reindex(columns=["C1", "C2", "C3"]).fillna(0.0)
    erro_identidade = (por_grupo["C3"] - (por_grupo["C1"] - por_grupo["C2"])).abs().max()
    v.check("identidade C3 = C1 − C2 em todos os grupos",
            bool(pd.isna(erro_identidade) or erro_identidade < 0.005))
    for col in ("contabil", "base_operacional", "diferenca"):
        res[col] = res[col].round(2)
    return res, faltam_contabil


def aplicar_baseline(res, baseline, tol):
    res = res.merge(baseline, on=["checagem", "chave"], how="left")
    d = res["diferenca"]
    b = res["diferenca_baseline"]
    tem_base = b.notna() & (b.abs() > tol + EPS)
    res["status"] = np.select(
        [d.abs() <= tol + EPS, tem_base & ((d - b).abs() <= tol + EPS), tem_base],
        ["OK", "CONHECIDA", "MUDOU"], "NOVA")
    res["variacao_vs_baseline"] = np.where(tem_base, (d - b.fillna(0.0)).round(2), np.nan)
    res["descricao"] = res["checagem"].map(CHECAGENS)
    res["_ordem"] = res["status"].map(ORDEM_STATUS)
    res["_abs"] = -res["diferenca"].abs()
    res = res.sort_values(["_ordem", "_abs", "checagem", "chave"]).drop(columns=["_ordem", "_abs"])
    return res[["status", "checagem", "chave", "grupo", "contabil", "base_operacional", "diferenca",
                "diferenca_baseline", "variacao_vs_baseline", "motivo", "descricao"]].reset_index(drop=True)


def ler_baseline(arquivo):
    vazio = pd.DataFrame(columns=["checagem", "chave", "diferenca_baseline", "motivo"])
    if not Path(arquivo).exists():
        return vazio
    b = pd.read_excel(arquivo, dtype={"checagem": str, "chave": str, "motivo": str})
    b["chave"] = _texto(b["chave"])
    b["checagem"] = _texto(b["checagem"])
    b["motivo"] = _texto(b["motivo"])
    b = b.rename(columns={"diferenca": "diferenca_baseline"})
    b["diferenca_baseline"] = _numero(b["diferenca_baseline"])
    return b[["checagem", "chave", "diferenca_baseline", "motivo"]]


def validar_conciliacao_atual(atual, res, contas, P, tol, v):
    if atual.empty:
        v.info("CHECK C3 = conciliação atual: PULADO (fonte conciliacao_atual não configurada)")
        return pd.DataFrame()
    sinal = _num_param(P, "sinal_conciliacao_atual")
    conta_grupo = dict(zip(contas["conta_emprestimo"], contas["grupo"]))
    conta_grupo.update(dict(zip(contas["conta_raoc"], contas["grupo"])))
    a = atual.copy()
    a["grupo"] = a["conta"].map(conta_grupo)
    v.check("contas da conciliação atual estão na aba CONTAS", not a["grupo"].isna().any())
    a = a.dropna(subset=["grupo"]).groupby("grupo")["diferenca"].sum() * sinal
    c3 = res[res["checagem"] == "C3"].set_index("chave")["diferenca"]
    val = pd.DataFrame({"diferenca_C3": c3, "diferenca_conciliacao_atual": a}).fillna(0.0)
    val["divergencia"] = (val["diferenca_C3"] - val["diferenca_conciliacao_atual"]).round(2)
    val["bate"] = val["divergencia"].abs() <= tol + EPS
    v.check("C3 = conciliação atual em todos os grupos", bool(val["bate"].all()))
    return val.rename_axis("grupo").reset_index()


def resumo_atraso(ops):
    a = ops[ops["conta_emprestimo"] != ""].groupby(
        ["grupo", "conta_emprestimo", "faixa_atraso", "congelada"], as_index=False).agg(
        qtd_operacoes=("operacao", "size"), emprestimo=("emprestimo_op", "sum"),
        raoc_implicito=("raoc_implicito", "sum"), raoc_coluna=("raoc_coluna", "sum"),
        saldo=("saldo_op", "sum"))
    for col in ("emprestimo", "raoc_implicito", "raoc_coluna", "saldo"):
        a[col] = a[col].round(2)
    return a


# ---------------------------------------------------------------------------
# Excel de saída
# ---------------------------------------------------------------------------
def _formatar(ws, df, status_col=None):
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    ws.freeze_panes = "A2"
    if len(df):
        ws.auto_filter.ref = ws.dimensions
    for i, col in enumerate(df.columns, 1):
        ws.cell(1, i).font = Font(bold=True)
        ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(col)) + 2, 12), 60)
        if len(df) <= 50000 and pd.api.types.is_float_dtype(df[col]):
            for r in range(2, len(df) + 2):
                ws.cell(r, i).number_format = "#,##0.00"
        if len(df) <= 50000 and pd.api.types.is_datetime64_any_dtype(df[col]):
            for r in range(2, len(df) + 2):
                ws.cell(r, i).number_format = "DD/MM/YYYY"
    if status_col and status_col in df.columns:
        j = list(df.columns).index(status_col) + 1
        for r in range(2, len(df) + 2):
            cor = COR_STATUS.get(ws.cell(r, j).value)
            if cor:
                ws.cell(r, j).fill = PatternFill("solid", fgColor=cor)


def gravar_excel(arquivo, abas, raiz_csv):
    Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(arquivo, engine="openpyxl") as w:
        for nome, df in abas.items():
            if len(df) > 1_000_000:
                csv = Path(raiz_csv) / f"{Path(arquivo).stem}_{nome}.csv"
                df.to_csv(csv, sep=";", decimal=",", index=False, encoding="utf-8-sig")
                df = pd.DataFrame({"aviso": [f"Linhas demais para o Excel; gravado em {csv.name}"]})
            df.to_excel(w, sheet_name=nome, index=False)
            _formatar(w.sheets[nome], df, status_col="status" if nome == "RESUMO" else None)


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def executar_conciliacao(config, data_base=None, v=None):
    v = v or Verificacao()
    config = Path(config).resolve()
    raiz = config.parent.parent
    cfg, P = ler_config(config)
    db = _data_param(data_base if data_base else P["data_base"], "data_base")
    tol = _num_param(P, "tolerancia_conta")
    v.info(f"Data-base: {db:%Y-%m-%d}")

    contas = preparar_contas(cfg, v)
    indexadores = preparar_indexadores(cfg, v)
    faixas = preparar_faixas(cfg, v)
    dados = carregar_fontes(cfg, P, db, raiz, v)

    ops = calcular_operacoes(dados, contas, indexadores, faixas, P, db, v)
    res, faltam_contabil = conciliar_contas(ops, dados["saldo_contabil"], contas, v)
    res = aplicar_baseline(res, ler_baseline(_resolver(P["arquivo_baseline"], raiz)), tol)
    validacao = validar_conciliacao_atual(dados["conciliacao_atual"], res, contas, P, tol, v)
    v.check("sem diferenças NOVAS", not (res["status"] == "NOVA").any())
    v.check("sem diferenças conhecidas que MUDARAM", not (res["status"] == "MUDOU").any())

    inconsist = ops[ops["alertas"] != ""][["alertas", "sistema", "operacao", "conta_operacional"]]
    inconsist = inconsist.rename(columns={"alertas": "tipo"})
    extra = pd.DataFrame({"tipo": "CONTA_SEM_SALDO_CONTABIL", "sistema": "", "operacao": "",
                          "conta_operacional": faltam_contabil})
    inconsist = pd.concat([inconsist, extra], ignore_index=True)

    params = pd.DataFrame([("versao", VERSAO), ("executado_em", f"{datetime.now():%Y-%m-%d %H:%M}"),
                           ("data_base_usada", f"{db:%Y-%m-%d}")]
                          + [(k, _s(val)) for k, val in P.items() if k != "data_base"],
                          columns=["nome", "valor"])
    leitura = pd.DataFrame([(k, len(d)) for k, d in dados.items()], columns=["nome", "valor"])
    leitura["nome"] = "linhas_" + leitura["nome"]
    legenda = pd.DataFrame(list(CHECAGENS.items()), columns=["nome", "valor"])
    params = pd.concat([params, leitura.astype({"valor": str}), legenda], ignore_index=True)

    abas = {"RESUMO": res, "OPERACOES": ops, "ATRASO": resumo_atraso(ops),
            "INCONSISTENCIAS": inconsist, "PARAMETROS": params}
    if not validacao.empty:
        abas["VALIDACAO_ATUAL"] = validacao
    pasta = _resolver(P["pasta_saidas"], raiz)
    saida = pasta / f"conciliacao_{db:%Y-%m-%d}.xlsx"
    gravar_excel(saida, abas, pasta)
    v.check("Excel de saída gravado", saida.exists())
    return saida, res, ops, v


def gravar_baseline(config, data_base, eco=True):
    config = Path(config).resolve()
    raiz = config.parent.parent
    cfg, P = ler_config(config)
    db = _data_param(data_base, "data_base")
    saida = _resolver(P["pasta_saidas"], raiz) / f"conciliacao_{db:%Y-%m-%d}.xlsx"
    if not saida.exists():
        raise ErroConfig(f"Não achei {saida.name}. Rode antes: python conciliacao.py conciliar {db:%Y-%m-%d}")
    res = pd.read_excel(saida, sheet_name="RESUMO", dtype={"checagem": str, "chave": str})
    res["chave"] = _texto(res["chave"])
    foto = res[res["diferenca"].round(2).abs() > EPS][["checagem", "chave", "diferenca"]].copy()
    foto["data_base_foto"] = f"{db:%Y-%m-%d}"
    arquivo = _resolver(P["arquivo_baseline"], raiz)
    antigo = ler_baseline(arquivo)
    foto = foto.merge(antigo[["checagem", "chave", "motivo"]], on=["checagem", "chave"], how="left")
    foto["motivo"] = foto["motivo"].fillna("")
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    if arquivo.exists():
        shutil.copy2(arquivo, arquivo.with_name(f"{arquivo.stem}_anterior_{datetime.now():%Y%m%d_%H%M%S}.xlsx"))
    gravar_excel(arquivo, {"BASELINE": foto.reset_index(drop=True)}, arquivo.parent)
    if eco:
        print(f"Baseline gravada: {arquivo}")
    return arquivo


def diagnostico(config):
    v = Verificacao()
    config = Path(config).resolve()
    raiz = config.parent.parent
    linhas = [f"Python {sys.version.split()[0]}", f"pandas {pd.__version__}"]
    try:
        import openpyxl
        linhas.append(f"openpyxl {openpyxl.__version__}")
        v.check("openpyxl instalado", True)
    except ImportError:
        v.check("openpyxl instalado", False)
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        linhas.append(f"pyodbc {pyodbc.version}; drivers: {drivers}")
        v.check("pyodbc instalado", True)
        v.check("driver ODBC do Access disponível", any("Access" in d for d in drivers))
        v.check("driver ODBC Oracle disponível", any("Oracle" in d for d in drivers))
    except ImportError:
        v.check("pyodbc instalado", False)
    cfg, P = ler_config(config)
    db = _data_param(P["data_base"] or datetime.now().strftime("%Y-%m-%d"), "data_base")
    for apelido, sistema, tipo, caminho, alvo in cfg["FONTES"].itertuples(index=False):
        apelido, sistema = _s(apelido), _s(sistema)
        rotulo = f"{apelido}[{sistema or '-'}]"
        try:
            amostra = ler_fonte(_s(tipo), _s(caminho), _s(alvo), db, raiz, amostra=50)
        except Exception as e:  # diagnóstico: mostra o erro e segue para a próxima fonte
            v.check(f"{rotulo} fonte abre", False)
            linhas.append(f"\n[{rotulo}] ERRO ao abrir: {type(e).__name__}: {e}")
            continue
        v.check(f"{rotulo} fonte abre", True)
        linhas.append(f"\n[{rotulo}] colunas (nome: tipo):")
        linhas += [f"  {c}: {t}" for c, t in amostra.dtypes.astype(str).items()]
        nomes = {str(c).strip().upper() for c in amostra.columns}
        mapa = mapa_colunas(cfg, apelido, sistema)
        faltam = [c for c in CANONICO.get(apelido, {}).get("obrig", []) if c not in mapa]
        ausentes = [o for o in mapa.values() if o.strip().upper() not in nomes]
        v.check(f"{rotulo} colunas obrigatórias mapeadas", not faltam)
        v.check(f"{rotulo} colunas mapeadas existem na fonte", not ausentes)
        if faltam:
            linhas.append(f"  sem mapeamento: {faltam}")
        if ausentes:
            linhas.append(f"  mapeadas mas não achadas: {ausentes}")
    arq = raiz / "diagnostico.txt"
    arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"\nMetadados (só nomes e tipos, sem valores) em: {arq}")
    return v


# ---------------------------------------------------------------------------
# Modelo de config + dados de exemplo (inventados)
# ---------------------------------------------------------------------------
def _dados_exemplo(data_base):
    db = pd.Timestamp(data_base)
    dia_antes = db - pd.Timedelta(days=1)
    parcelas_a = pd.DataFrame({
        "DT_REF": [db, db, db, dia_antes],
        "CONTRATO": ["A1", "A1", "A2", "A1"],
        "NR_PARCELA": [1, 2, 1, 1],
        "CONTA": ["EMP01", "EMP01", "EMP02", "EMP01"],
        "DT_VENCTO": [db - pd.Timedelta(days=40), db + pd.Timedelta(days=21),
                      db + pd.Timedelta(days=92), db - pd.Timedelta(days=40)],
        "VL_VENCTO": [110.0, 110.0, 500.0, 999.0],
        "VL_MULTA": [2.0, 0.0, 0.0, 0.0],
        "VL_MORA": [1.0, 0.0, 0.0, 0.0],
        "VL_RAOC": [5.0, 5.0, 50.0, 0.0],
        "VL_PRESENTE": [103.0, 100.0, 450.0, 0.0],
        "INDEXADOR": ["PRE", "PRE", "PRE", "PRE"],
    })
    br = (db + pd.Timedelta(days=30)).strftime("%d/%m/%Y")
    parcelas_b = pd.DataFrame({  # CSV no formato brasileiro (vírgula decimal, dd/mm/aaaa)
        "DATA_REFERENCIA": [db.strftime("%d/%m/%Y")] * 2, "NUM_OPERACAO": ["B1", "B2"],
        "PARC": ["1", "1"], "COD_CONTA": ["EMP03", "EMP03"], "VENCIMENTO": [br, br],
        "VALOR_FUTURO": ["1.000,00", "600,00"], "MULTA": ["", ""], "MORA": ["", ""],
        "RAOC_PARCELA": ["0,00", "0,00"], "VALOR_ATUAL": ["800,00", "500,00"],
        "INDEXADOR": ["CDI", "SELIC"],
    })
    posicao_a = pd.DataFrame({"DT_REF": [db, db], "CONTRATO": ["A1", "A2"],
                              "CONTA": ["EMP01", "EMP02"], "SALDO_DEVEDOR": [203.0, 450.0]})
    posicao_b = pd.DataFrame({"DATA_REFERENCIA": [db.strftime("%d/%m/%Y")] * 2,
                              "NUM_OPERACAO": ["B1", "B2"], "COD_CONTA": ["EMP03", "EMP03"],
                              "SALDO": ["800,00", "500,00"], "CONGELADA": ["N", "S"],
                              "JUROS_CONG": ["", "30,00"]})
    contabil = pd.DataFrame({
        "DATA": [db] * 6,
        "CONTA": ["1.000.001", "1.000.002", "1.000.099", "3.000.001", "3.000.099", "9.999.999"],
        "SALDO": [223.0, 510.0, -80.0, 1330.0, -30.0, 12345.0],
    })
    atual = pd.DataFrame({"CONTA": ["1.000.001", "1.000.002", "3.000.001"],
                          "DIFERENCA": [0.0, 0.0, 0.0]})
    return {"parcelas_a": parcelas_a, "parcelas_b": parcelas_b, "posicao_a": posicao_a,
            "posicao_b": posicao_b, "contabil": contabil, "atual": atual}


def _config_exemplo(data_base, pasta_dados):
    d = Path(pasta_dados)  # relativo à pasta do projeto
    fontes = [
        ("saldo_contabil", "", "excel", str(d / "contabil.xlsx"), ""),
        ("parcelas", "A", "excel", str(d / "parcelas_a.xlsx"), ""),
        ("parcelas", "B", "csv", str(d / "parcelas_b.csv"), ""),
        ("posicao", "A", "excel", str(d / "posicao_a.xlsx"), ""),
        ("posicao", "B", "csv", str(d / "posicao_b.csv"), ""),
        ("conciliacao_atual", "", "excel", str(d / "conciliacao_atual.xlsx"), ""),
    ]
    colunas = [
        ("saldo_contabil", "", "data_base", "DATA"), ("saldo_contabil", "", "conta", "CONTA"),
        ("saldo_contabil", "", "saldo", "SALDO"),
        ("conciliacao_atual", "", "conta", "CONTA"), ("conciliacao_atual", "", "diferenca", "DIFERENCA"),
    ]
    for sis, m in (("A", {"data_base": "DT_REF", "operacao": "CONTRATO", "num_parcela": "NR_PARCELA",
                          "conta_operacional": "CONTA", "vencimento": "DT_VENCTO",
                          "valor_vencimento": "VL_VENCTO", "multa": "VL_MULTA", "mora": "VL_MORA",
                          "raoc_informado": "VL_RAOC", "saldo_parcela": "VL_PRESENTE",
                          "indexador": "INDEXADOR"}),
                   ("B", {"data_base": "DATA_REFERENCIA", "operacao": "NUM_OPERACAO",
                          "num_parcela": "PARC", "conta_operacional": "COD_CONTA",
                          "vencimento": "VENCIMENTO", "valor_vencimento": "VALOR_FUTURO",
                          "multa": "MULTA", "mora": "MORA", "raoc_informado": "RAOC_PARCELA",
                          "saldo_parcela": "VALOR_ATUAL", "indexador": "INDEXADOR"})):
        colunas += [("parcelas", sis, k, val) for k, val in m.items()]
    colunas += [("posicao", "A", "data_base", "DT_REF"), ("posicao", "A", "operacao", "CONTRATO"),
                ("posicao", "A", "conta_operacional", "CONTA"), ("posicao", "A", "saldo_devedor", "SALDO_DEVEDOR"),
                ("posicao", "B", "data_base", "DATA_REFERENCIA"), ("posicao", "B", "operacao", "NUM_OPERACAO"),
                ("posicao", "B", "conta_operacional", "COD_CONTA"), ("posicao", "B", "saldo_devedor", "SALDO"),
                ("posicao", "B", "congelada", "CONGELADA"), ("posicao", "B", "juros_congelados", "JUROS_CONG")]
    contas = [("EMP01", "1.000.001", "1.000.099", "G1", 1, -1, "sim"),
              ("EMP02", "1.000.002", "1.000.099", "G1", 1, -1, "sim"),
              ("EMP03", "3.000.001", "3.000.099", "G3", 1, -1, "sim")]
    params = [(k, f"{pd.Timestamp(data_base):%Y-%m-%d}" if k == "data_base" else val)
              for k, val in PARAM_PADRAO.items()]
    return {
        "PARAMETROS": pd.DataFrame(params, columns=ABAS_CONFIG["PARAMETROS"]),
        "FONTES": pd.DataFrame(fontes, columns=ABAS_CONFIG["FONTES"]),
        "COLUNAS": pd.DataFrame(colunas, columns=ABAS_CONFIG["COLUNAS"]),
        "CONTAS": pd.DataFrame(contas, columns=ABAS_CONFIG["CONTAS"]),
        "INDEXADORES": pd.DataFrame([("PRE", "PRE"), ("CDI", "POS"), ("SELIC", "POS")],
                                    columns=ABAS_CONFIG["INDEXADORES"]),
        "FAIXAS_ATRASO": pd.DataFrame(FAIXAS_PADRAO, columns=ABAS_CONFIG["FAIXAS_ATRASO"]),
    }


def _gravar_exemplo(raiz, data_base, pasta_rel):
    pasta_dados = Path(raiz) / pasta_rel
    pasta_dados.mkdir(parents=True, exist_ok=True)
    dados = _dados_exemplo(data_base)
    dados["contabil"].to_excel(pasta_dados / "contabil.xlsx", index=False)
    dados["parcelas_a"].to_excel(pasta_dados / "parcelas_a.xlsx", index=False)
    dados["posicao_a"].to_excel(pasta_dados / "posicao_a.xlsx", index=False)
    dados["atual"].to_excel(pasta_dados / "conciliacao_atual.xlsx", index=False)
    dados["parcelas_b"].to_csv(pasta_dados / "parcelas_b.csv", sep=";", index=False, encoding="utf-8-sig")
    dados["posicao_b"].to_csv(pasta_dados / "posicao_b.csv", sep=";", index=False, encoding="utf-8-sig")
    config = Path(raiz) / "config_local" / "config.xlsx"
    config.parent.mkdir(parents=True, exist_ok=True)
    abas = _config_exemplo(data_base, pasta_rel)
    with pd.ExcelWriter(config, engine="openpyxl") as w:
        for nome, df in abas.items():
            df.to_excel(w, sheet_name=nome, index=False)
            _formatar(w.sheets[nome], df)
    return config


def criar_modelo(config):
    config = Path(config).resolve()
    raiz = config.parent.parent
    if config.exists():
        print(f"Já existe {config}. Não sobrescrevi. Apague ou renomeie se quiser um modelo novo.")
        return None
    criado = _gravar_exemplo(raiz, "2026-10-31", "dados/exemplo")
    print(f"Modelo criado: {criado}\nDados inventados em: {raiz / 'dados' / 'exemplo'}\n"
          "Teste: python conciliacao.py conciliar")
    return criado


# ---------------------------------------------------------------------------
# Autoteste (dados inventados, resultado conhecido)
# ---------------------------------------------------------------------------
def autoteste():
    v = Verificacao()
    v.info("== AUTOTESTE (dados inventados) ==")
    tmp = Path(tempfile.mkdtemp(prefix="conciliacao_teste_"))
    try:
        db = "2026-10-31"
        config = _gravar_exemplo(tmp, db, "dados")
        interno = Verificacao(eco=False)  # checagens internas da execução ficam fora do resumo do autoteste

        def status(res, chk, chave):
            linha = res[(res["checagem"] == chk) & (res["chave"] == chave)]
            return linha["status"].iloc[0] if len(linha) else "AUSENTE"

        def dif(res, chk, chave):
            return float(res[(res["checagem"] == chk) & (res["chave"] == chave)]["diferenca"].iloc[0])

        # Rodada 1: sem baseline
        saida, res, ops, _ = executar_conciliacao(config, v=interno)
        a1 = ops[(ops["sistema"] == "A") & (ops["operacao"] == "A1")].iloc[0]
        b1 = ops[(ops["sistema"] == "B") & (ops["operacao"] == "B1")].iloc[0]
        v.check("T01 filtro de data-base ignora outro dia", abs(a1["soma_vencimento"] - 220) < EPS)
        v.check("T02 Empréstimo da operação inclui multa e mora", abs(a1["emprestimo_op"] - 223) < EPS)
        v.check("T03 RAOC implícito = Empréstimo − saldo", abs(a1["raoc_implicito"] - 20) < EPS)
        v.check("T04 erro da coluna RAOC medido", abs(a1["erro_coluna_raoc"] - (-10)) < EPS)
        v.check("T05 dias de atraso calculados", a1["dias_atraso"] == 40)
        v.check("T06 faixa de atraso 1-60", a1["faixa_atraso"] == "1-60")
        v.check("T07 pós-fixada: Empréstimo = saldo e RAOC = 0",
                abs(b1["emprestimo_op"] - 800) < EPS and abs(b1["raoc_implicito"]) < EPS)
        v.check("T08 CSV com vírgula decimal lido", abs(b1["soma_vencimento"] - 1000) < EPS)
        b2 = ops[(ops["sistema"] == "B") & (ops["operacao"] == "B2")].iloc[0]
        v.check("T08b pós congelada: Empréstimo = saldo + juros e RAOC = juros",
                abs(b2["emprestimo_op"] - 530) < EPS and abs(b2["raoc_implicito"] - 30) < EPS
                and bool(b2["congelada"]))
        v.check("T08c contas da pós congelada fecham (C1, C2, C3)",
                all(status(res, c, k) == "OK" for c, k in (("C1", "3000001"), ("C2", "3000099"),
                                                          ("C3", "G3"))))
        v.check("T09 C1 conta sem erro = OK", status(res, "C1", "1000001") == "OK")
        v.check("T10 C1 conta com erro = NOVA", status(res, "C1", "1000002") == "NOVA"
                and abs(dif(res, "C1", "1000002") - 10) < EPS)
        v.check("T11 C2 RAOC compartilhado (N:1) = NOVA", status(res, "C2", "1000099") == "NOVA"
                and abs(dif(res, "C2", "1000099") - 10) < EPS)
        v.check("T12 C2b mede a coluna", abs(dif(res, "C2b", "1000099") - 20) < EPS)
        v.check("T13 C3 líquido fecha mesmo com C1 e C2 errados", status(res, "C3", "G1") == "OK")
        v.check("T14 conta fora da aba CONTAS é ignorada", not (res["chave"] == "9999999").any())
        v.check("T15 checagens internas sem falha inesperada",
                [l for l in interno.linhas if "FALHOU" in l]
                == ["CHECK sem diferenças NOVAS: FALHOU"])
        v.check("T16 Excel com as abas esperadas",
                set(pd.ExcelFile(saida).sheet_names) >= {"RESUMO", "OPERACOES", "ATRASO",
                                                         "INCONSISTENCIAS", "PARAMETROS",
                                                         "VALIDACAO_ATUAL"})

        # Rodada 2: com baseline -> CONHECIDA
        gravar_baseline(config, db, eco=False)
        _, res2, _, _ = executar_conciliacao(config, v=Verificacao(eco=False))
        v.check("T17 diferença na baseline vira CONHECIDA",
                status(res2, "C1", "1000002") == "CONHECIDA" and status(res2, "C2", "1000099") == "CONHECIDA")

        # Rodada 3: contábil muda -> MUDOU e C3 NOVA
        contabil = pd.read_excel(tmp / "dados" / "contabil.xlsx")
        contabil.loc[contabil["CONTA"] == "1.000.002", "SALDO"] = 515.0
        contabil.to_excel(tmp / "dados" / "contabil.xlsx", index=False)
        _, res3, _, _ = executar_conciliacao(config, v=Verificacao(eco=False))
        v.check("T18 diferença conhecida que mudou = MUDOU", status(res3, "C1", "1000002") == "MUDOU")
        v.check("T19 C3 nova diferença = NOVA", status(res3, "C3", "G1") == "NOVA")

        # Rodada 4: conta operacional sem mapa
        pa = pd.read_excel(tmp / "dados" / "parcelas_a.xlsx")
        extra = pa.iloc[[2]].copy()
        extra["CONTRATO"], extra["CONTA"] = "A9", "EMP99"
        pd.concat([pa, extra]).to_excel(tmp / "dados" / "parcelas_a.xlsx", index=False)
        v4 = Verificacao(eco=False)
        _, _, ops4, _ = executar_conciliacao(config, v=v4)
        v.check("T20 conta sem mapa derruba a checagem",
                "CHECK todas as contas operacionais estão na aba CONTAS: FALHOU" in v4.linhas)
        v.check("T21 operação sem mapa aparece com alerta",
                "SEM_MAPA" in ops4[ops4["operacao"] == "A9"]["alertas"].iloc[0])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return v


# ---------------------------------------------------------------------------
def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Conciliação Empréstimo x RAOC x Saldo")
    ap.add_argument("comando", choices=["autoteste", "modelo", "diagnostico", "conciliar", "baseline"])
    ap.add_argument("data_base", nargs="?", help="AAAA-MM-DD (conciliar: opcional; baseline: obrigatória)")
    ap.add_argument("--config", default=str(CONFIG_PADRAO))
    a = ap.parse_args(argv)
    resumo = PASTA_SCRIPT / "resumo_verificacao.txt"
    v = Verificacao()
    try:
        if a.comando == "autoteste":
            v = autoteste()
        elif a.comando == "modelo":
            criar_modelo(a.config)
            return 0
        elif a.comando == "diagnostico":
            v = diagnostico(a.config)
        elif a.comando == "conciliar":
            saida, _, _, v = executar_conciliacao(a.config, a.data_base, v)
            print(f"\nArquivo gerado: {saida}")
        elif a.comando == "baseline":
            if not a.data_base:
                raise ErroConfig("Informe a data: python conciliacao.py baseline AAAA-MM-DD")
            gravar_baseline(a.config, a.data_base)
            return 0
    except ErroConfig as e:
        v.check("configuração", False)
        v.info(f"ERRO: {e}")
        v.salvar(resumo)
        return 1
    v.salvar(resumo)
    print(f"\nResumo das checagens: {resumo}")
    return 0 if v.falhas == 0 or a.comando == "conciliar" else 1


if __name__ == "__main__":
    sys.exit(main())
