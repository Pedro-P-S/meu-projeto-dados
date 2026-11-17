# -*- coding: utf-8 -*-
"""
Conciliação Empréstimo x RAOC x Saldo — arquivo único.

Bate 3 fontes (saldo das contas, base operacional, lançamentos do dia) em 3 medidas
(Empréstimo, RAOC e saldo líquido = Empréstimo − RAOC) e entrega uma lista curta de
pendências: qual operação/conta abriu diferença, em qual medida, desde quando.

Uso (rodar na pasta onde está este arquivo):
  python conciliacao.py autoteste                 testa tudo com dados inventados
  python conciliacao.py modelo                    cria config_local/config.xlsx + dados de exemplo
  python conciliacao.py descobrir                 lê as fontes e sugere o mapeamento das colunas
  python conciliacao.py hipoteses [AAAA-MM-DD]    testa com os valores qual coluna/regra fecha melhor
  python conciliacao.py conciliar [AAAA-MM-DD] [--anterior AAAA-MM-DD]
  python conciliacao.py baseline AAAA-MM-DD       guarda as diferenças daquela data como "histórico"

Opcional em todos: --config <caminho do config.xlsx>
Checagens (só OK/FALHOU, nunca valores): resumo_verificacao.txt
Regras de negócio: _ai_context/01-doc-mestre-contexto.md
"""
import argparse
import copy
import re
import shutil
import sys
import tempfile
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

VERSAO = "0.2.3"
PASTA_SCRIPT = Path(__file__).resolve().parent
CONFIG_PADRAO = PASTA_SCRIPT / "config_local" / "config.xlsx"
EPS = 1e-9

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
                         "indexador", "congelada", "juros_congelados"]},
    "posicao": {"obrig": ["operacao", "conta_operacional", "saldo_devedor"],
                "opc": ["data_base", "indexador", "congelada", "juros_congelados", "multa", "mora"]},
    "lancamentos": {"obrig": ["conta", "valor"],
                    "opc": ["data_base", "natureza", "operacao", "historico"]},
    "conciliacao_atual": {"obrig": ["conta", "diferenca"], "opc": ["data_base"]},
}
APELIDOS_DIA_ANTERIOR = {"saldo_contabil", "parcelas", "posicao"}

TIPO_COLUNA = {
    "data_base": "data", "vencimento": "data",
    "saldo": "num", "valor_vencimento": "num", "multa": "num", "mora": "num",
    "raoc_informado": "num", "saldo_parcela": "num", "saldo_devedor": "num",
    "diferenca": "num", "juros_congelados": "num", "valor": "num",
}
COLUNAS_CONTA = ("conta", "conta_operacional")

PARAM_PADRAO = {
    "data_base": "",
    "data_base_anterior": "",               # vazio = dia útil anterior
    "tolerancia_conta": 0,
    "tolerancia_operacao": 0,
    "fonte_saldo_devedor": "posicao",       # posicao | parcelas
    "saldo_inclui_multa_mora": "sim",       # o saldo devedor já contém multa e mora?
    "indexador_padrao": "PRE",
    "valores_congelada": "S,SIM,1,TRUE,CONGELADA",  # valores da coluna 'congelada' que significam congelada
    "sinal_conciliacao_atual": 1,
    "nome_base": "Base",                    # como chamar cada fonte no relatório
    "nome_lancamentos": "Lançamentos",
    "nome_contabil": "Contábil",
    "pasta_saidas": "saidas",
    "pasta_historico": "historico",
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

# Tipos de pendência (código interno -> texto do relatório, com os nomes de PARAMETROS)
ONDE = {
    "BASE_X_LANC": "{base} ≠ {lanc}",
    "BASE_X_LANC_SEM_OP": "{base} ≠ {lanc} (lançamento sem operação)",
    "CONTABIL_X_LANC": "{contabil} ≠ {lanc}",
    "NAO_EXPLICADA": "{contabil} ≠ {base} (não explicada)",
    "HISTORICO": "Histórico",
}
COR_PRIORIDADE = {1: "F8CBAD", 2: "FFD966", 3: "DDEBF7", 4: "EDEDED"}


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
        ok = bool(ok)
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
        cab = [f"conciliacao.py v{VERSAO} — {datetime.now():%Y-%m-%d %H:%M}"]
        rod = [f"RESULTADO: {'TUDO OK' if self.falhas == 0 else 'HÁ CHECAGENS FALHOU'}"]
        Path(caminho).write_text("\n".join(cab + self.linhas + rod) + "\n", encoding="utf-8")


def _sinal(x):
    return "positiva" if x > 0 else ("negativa" if x < 0 else "zero")


# ---------------------------------------------------------------------------
# Conversões
# ---------------------------------------------------------------------------
_NULOS = {"", "nan", "NaN", "NaT", "None", "<NA>", "NULL", "null"}


def _s(v):
    """Célula -> texto limpo ('' para vazio)."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    t = str(v).strip()
    if t in _NULOS:
        return ""
    return t[:-2] if t.endswith(".0") and t[:-2].lstrip("-").isdigit() else t


def _texto(serie):
    if pd.api.types.is_float_dtype(serie):
        return serie.map(_s).astype(object)
    out = serie.astype(object).where(serie.notna(), "").astype(str).str.strip()
    out = out.str.replace(r"^(-?\d+)\.0$", r"\1", regex=True)
    return out.where(~out.isin(_NULOS), "").astype(object)


def _conta(serie):
    return _texto(serie).str.replace(r"[^0-9A-Za-z]", "", regex=True)


def _numero(serie):
    if pd.api.types.is_numeric_dtype(serie) and not pd.api.types.is_bool_dtype(serie):
        return pd.to_numeric(serie, errors="coerce").astype(float)
    t = _texto(serie)
    virgula = t.str.contains(",", regex=False)
    t = t.where(~virgula, t.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(t.replace("", np.nan), errors="coerce").astype(float)


def _data(serie):
    if pd.api.types.is_datetime64_any_dtype(serie):
        out = serie
    else:
        valores = serie.astype(object).where(_texto(serie) != "", np.nan)
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


def _dia_util_anterior(d):
    d = pd.Timestamp(d) - pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d -= pd.Timedelta(days=1)
    return d


_SENHAS = {}


def _preencher_senha(conexao):
    """Troca {senha} ou {senha:NOME} pela senha, sem nunca gravá-la em arquivo.
    Ordem: variável de ambiente CONCILIACAO_SENHA (ou CONCILIACAO_SENHA_NOME); senão pergunta
    uma vez por execução, sem mostrar o que é digitado."""
    import getpass
    import os

    def trocar(m):
        nome = (m.group(1) or "").upper()
        if nome not in _SENHAS:
            var = "CONCILIACAO_SENHA" + (f"_{nome}" if nome else "")
            _SENHAS[nome] = os.environ.get(var) or getpass.getpass(
                f"Senha do banco{' ' + nome if nome else ''} (não aparece ao digitar): ")
        return _SENHAS[nome]

    return re.sub(r"\{senha(?::([A-Za-z0-9_]+))?\}", trocar, conexao)


def _substituir(texto, db):
    return (texto.replace("{data_base}", db.strftime("%Y-%m-%d"))
                 .replace("{data_base_br}", db.strftime("%d/%m/%Y"))
                 .replace("{aaaammdd}", db.strftime("%Y%m%d"))
                 .replace("{ddmmaaaa}", db.strftime("%d%m%Y")))


def _partes_expr(expr):
    """'A + B - C' -> [(1,'A'), (1,'B'), (-1,'C')]. Operadores precisam de espaço dos dois lados."""
    tokens = re.split(r"\s+([+-])\s+", expr.strip())
    partes = [(1.0, tokens[0])]
    for op, col in zip(tokens[1::2], tokens[2::2]):
        partes.append((1.0 if op == "+" else -1.0, col))
    return partes


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


def ler_fonte(tipo, caminho, alvo, data_base, raiz, amostra=None, cache=None):
    tipo = tipo.lower()
    caminho, alvo = _substituir(caminho, data_base), _substituir(alvo, data_base)
    chave = (tipo, caminho, alvo, amostra)
    if cache is not None and chave in cache:
        return cache[chave]
    if tipo == "excel":
        df = pd.read_excel(_resolver(caminho, raiz), sheet_name=alvo if alvo else 0, nrows=amostra)
    elif tipo == "csv":
        arq = _resolver(caminho, raiz)
        df = None
        for enc in ("utf-8-sig", "latin-1"):
            try:
                sep = (chr(9) if alvo.lower() == "tab" else alvo) if alvo else _separador(arq, enc)
                df = pd.read_csv(arq, sep=sep, encoding=enc, dtype=str, nrows=amostra)
                break
            except UnicodeDecodeError:
                continue
    elif tipo == "odbc":
        import pyodbc  # só precisa existir se alguma fonte for odbc
        con = pyodbc.connect(_preencher_senha(caminho))
        try:
            cur = con.cursor()
            cur.execute(alvo)
            nomes = [d[0] for d in cur.description]
            linhas = cur.fetchmany(amostra) if amostra else cur.fetchall()
            df = pd.DataFrame.from_records([tuple(r) for r in linhas], columns=nomes)
        finally:
            con.close()
    else:
        raise ErroConfig(f"Tipo de fonte desconhecido: '{tipo}'. Use excel, csv ou odbc.")
    df.columns = [str(c).strip() for c in df.columns]
    if cache is not None:
        cache[chave] = df
    return df


def _separador(arq, encoding):
    """Separador do CSV pela 1ª linha: ; , tab ou | (o que aparecer mais)."""
    with open(arq, encoding=encoding) as f:
        primeira = f.readline()
    contagem = {sep: primeira.count(sep) for sep in (";", ",", chr(9), "|")}
    melhor = max(contagem, key=contagem.get)
    return melhor if contagem[melhor] > 0 else ";"


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
        if canon == "operacao":
            out = out.str.replace(r"^0+(?=\d)", "", regex=True)
        if canon in ("indexador", "congelada", "natureza"):
            out = out.str.upper()
        return out
    preenchido = _texto(serie) != ""
    out = _numero(serie) if tipo == "num" else _data(serie)
    v.check(f"{rotulo} valores válidos em {canon}", not (preenchido & out.isna()).any())
    if tipo == "num" and not obrigatoria:
        out = out.fillna(0.0)
    return out


def canonizar(bruto, apelido, sistema, mapa, data_base, v):
    esp = CANONICO[apelido]
    rotulo = f"{apelido}[{sistema or '-'}]"
    faltam = [c for c in esp["obrig"] if c not in mapa]
    nomes = {str(c).strip().upper(): c for c in bruto.columns}
    ausentes = [col for origem in mapa.values() for _, col in _partes_expr(origem)
                if col.strip().upper() not in nomes]
    v.check(f"{rotulo} colunas obrigatórias mapeadas", not faltam)
    v.check(f"{rotulo} colunas mapeadas existem na fonte", not ausentes)
    if faltam or ausentes:
        raise ErroConfig(f"{rotulo}: sem mapeamento para {faltam}; não achadas na fonte {ausentes}.")
    bruto = bruto.reset_index(drop=True)
    df = pd.DataFrame(index=bruto.index)
    for canon in esp["obrig"] + esp["opc"]:
        if canon not in mapa:
            df[canon] = _vazio(canon, len(bruto)).values
            continue
        partes = _partes_expr(mapa[canon])
        obrig = canon in esp["obrig"]
        if len(partes) > 1:
            if TIPO_COLUNA.get(canon) != "num":
                raise ErroConfig(f"{rotulo}: soma de colunas só vale para números ({canon}).")
            total = 0.0
            for sinal, col in partes:
                total = total + sinal * _converter(bruto[nomes[col.strip().upper()]], canon,
                                                   False, rotulo, v)
            df[canon] = np.asarray(total, dtype=float)
        else:
            df[canon] = _converter(bruto[nomes[partes[0][1].strip().upper()]], canon,
                                   obrig, rotulo, v).values
    df["sistema"] = sistema
    if "data_base" in mapa:
        df = df[df["data_base"] == data_base]
        if apelido != "lancamentos":  # dia sem lançamento é possível
            v.check(f"{rotulo} tem linhas na data-base", len(df) > 0)
    for canon in esp["obrig"]:
        if TIPO_COLUNA.get(canon, "texto") == "texto":
            vazio = (df[canon] == "").any()
        else:
            vazio = df[canon].isna().any()
        v.check(f"{rotulo} sem vazios em {canon}", not vazio)
    return df.reset_index(drop=True)


def carregar_fontes(cfg, P, data_base, raiz, v, cache=None, apelidos=None):
    partes = {}
    for apelido, sistema, tipo, caminho, alvo in cfg["FONTES"].itertuples(index=False):
        apelido, sistema = _s(apelido), _s(sistema)
        if apelido not in CANONICO:
            raise ErroConfig(f"FONTES: apelido '{apelido}' desconhecido. Use {list(CANONICO)}.")
        if apelidos is not None and apelido not in apelidos:
            continue
        bruto = ler_fonte(_s(tipo), _s(caminho), _s(alvo), data_base, raiz, cache=cache)
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


def tem_fonte(cfg, apelido):
    return any(_s(a) == apelido for a in cfg["FONTES"]["apelido"])


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
    valores_cong = {x.strip().upper() for x in _s(P["valores_congelada"]).split(",") if x.strip()}

    v.check("parcelas sem parcela repetida (sistema, operação, parcela)",
            not parc.duplicated(chave + ["num_parcela"]).any())
    v.check("posição sem operação repetida (sistema, operação)", not pos.duplicated(chave).any())

    parc["encargos"] = parc["multa"] + parc["mora"]
    pos["encargos"] = pos["multa"] + pos["mora"]
    parc["cong"] = parc["congelada"].isin(valores_cong)
    pos["cong"] = pos["congelada"].isin(valores_cong)
    g = parc.groupby(chave, as_index=False).agg(
        conta_parc=("conta_operacional", "first"),
        n_contas=("conta_operacional", "nunique"),
        qtd_parcelas=("num_parcela", "size"),
        soma_vencimento=("valor_vencimento", "sum"),
        encargos_parc=("encargos", "sum"),
        raoc_coluna=("raoc_informado", "sum"),
        soma_saldo_parcela=("saldo_parcela", "sum"),
        juros_cong_parc=("juros_congelados", "sum"),
        idx_parc=("indexador", "first"),
        cong_parc=("cong", "max"),
    )
    vencidas = parc[parc["vencimento"] < data_base]
    antigo = vencidas.groupby(chave, as_index=False).agg(vencimento_mais_antigo=("vencimento", "min"))
    g = g.merge(antigo, on=chave, how="left")
    pg = pos.groupby(chave, as_index=False).agg(
        conta_pos=("conta_operacional", "first"),
        saldo_devedor=("saldo_devedor", "sum"),
        encargos_pos=("encargos", "sum"),
        juros_cong_pos=("juros_congelados", "sum"),
        idx_pos=("indexador", "first"),
        cong_pos=("cong", "max"),
    )
    ops = g.merge(pg, on=chave, how="outer" if usa_posicao else "left", indicator=True)
    ops["origem"] = ops["_merge"].astype(str).map(
        {"both": "ambas", "left_only": "so_parcelas", "right_only": "so_posicao"})
    ops = ops.drop(columns="_merge")
    for col in ("conta_parc", "conta_pos", "idx_parc", "idx_pos"):
        ops[col] = _texto(ops[col])
    for col in ("qtd_parcelas", "soma_vencimento", "encargos_parc", "encargos_pos", "raoc_coluna",
                "soma_saldo_parcela", "saldo_devedor", "juros_cong_parc", "juros_cong_pos"):
        ops[col] = pd.to_numeric(ops[col], errors="coerce").fillna(0.0)
    ops["multa_mora"] = ops["encargos_parc"] + ops["encargos_pos"]
    ops["juros_congelados"] = ops["juros_cong_parc"] + ops["juros_cong_pos"]
    ops["congelada"] = (ops["cong_parc"].fillna(False).astype(bool)
                        | ops["cong_pos"].fillna(False).astype(bool))
    ops["conta_operacional"] = ops["conta_parc"].where(ops["conta_parc"] != "", ops["conta_pos"])
    conflito_conta = ((ops["conta_parc"] != "") & (ops["conta_pos"] != "")
                      & (ops["conta_parc"] != ops["conta_pos"])) | (ops["n_contas"].fillna(1) > 1)

    idx = ops["idx_parc"].where(ops["idx_parc"] != "", ops["idx_pos"])
    idx = idx.where(idx != "", _s(P["indexador_padrao"]).upper())
    ops["indexador"] = idx
    regra = idx.map(lambda x: indexadores.get(x, x if x in ("PRE", "POS") else "DESCONHECIDO"))
    idx_desconhecido = regra == "DESCONHECIDO"
    v.check("todos os indexadores estão na aba INDEXADORES", not idx_desconhecido.any())

    saldo = ops["saldo_devedor"] if usa_posicao else ops["soma_saldo_parcela"]
    ops["saldo_op"] = saldo + (0.0 if inclui_encargos else ops["multa_mora"])
    # PRE: Empréstimo = parcelas no vencimento + multa + mora; RAOC = Empréstimo − saldo.
    #      Congelada não muda a fórmula: o saldo da base para e o RAOC implícito cresce junto.
    # POS: juros e correção vão a D Empréstimo / C Rendas -> Empréstimo = saldo, RAOC = 0.
    #      Congelada: juros vão a D Empréstimo / C RAOC -> Empréstimo = saldo + juros congelados.
    pos_fixada = regra == "POS"
    juros_cong = np.where(pos_fixada & ops["congelada"], ops["juros_congelados"], 0.0)
    ops["emprestimo_op"] = np.where(pos_fixada, ops["saldo_op"] + juros_cong,
                                    ops["soma_vencimento"] + ops["multa_mora"])
    ops["raoc_implicito"] = np.where(pos_fixada, juros_cong, ops["emprestimo_op"] - ops["saldo_op"])
    ops["erro_coluna_raoc"] = ops["raoc_coluna"] - ops["raoc_implicito"]
    tem_cruzado = usa_posicao and bool((ops["soma_saldo_parcela"] != 0).any())
    ops["dif_saldo_cruzado"] = (np.where(ops["origem"] == "ambas",
                                         ops["soma_saldo_parcela"] - ops["saldo_devedor"], 0.0)
                                if tem_cruzado else 0.0)
    ops["regra"] = np.where(ops["congelada"], regra + " congelada", regra)

    ops["dias_atraso"] = (data_base - ops["vencimento_mais_antigo"]).dt.days.fillna(0).astype(int)
    ops["faixa_atraso"] = "fora das faixas"
    for faixa, de, ate in faixas[["faixa", "de_dias", "ate_dias"]].itertuples(index=False):
        dentro = ((ops["dias_atraso"] >= de) & (ops["dias_atraso"] <= ate)
                  & (ops["faixa_atraso"] == "fora das faixas"))
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
    dif_total = parc["valor_vencimento"].sum() - ops["soma_vencimento"].sum()
    v.check("Σ valor no vencimento preservado (fonte x operações)", abs(dif_total) < 0.005, dif_total)

    colunas = ["sistema", "operacao", "conta_operacional", "conta_emprestimo", "conta_raoc", "grupo",
               "indexador", "regra", "congelada", "origem", "qtd_parcelas", "dias_atraso",
               "faixa_atraso", "vencimento_mais_antigo", "soma_vencimento", "multa_mora",
               "emprestimo_op", "saldo_devedor", "soma_saldo_parcela", "saldo_op", "juros_congelados",
               "raoc_implicito", "raoc_coluna", "erro_coluna_raoc", "dif_saldo_cruzado", "alertas"]
    return ops[colunas].sort_values(chave).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Estoque: contábil x base, por conta / grupo
# ---------------------------------------------------------------------------
def conciliar_contas(ops, contabil, contas, v):
    saldo_raw = contabil.groupby("conta")["saldo"].sum()
    ok = ops[ops["conta_emprestimo"] != ""]
    emp = contas.drop_duplicates("conta_emprestimo")[["conta_emprestimo", "grupo", "sinal_emprestimo"]]
    raoc = contas.drop_duplicates("conta_raoc")[["conta_raoc", "grupo", "sinal_raoc"]]
    faltam = sorted((set(emp["conta_emprestimo"]) | set(raoc["conta_raoc"])) - set(saldo_raw.index))
    v.check("toda conta da aba CONTAS existe no saldo contábil", not faltam)

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
    por_grupo = res.pivot_table(index="grupo", columns="checagem", values="diferenca",
                                aggfunc="sum").reindex(columns=["C1", "C2", "C3"]).fillna(0.0)
    erro = (por_grupo["C3"] - (por_grupo["C1"] - por_grupo["C2"])).abs().max()
    v.check("identidade C3 = C1 − C2 em todos os grupos", pd.isna(erro) or erro < 0.005)
    for col in ("contabil", "base_operacional", "diferenca"):
        res[col] = res[col].round(2)
    res["descricao"] = res["checagem"].map(CHECAGENS)
    return res, faltam


def validar_conciliacao_atual(atual, res, contas, P, v):
    if atual.empty:
        v.info("CHECK C3 = conciliação atual: PULADO (fonte conciliacao_atual não configurada)")
        return pd.DataFrame()
    tol = _num_param(P, "tolerancia_conta")
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
    v.check("C3 = conciliação atual em todos os grupos", val["bate"].all())
    return val.rename_axis("grupo").reset_index()


# ---------------------------------------------------------------------------
# Movimento do dia: Δ contábil x lançamentos x Δ base (por conta e por operação)
# ---------------------------------------------------------------------------
# Convenção de "impacto": quanto o item muda a diferença (contábil − base) da conta.
# Assim a soma das pendências de uma conta = diferença contábil − base dela.
def conciliar_movimento(res_d, res_a, ops_d, ops_a, lanc, contas, P, v):
    tol_op = _num_param(P, "tolerancia_operacao")
    emp_set, raoc_set = set(contas["conta_emprestimo"]), set(contas["conta_raoc"])
    lc = lanc.copy()
    # 'sistema' = dono do número da operação. Lançamento sem sistema, com um só sistema na base: é dele.
    sistemas_base = set(ops_d["sistema"]) | set(ops_a["sistema"])
    if len(sistemas_base) == 1:
        lc.loc[lc["sistema"] == "", "sistema"] = next(iter(sistemas_base))
    v.check("lançamentos: sistema informado (há mais de um sistema na base)",
            len(sistemas_base) <= 1 or not (lc["sistema"] == "").any())
    nat = lc["natureza"].astype(str).str[:1]
    v.check("lançamentos: natureza é D ou C", nat.isin(["D", "C", ""]).all())
    lc["mov"] = lc["valor"] * np.where(nat == "C", -1.0, 1.0)          # devedor positivo
    lc["lado"] = np.where(lc["conta"].isin(emp_set), "EMP",
                          np.where(lc["conta"].isin(raoc_set), "RAOC", ""))
    lc = lc[lc["lado"] != ""].copy()
    lc.loc[lc["lado"] == "RAOC", "mov"] *= -1                           # RAOC tem saldo credor

    # --- por conta
    partes = []
    for chk, lado in (("C1", "EMP"), ("C2", "RAOC")):
        d = res_d[res_d["checagem"] == chk].set_index("chave")
        a = res_a[res_a["checagem"] == chk].set_index("chave")
        idx = d.index.union(a.index)
        m = pd.DataFrame(index=idx)
        m["lado"] = lado
        m["grupo"] = d["grupo"].reindex(idx).fillna(a["grupo"].reindex(idx))
        m["contabil_anterior"] = a["contabil"].reindex(idx).fillna(0.0)
        m["contabil_atual"] = d["contabil"].reindex(idx).fillna(0.0)
        m["base_anterior"] = a["base_operacional"].reindex(idx).fillna(0.0)
        m["base_atual"] = d["base_operacional"].reindex(idx).fillna(0.0)
        m["lancamentos"] = lc[lc["lado"] == lado].groupby("conta")["mov"].sum().reindex(idx).fillna(0.0)
        partes.append(m)
    mc = pd.concat(partes).rename_axis("conta").reset_index()
    mc["delta_contabil"] = mc["contabil_atual"] - mc["contabil_anterior"]
    mc["delta_base"] = mc["base_atual"] - mc["base_anterior"]
    mc["contabil_menos_lanc"] = (mc["delta_contabil"] - mc["lancamentos"]).round(2)
    mc["base_menos_lanc"] = (mc["delta_base"] - mc["lancamentos"]).round(2)

    # --- por operação e conta
    chave = ["sistema", "operacao", "lado", "conta"]

    def base_por_op(ops):
        e = ops[ops["conta_emprestimo"] != ""]
        b1 = e[["sistema", "operacao", "conta_emprestimo", "emprestimo_op"]].rename(
            columns={"conta_emprestimo": "conta", "emprestimo_op": "valor"}).assign(lado="EMP")
        b2 = e[["sistema", "operacao", "conta_raoc", "raoc_implicito"]].rename(
            columns={"conta_raoc": "conta", "raoc_implicito": "valor"}).assign(lado="RAOC")
        return pd.concat([b1, b2]).groupby(chave)["valor"].sum()

    bd, ba = base_por_op(ops_d), base_por_op(ops_a)
    lop = lc[lc["operacao"] != ""].groupby(chave)["mov"].sum()
    idx = bd.index.union(ba.index).union(lop.index)
    mo = pd.DataFrame(index=idx)
    mo["base_anterior"] = ba.reindex(idx).fillna(0.0)
    mo["base_atual"] = bd.reindex(idx).fillna(0.0)
    mo["lancamentos"] = lop.reindex(idx).fillna(0.0)
    mo["impacto"] = -((mo["base_atual"] - mo["base_anterior"]) - mo["lancamentos"])
    mo = mo.reset_index()
    divergente = mo["impacto"].abs() > tol_op + 0.005
    v.check("movimento por operação = lançamentos", not divergente.any())

    # --- itens do dia (vão para o histórico)
    itens = [mo[divergente].assign(onde="BASE_X_LANC")[chave + ["onde", "impacto"]]]
    soma_op = mo.groupby(["lado", "conta"])["impacto"].sum()
    imp_conta = -mc.set_index(["lado", "conta"])["base_menos_lanc"]
    sem_op = (imp_conta - soma_op.reindex(imp_conta.index).fillna(0.0)).round(2)
    sem_op = sem_op[sem_op.abs() > EPS].rename("impacto").reset_index()
    itens.append(sem_op.assign(onde="BASE_X_LANC_SEM_OP", sistema="", operacao="")[chave + ["onde", "impacto"]])
    m1 = mc[mc["contabil_menos_lanc"].abs() > EPS]
    itens.append(m1.assign(onde="CONTABIL_X_LANC", sistema="", operacao="",
                           impacto=m1["contabil_menos_lanc"])[chave + ["onde", "impacto"]])
    itens = pd.concat(itens, ignore_index=True)
    itens["impacto"] = itens["impacto"].round(2)
    itens = itens[itens["impacto"].abs() > EPS].reset_index(drop=True)
    v.check(f"Δ saldo das contas = lançamentos em todas as contas", (mc["contabil_menos_lanc"].abs() <= EPS).all())
    v.check(f"Δ base = lançamentos em todas as contas", (mc["base_menos_lanc"].abs() <= EPS).all())
    for col in ("contabil_anterior", "contabil_atual", "base_anterior", "base_atual", "lancamentos",
                "delta_contabil", "delta_base"):
        mc[col] = mc[col].round(2)
    for col in ("base_anterior", "base_atual", "lancamentos", "impacto"):
        mo[col] = mo[col].round(2)
    return mc, mo[mo["impacto"].abs() > EPS].reset_index(drop=True), itens


# ---------------------------------------------------------------------------
# Histórico (pasta_historico): baseline, itens diários, resíduos, execuções
# ---------------------------------------------------------------------------
COLS_ITENS = ["data", "onde", "sistema", "operacao", "lado", "conta", "impacto"]
COLS_RESIDUO = ["data", "lado", "conta", "residuo"]


def _ler_csv_hist(arq, colunas):
    if not Path(arq).exists():
        return pd.DataFrame(columns=colunas)
    df = pd.read_csv(arq, sep=";", dtype=str, encoding="utf-8-sig", keep_default_na=False)
    for c in colunas:
        if c not in df.columns:
            df[c] = ""
    return df[colunas]


def _gravar_csv_hist(arq, df, data_txt, colunas):
    """Substitui as linhas da data e regrava (rodar de novo o mesmo dia não duplica)."""
    antigo = _ler_csv_hist(arq, colunas)
    antigo = antigo[antigo["data"] != data_txt]
    novo = pd.concat([antigo, df[colunas].astype(str)], ignore_index=True).sort_values("data")
    Path(arq).parent.mkdir(parents=True, exist_ok=True)
    novo.to_csv(arq, sep=";", index=False, encoding="utf-8-sig")


def ler_baseline(pasta):
    arq = Path(pasta) / "baseline.xlsx"
    if not arq.exists():
        return pd.DataFrame(columns=["checagem", "chave", "diferenca"]), None
    b = pd.read_excel(arq, dtype={"checagem": str, "chave": str})
    b["chave"] = _texto(b["chave"])
    b["checagem"] = _texto(b["checagem"])
    b["diferenca"] = _numero(b["diferenca"])
    data = _data_param(b["data_base_foto"].iloc[0], "data_base_foto") if len(b) else None
    return b[["checagem", "chave", "diferenca"]], data


def _abertos(itens, tol):
    """Itens com saldo acumulado ≠ 0 e a data em que abriram."""
    linhas = []
    if itens.empty:
        return pd.DataFrame(columns=["onde", "sistema", "operacao", "lado", "conta", "impacto", "desde"])
    it = itens.sort_values("data")
    for chave, g in it.groupby(["onde", "sistema", "operacao", "lado", "conta"], sort=False):
        acum, desde = 0.0, None
        for d, imp in zip(g["data"], g["impacto"]):
            zerado = abs(acum) <= tol + 0.005
            acum = round(acum + imp, 2)
            if zerado and abs(acum) > tol + 0.005:
                desde = d
            elif abs(acum) <= tol + 0.005:
                desde = None
        if desde is not None:
            linhas.append((*chave, acum, desde))
    return pd.DataFrame(linhas, columns=["onde", "sistema", "operacao", "lado", "conta", "impacto", "desde"])


def montar_pendencias(db, res, contas, pasta_hist, P, varios_sistemas, v, itens_hoje=None):
    """Lista curta: 1 linha por operação (ou conta/grupo) que explica a diferença."""
    tol = _num_param(P, "tolerancia_conta")
    nomes = {"base": _s(P["nome_base"]), "lanc": _s(P["nome_lancamentos"]),
             "contabil": _s(P["nome_contabil"])}
    data_txt = f"{db:%Y-%m-%d}"
    baseline, data_bl = ler_baseline(pasta_hist)
    if data_bl is not None and data_bl >= db:
        baseline, data_bl = baseline.iloc[0:0], None  # baseline de data futura não vale para trás

    # itens de movimento (de dias > baseline, até hoje)
    hist = _ler_csv_hist(Path(pasta_hist) / "itens.csv", COLS_ITENS)
    hist = hist[hist["data"] != data_txt]
    if itens_hoje is not None and len(itens_hoje):
        hist = pd.concat([hist, itens_hoje.assign(data=data_txt)[COLS_ITENS]], ignore_index=True)
    hist["impacto"] = pd.to_numeric(hist["impacto"], errors="coerce").fillna(0.0)
    hist = hist[hist["data"] <= data_txt]
    if data_bl is not None:
        hist = hist[hist["data"] > f"{data_bl:%Y-%m-%d}"]
    abertos = _abertos(hist, tol)

    # resíduo por conta = diferença − histórico − Σ itens  (o que nada explica)
    dif = pd.concat([res[res["checagem"] == "C1"].assign(lado="EMP"),
                     res[res["checagem"] == "C2"].assign(lado="RAOC")]).set_index(["lado", "chave"])["diferenca"]
    bl = pd.concat([baseline[baseline["checagem"] == "C1"].assign(lado="EMP"),
                    baseline[baseline["checagem"] == "C2"].assign(lado="RAOC")])
    bl = bl.set_index(["lado", "chave"])["diferenca"] if len(bl) else pd.Series(dtype=float)
    soma_itens = hist.groupby(["lado", "conta"])["impacto"].sum() if len(hist) else pd.Series(dtype=float)
    residuo = (dif - bl.reindex(dif.index).fillna(0.0)
               - soma_itens.reindex(dif.index).fillna(0.0)).round(2)
    residuo = residuo[residuo.abs() > tol + EPS]
    res_hoje = residuo.rename("residuo").rename_axis(["lado", "conta"]).reset_index().assign(data=data_txt)

    # desde quando o resíduo existe (dias seguidos de execução com resíduo)
    hist_res = _ler_csv_hist(Path(pasta_hist) / "residuos.csv", COLS_RESIDUO)
    hist_res = pd.concat([hist_res[hist_res["data"] != data_txt], res_hoje.astype(str)], ignore_index=True)
    execs = sorted(set(_ler_csv_hist(Path(pasta_hist) / "execucoes.csv", ["data"])["data"]) | {data_txt})
    execs = [d for d in execs if d <= data_txt]
    com_res = set(zip(hist_res["data"], hist_res["lado"], hist_res["conta"]))
    desde_res = {}
    for lado, conta in residuo.index:
        desde = data_txt
        for d in reversed(execs):
            if (d, lado, conta) in com_res:
                desde = d
            else:
                break
        desde_res[(lado, conta)] = desde

    grupo_de = {**dict(zip(contas["conta_emprestimo"], contas["grupo"])),
                **dict(zip(contas["conta_raoc"], contas["grupo"]))}
    linhas = []

    def add(onde, operacao, conta, emp, raoc, desde, idade_txt=None):
        d = pd.Timestamp(desde)
        linhas.append({"onde_cod": onde, "Onde": ONDE[onde].format(**nomes), "Operação": operacao,
                       "Conta": conta, "Dif. saldo": round(emp - raoc, 2), "Dif. Empréstimo": round(emp, 2),
                       "Dif. RAOC": round(raoc, 2), "Desde": idade_txt or f"{d:%d/%m/%Y}",
                       "Idade (dias)": int((db - d).days), "grupo": grupo_de.get(conta.split(" / ")[0], conta)})

    # itens abertos: 1 linha por (onde, operação); se a operação tocou várias contas do mesmo lado, 1 por conta
    for (onde, sistema, operacao), g in abertos.groupby(["onde", "sistema", "operacao"], sort=False):
        op_txt = (f"{sistema}/{operacao}" if varios_sistemas and sistema else operacao) or "—"
        varias = (g.groupby("lado")["conta"].nunique() > 1).any()
        blocos = [gg for _, gg in g.groupby("conta")] if varias else [g]
        for b in blocos:
            emp = b.loc[b["lado"] == "EMP", "impacto"].sum()
            raoc = b.loc[b["lado"] == "RAOC", "impacto"].sum()
            contas_txt = " / ".join(dict.fromkeys(b.sort_values("lado")["conta"]))
            add(onde, op_txt, contas_txt, emp, raoc, b["desde"].min())

    # histórico e não explicada: 1 linha por grupo
    for onde, serie in (("HISTORICO", bl), ("NAO_EXPLICADA", residuo)):
        if serie is None or not len(serie):
            continue
        s = serie[serie.abs() > tol + EPS]
        for grupo in sorted({grupo_de.get(c, c) for _, c in s.index}):
            parte = s[[grupo_de.get(c, c) == grupo for _, c in s.index]]
            emp = parte[[l == "EMP" for l, _ in parte.index]].sum()
            raoc = parte[[l == "RAOC" for l, _ in parte.index]].sum()
            if onde == "HISTORICO":
                add(onde, "—", grupo, emp, raoc, data_bl, f"até {data_bl:%d/%m/%Y}")
            else:
                desde = min(desde_res[k] for k in parte.index)
                add(onde, "—", grupo, emp, raoc, desde)

    cols = ["Prioridade", "Onde", "Operação", "Conta", "Dif. saldo", "Dif. Empréstimo", "Dif. RAOC",
            "Desde", "Idade (dias)"]
    pend = pd.DataFrame(linhas)
    if pend.empty:
        pend = pd.DataFrame(columns=cols + ["onde_cod", "grupo"])
    else:
        historico = pend["onde_cod"] == "HISTORICO"
        mexe_saldo = pend["Dif. saldo"].abs() > tol + EPS
        pend["Prioridade"] = np.where(historico, np.where(mexe_saldo, 3, 4), np.where(mexe_saldo, 1, 2))
        pend["_abs"] = -pend["Dif. saldo"].abs() - (pend["Dif. Empréstimo"].abs() + pend["Dif. RAOC"].abs()) / 1e6
        pend = pend.sort_values(["Prioridade", "Idade (dias)", "_abs"]).drop(columns="_abs").reset_index(drop=True)

    novas = pend[(pend["onde_cod"] != "HISTORICO") & (pend["Idade (dias)"] == 0)]
    v.check("nenhuma pendência nova hoje", novas.empty)
    v.check("todas as diferenças explicadas (sem 'não explicada')", residuo.empty)
    return pend, res_hoje, data_bl


def resumo_grupos(res, pend):
    g = res.pivot_table(index="grupo", columns="checagem", values="diferenca", aggfunc="sum")
    g = g.reindex(columns=["C3", "C1", "C2"]).fillna(0.0).round(2)
    g.columns = ["Dif. saldo", "Dif. Empréstimo", "Dif. RAOC"]
    abertas = pend[pend["onde_cod"] != "HISTORICO"]
    g["Pendências abertas"] = abertas.groupby("grupo").size().reindex(g.index).fillna(0).astype(int)
    g["Abertas hoje"] = abertas[abertas["Idade (dias)"] == 0].groupby("grupo").size() \
        .reindex(g.index).fillna(0).astype(int)
    nao = pend[pend["onde_cod"] == "NAO_EXPLICADA"].groupby("grupo")["Dif. saldo"].sum()
    g["Não explicada (saldo)"] = nao.reindex(g.index).fillna(0.0).round(2)
    return g.rename_axis("Grupo").reset_index().sort_values(
        "Dif. saldo", key=lambda s: -s.abs()).reset_index(drop=True)


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
def _formatar(ws, df, prioridade=False):
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    ws.freeze_panes = "A2"
    if len(df):
        ws.auto_filter.ref = ws.dimensions
    for i, col in enumerate(df.columns, 1):
        ws.cell(1, i).font = Font(bold=True)
        ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(col)) + 3, 12), 60)
        if len(df) <= 50000 and pd.api.types.is_float_dtype(df[col]):
            for r in range(2, len(df) + 2):
                ws.cell(r, i).number_format = "#,##0.00"
        if len(df) <= 50000 and pd.api.types.is_datetime64_any_dtype(df[col]):
            for r in range(2, len(df) + 2):
                ws.cell(r, i).number_format = "DD/MM/YYYY"
    if prioridade and "Prioridade" in df.columns:
        j = list(df.columns).index("Prioridade") + 1
        for r in range(2, len(df) + 2):
            cor = COR_PRIORIDADE.get(ws.cell(r, j).value)
            if cor:
                for c in range(1, len(df.columns) + 1):
                    ws.cell(r, c).fill = PatternFill("solid", fgColor=cor)


def gravar_excel(arquivo, abas, pasta_csv):
    Path(arquivo).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(arquivo, engine="openpyxl") as w:
        for nome, df in abas.items():
            if len(df) > 1_000_000:
                csv = Path(pasta_csv) / f"{Path(arquivo).stem}_{nome}.csv"
                df.to_csv(csv, sep=";", decimal=",", index=False, encoding="utf-8-sig")
                df = pd.DataFrame({"aviso": [f"Linhas demais para o Excel; gravado em {csv.name}"]})
            df.to_excel(w, sheet_name=nome, index=False)
            _formatar(w.sheets[nome], df, prioridade=(nome == "PENDENCIAS"))


LEGENDA = [
    ("PENDENCIAS", "O que arrumar. Prioridade 1 = mexe no saldo líquido; 2 = só Empréstimo/RAOC; "
                   "3 e 4 = histórico (diferenças que já existiam na baseline)."),
    ("Dif.", "Quanto o item explica da diferença Contábil − Base. Somando as linhas de um grupo, "
             "dá a diferença do grupo na aba RESUMO."),
    ("Onde: Base ≠ Lançamentos", "A operação mexeu na base e o lançamento do dia não veio igual "
                                 "(faltou, sobrou ou foi para outra conta)."),
    ("Onde: Contábil ≠ Lançamentos", "A conta mexeu no contábil sem lançamento do dia (ex.: lançamento manual)."),
    ("Onde: ... sem operação", "Lançamento sem número de operação que não fecha com a base."),
    ("Onde: não explicada", "Diferença que nenhum item explica (dia não processado, fonte faltando)."),
    ("Idade", "Dias corridos desde que a pendência abriu."),
]


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def _preparar(config, v):
    config = Path(config).resolve()
    cfg, P = ler_config(config)
    return config.parent.parent, cfg, P, preparar_contas(cfg, v), preparar_indexadores(cfg, v), \
        preparar_faixas(cfg, v)


def _calcular_dia(cfg, P, contas, indexadores, faixas, db, raiz, v, cache, apelidos=None):
    dados = carregar_fontes(cfg, P, db, raiz, v, cache, apelidos)
    ops = calcular_operacoes(dados, contas, indexadores, faixas, P, db, v)
    res, faltam = conciliar_contas(ops, dados["saldo_contabil"], contas, v)
    return dados, ops, res, faltam


def executar_conciliacao(config, data_base=None, v=None, anterior=None, cache=None):
    v = v or Verificacao()
    raiz, cfg, P, contas, indexadores, faixas = _preparar(config, v)
    db = _data_param(data_base if data_base else P["data_base"], "data_base")
    pasta_hist = _resolver(P["pasta_historico"], raiz)
    cache = {} if cache is None else cache
    v.info(f"Data-base: {db:%Y-%m-%d}")
    dados, ops, res, faltam = _calcular_dia(cfg, P, contas, indexadores, faixas, db, raiz, v, cache)
    validacao = validar_conciliacao_atual(dados["conciliacao_atual"], res, contas, P, v)

    mc = mo = itens = None
    da = None
    if tem_fonte(cfg, "lancamentos"):
        da = _data_param(anterior or P["data_base_anterior"], "anterior") \
            if (anterior or _s(P["data_base_anterior"])) else _dia_util_anterior(db)
        v.info(f"Dia anterior: {da:%Y-%m-%d}")
        va = Verificacao(eco=False)
        _, ops_a, res_a, _ = _calcular_dia(cfg, P, contas, indexadores, faixas, da, raiz, va, cache,
                                           APELIDOS_DIA_ANTERIOR)
        falhas_a = [l for l in va.linhas if "FALHOU" in l]
        v.check("dia anterior lido sem falhas", not falhas_a)
        for l in falhas_a:
            v.info(f"    [dia anterior] {l}")
        execs = set(_ler_csv_hist(pasta_hist / "execucoes.csv", ["data"])["data"])
        _, data_bl = ler_baseline(pasta_hist)
        continuo = (not execs) or (f"{da:%Y-%m-%d}" in execs) or (data_bl is not None and data_bl >= da)
        v.check("histórico contínuo (dia anterior já foi conciliado)", continuo)
        mc, mo, itens = conciliar_movimento(res, res_a, ops, ops_a, dados["lancamentos"], contas, P, v)

    varios = len({_s(s) for s in cfg["FONTES"]["sistema"] if _s(s)}) > 1
    pend, res_hoje, data_bl = montar_pendencias(db, res, contas, pasta_hist, P, varios, v, itens)

    # grava histórico (substitui o dia se rodar de novo)
    data_txt = f"{db:%Y-%m-%d}"
    if itens is not None:
        _gravar_csv_hist(pasta_hist / "itens.csv", itens.assign(data=data_txt), data_txt, COLS_ITENS)
    _gravar_csv_hist(pasta_hist / "residuos.csv", res_hoje, data_txt, COLS_RESIDUO)
    _gravar_csv_hist(pasta_hist / "execucoes.csv",
                     pd.DataFrame({"data": [data_txt], "data_anterior": [f"{da:%Y-%m-%d}" if da is not None else ""],
                                   "executado_em": [f"{datetime.now():%Y-%m-%d %H:%M}"]}),
                     data_txt, ["data", "data_anterior", "executado_em"])

    inconsist = ops[ops["alertas"] != ""][["alertas", "sistema", "operacao", "conta_operacional"]]
    inconsist = pd.concat([inconsist.rename(columns={"alertas": "tipo"}),
                           pd.DataFrame({"tipo": "CONTA_SEM_SALDO_CONTABIL", "sistema": "", "operacao": "",
                                         "conta_operacional": faltam})], ignore_index=True)
    params = pd.DataFrame([("versao", VERSAO), ("executado_em", f"{datetime.now():%Y-%m-%d %H:%M}"),
                           ("data_base_usada", data_txt),
                           ("dia_anterior_usado", f"{da:%Y-%m-%d}" if da is not None else "sem lançamentos"),
                           ("baseline", f"{data_bl:%Y-%m-%d}" if data_bl is not None else "nenhuma")]
                          + [(k, _s(val)) for k, val in P.items() if k != "data_base"]
                          + [(k, len(d)) for k, d in (("linhas_" + a, dd) for a, dd in dados.items())]
                          + list(CHECAGENS.items()) + LEGENDA, columns=["nome", "valor"])
    params["valor"] = params["valor"].astype(str)

    abas = {"PENDENCIAS": pend.drop(columns=["onde_cod", "grupo"], errors="ignore")
            [["Prioridade", "Onde", "Operação", "Conta", "Dif. saldo", "Dif. Empréstimo", "Dif. RAOC",
              "Desde", "Idade (dias)"]],
            "RESUMO": resumo_grupos(res, pend),
            "DET_CONTAS": res}
    if mc is not None:
        abas["DET_MOVIMENTO_CONTAS"] = mc
        abas["DET_MOVIMENTO_OPERACOES"] = mo
    abas["DET_OPERACOES"] = ops
    abas["DET_ATRASO"] = resumo_atraso(ops)
    abas["DET_INCONSISTENCIAS"] = inconsist
    if not validacao.empty:
        abas["DET_VALIDACAO_ATUAL"] = validacao
    abas["LEGENDA_PARAMETROS"] = params
    pasta = _resolver(P["pasta_saidas"], raiz)
    saida = pasta / f"conciliacao_{data_txt}.xlsx"
    gravar_excel(saida, abas, pasta)
    v.check("Excel de saída gravado", saida.exists())
    return {"saida": saida, "res": res, "ops": ops, "pend": pend, "mov_contas": mc,
            "mov_ops": mo, "itens": itens, "v": v}


def gravar_baseline(config, data_base, eco=True):
    config = Path(config).resolve()
    raiz = config.parent.parent
    cfg, P = ler_config(config)
    db = _data_param(data_base, "data_base")
    saida = _resolver(P["pasta_saidas"], raiz) / f"conciliacao_{db:%Y-%m-%d}.xlsx"
    if not saida.exists():
        raise ErroConfig(f"Não achei {saida.name}. Rode antes: python conciliacao.py conciliar {db:%Y-%m-%d}")
    res = pd.read_excel(saida, sheet_name="DET_CONTAS", dtype={"checagem": str, "chave": str})
    res["chave"] = _texto(res["chave"])
    foto = res[res["checagem"].isin(["C1", "C2", "C3"])][["checagem", "chave", "diferenca"]].copy()
    foto = foto[foto["diferenca"].round(2).abs() > EPS]
    foto["data_base_foto"] = f"{db:%Y-%m-%d}"
    foto["motivo"] = ""
    pasta = _resolver(P["pasta_historico"], raiz)
    arq = pasta / "baseline.xlsx"
    pasta.mkdir(parents=True, exist_ok=True)
    if arq.exists():
        antigo = pd.read_excel(arq, dtype={"checagem": str, "chave": str, "motivo": str})
        antigo["chave"] = _texto(antigo["chave"])
        motivos = {(c, k): _s(m) for c, k, m in antigo[["checagem", "chave", "motivo"]].itertuples(index=False)}
        foto["motivo"] = [motivos.get((c, k), "") for c, k in foto[["checagem", "chave"]].itertuples(index=False)]
        shutil.copy2(arq, pasta / f"baseline_anterior_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
    if len(foto) == 0:  # sem diferenças: guarda uma linha zerada só para registrar a data
        foto = pd.DataFrame([{"checagem": "C3", "chave": "", "diferenca": 0.0,
                              "data_base_foto": f"{db:%Y-%m-%d}", "motivo": ""}])
    gravar_excel(arq, {"BASELINE": foto.reset_index(drop=True)}, pasta)
    if eco:
        print(f"Baseline gravada: {arq}\nDiferenças até {db:%d/%m/%Y} passam a aparecer como 'Histórico'.")
    return arq


# ---------------------------------------------------------------------------
# Descobrir colunas (nomes e tipos) e testar hipóteses (valores)
# ---------------------------------------------------------------------------
# canônica: (palavras fortes, palavras fracas, palavras que excluem)
PALAVRAS = {
    "data_base": (["DATA_BASE", "DT_BASE", "DT_REF", "DATA_REF", "DT_POSICAO", "DATA_POSICAO", "DT_MOV",
                   "DATA_MOV", "DT_MOVIMENTO", "DATA_MOVIMENTO", "DT_LANC", "DATA_LANC", "DATA"],
                  ["REF", "POSICAO", "MOVIMENTO", "BASE"],
                  ["VENC", "CONTRAT", "LIBER", "NASC", "ABERT", "PAGAM", "INCLUS", "CONGEL"]),
    "operacao": (["NR_OPERACAO", "NUM_OPERACAO", "COD_OPERACAO", "ID_OPERACAO", "OPERACAO", "CONTRATO",
                  "NR_CONTRATO"], ["OPER", "CONTR"],
                 ["SITUAC", "TIPO", "DATA", "DT_", "VALOR", "VL_", "QTD", "MODAL", "STATUS", "PRODUTO"]),
    "num_parcela": (["NR_PARCELA", "NUM_PARCELA", "NU_PARCELA", "PARCELA", "SEQ_PARCELA"], ["PARC", "PRESTAC"],
                    ["VALOR", "VL_", "SALDO", "DATA", "DT_", "QTD", "MULTA", "MORA", "RAOC", "RENDA"]),
    "conta_operacional": (["CONTA_CONTABIL", "COD_CONTA", "CONTA", "COSIF", "RUBRICA"], ["CONTA", "CTA"],
                          ["CORRENTE", "AGENCIA", "VALOR", "SALDO", "DATA"]),
    "vencimento": (["DT_VENCIMENTO", "DATA_VENCIMENTO", "DT_VENCTO", "VENCIMENTO"], ["VENC"],
                   ["VALOR", "VL_", "SALDO", "QTD", "DIAS"]),
    "valor_vencimento": (["VALOR_PARCELA", "VL_PARCELA", "VALOR_VENCIMENTO", "VL_VENCIMENTO", "VL_VENCTO",
                          "VALOR_FUTURO"], ["PARC", "VENC", "FUTURO", "PRESTAC", "NOMINAL"],
                         ["SALDO", "PRESENTE", "MULTA", "MORA", "RAOC", "RENDA", "JUROS", "PAGO", "DT_",
                          "DATA", "NR_", "NUM_", "QTD"]),
    "multa": (["VL_MULTA", "VALOR_MULTA", "MULTA"], ["MULTA"], ["DATA", "DT_", "PERC", "TAXA", "CONGEL"]),
    "mora": (["VL_MORA", "VALOR_MORA", "JUROS_MORA", "MORA"], ["MORA"],
             ["DATA", "DT_", "PERC", "TAXA", "CONGEL", "DIAS"]),
    "raoc_informado": (["RAOC", "RENDA_A_APROPRIAR", "RENDAS_A_APROPRIAR"], ["RAOC", "APROPRIAR"],
                       ["CONGEL", "DATA", "DT_"]),
    "saldo_parcela": (["SALDO_PARCELA", "VALOR_PRESENTE", "VL_PRESENTE", "SALDO_ATUAL"],
                      ["SALDO", "PRESENTE", "ATUAL"], ["DATA", "DT_", "ANTERIOR", "CONGEL"]),
    "saldo_devedor": (["SALDO_DEVEDOR", "SALDO_ATUAL", "SD_DEVEDOR", "SALDO"], ["SALDO", "DEVEDOR"],
                      ["DATA", "DT_", "ANTERIOR", "CONGEL", "CONTABIL"]),
    "saldo": (["SALDO_CONTABIL", "SALDO_ATUAL", "SALDO_FINAL", "SALDO"], ["SALDO"], ["DATA", "DT_", "ANTERIOR"]),
    "conta": (["CONTA_CONTABIL", "COD_CONTA", "CONTA", "COSIF", "RUBRICA"], ["CONTA", "CTA"],
              ["CORRENTE", "AGENCIA", "VALOR", "SALDO", "DATA"]),
    "indexador": (["INDEXADOR", "INDICE", "COD_INDEXADOR"], ["INDEX", "INDIC"],
                  ["VALOR", "VL_", "DATA", "DT_", "PERC", "TAXA"]),
    "congelada": (["CONGELADA", "IN_CONGELADA", "SITUACAO_OPERACAO", "SITUACAO"], ["CONGEL", "SITUAC", "STATUS"],
                  ["VALOR", "VL_", "DATA", "DT_", "RENDA", "JUROS"]),
    "juros_congelados": (["RENDA_CONGELADA", "JUROS_CONGELADOS"], ["CONGEL", "CONG"], ["DESCONG", "DATA", "DT_"]),
    "valor": (["VALOR_LANCAMENTO", "VL_LANCAMENTO", "VALOR"], ["VALOR", "VL_"], ["DATA", "DT_"]),
    "natureza": (["DEB_CRED", "NATUREZA", "D_C", "IND_DC", "TIPO_LANCAMENTO"], ["NATUR", "DEB", "CRED"],
                 ["VALOR", "VL_", "DATA"]),
    "historico": (["HISTORICO", "EVENTO", "COD_EVENTO", "DESCRICAO"], ["HIST", "EVENT", "DESCR"],
                  ["VALOR", "DATA"]),
    "diferenca": (["DIFERENCA", "DIF"], ["DIF"], ["DATA"]),
}


def _tipo_detectado(s):
    t = _texto(s)
    if (t != "").sum() == 0:
        return "vazio"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "data"
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return "num"
    nn = s[t != ""]
    if nn.map(lambda x: isinstance(x, (datetime, pd.Timestamp))).mean() >= 0.95:
        return "data"
    tt = t[t != ""]
    if tt.str.match(r"^(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})").mean() >= 0.95:
        return "data"
    if _numero(nn).notna().mean() >= 0.95:
        return "num"
    return "texto"


def _pontuar(canon, coluna, tipo):
    fortes, fracas, proibidas = PALAVRAS.get(canon, ([], [], []))
    nome = re.sub(r"[^0-9A-Z]+", "_", str(coluna).upper()).strip("_")
    pts = 0.0
    if nome in fortes:
        pts += 12
    elif any(f in nome for f in fortes):
        pts += 6 + max(len(f) for f in fortes if f in nome) / 10
    elif any(f in nome for f in fracas):
        pts += 3
    if any(p in nome for p in proibidas):
        pts -= 8
    esperado = TIPO_COLUNA.get(canon, "texto")
    if tipo == "vazio":
        pts -= 2
    elif esperado == "data" and tipo != "data":
        pts -= 100
    elif esperado == "num" and tipo != "num":
        pts -= 100
    elif esperado == "texto" and tipo == "data":
        pts -= 100
    return pts


def sugerir_mapa(amostra, apelido):
    tipos = {c: _tipo_detectado(amostra[c]) for c in amostra.columns}
    esp = CANONICO[apelido]
    cand = []
    for canon in esp["obrig"] + esp["opc"]:
        for col in amostra.columns:
            p = _pontuar(canon, col, tipos[col])
            if p > 0:
                cand.append((p, canon, col))
    cand.sort(key=lambda x: -x[0])
    escolhido, usados = {}, set()
    for p, canon, col in cand:
        if canon not in escolhido and col not in usados:
            escolhido[canon] = (col, p)
            usados.add(col)
    alternativas = {canon: [c for p, k, c in cand if k == canon and c != escolhido.get(canon, ("",))[0]][:2]
                    for canon in esp["obrig"] + esp["opc"]}
    return escolhido, alternativas, tipos


def descobrir(config):
    v = Verificacao()
    config = Path(config).resolve()
    raiz = config.parent.parent
    try:
        import openpyxl  # noqa: F401
        v.check("openpyxl instalado", True)
    except ImportError:
        v.check("openpyxl instalado", False)
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        v.check("pyodbc instalado", True)
        v.check("driver ODBC do Access disponível", any("Access" in d for d in drivers))
        v.check("driver ODBC Oracle disponível", any("Oracle" in d for d in drivers))
    except ImportError:
        drivers = []
        v.check("pyodbc instalado", False)
    abas = pd.read_excel(config, sheet_name=None, dtype=object)
    cfg, P = ler_config(config)
    db = _data_param(P["data_base"] or datetime.now().strftime("%Y-%m-%d"), "data_base")
    txt = [f"Python {sys.version.split()[0]} | pandas {pd.__version__} | drivers ODBC: {drivers}", ""]
    col_rows, sug_rows = [], []
    for apelido, sistema, tipo, caminho, alvo in cfg["FONTES"].itertuples(index=False):
        apelido, sistema = _s(apelido), _s(sistema)
        rotulo = f"{apelido}[{sistema or '-'}]"
        try:
            amostra = ler_fonte(_s(tipo), _s(caminho), _s(alvo), db, raiz, amostra=5000)
        except Exception as e:  # mostra o erro e segue para a próxima fonte
            v.check(f"{rotulo} fonte abre", False)
            txt.append(f"[{rotulo}] ERRO ao abrir: {type(e).__name__}: {e}\n")
            continue
        v.check(f"{rotulo} fonte abre", True)
        escolhido, alternativas, tipos = sugerir_mapa(amostra, apelido)
        atual = mapa_colunas(cfg, apelido, sistema)
        for col in amostra.columns:
            t = _texto(amostra[col])
            distintos = t[t != ""].unique()
            col_rows.append({"fonte": rotulo, "coluna": col, "tipo": tipos[col],
                             "preenchido_%": round(100 * (t != "").mean(), 1),
                             "valores_distintos_(se até 20)": ", ".join(sorted(map(str, distintos))[:20])
                             if tipos[col] == "texto" and len(distintos) <= 20 else ""})
        txt.append(f"[{rotulo}] sugestão (coluna canônica <- coluna da fonte):")
        esp = CANONICO[apelido]
        for canon in esp["obrig"] + esp["opc"]:
            col, pts = escolhido.get(canon, ("", 0))
            conf = "alta" if pts >= 10 else ("média" if pts >= 5 else ("baixa" if col else ""))
            marca = "*" if canon in esp["obrig"] else " "
            txt.append(f"  {marca}{canon:<18} <- {col or '(nenhuma)':<32} {conf:<6} "
                       f"alternativas: {', '.join(alternativas[canon]) or '-'}")
            sug_rows.append({"apelido": apelido, "sistema": sistema, "coluna_canonica": canon,
                             "coluna_origem": atual.get(canon) or col,
                             "sugerido": "" if atual.get(canon) else (f"descobrir: {conf}" if col else ""),
                             "alternativas": ", ".join(alternativas[canon])})
        faltam = [c for c in esp["obrig"] if not (atual.get(c) or escolhido.get(c))]
        v.check(f"{rotulo} todas as colunas obrigatórias têm sugestão", not faltam)
        txt.append("")
    # grava sugestões no config só onde está vazio
    if sug_rows:
        sug = pd.DataFrame(sug_rows)
        sug = sug[sug["coluna_origem"] != ""]
        backup = config.with_name(f"config_anterior_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        shutil.copy2(config, backup)
        abas["COLUNAS"] = sug[["apelido", "sistema", "coluna_canonica", "coluna_origem", "sugerido",
                               "alternativas"]].reset_index(drop=True)
        with pd.ExcelWriter(config, engine="openpyxl") as w:
            for nome, df in abas.items():
                df.to_excel(w, sheet_name=nome, index=False)
                _formatar(w.sheets[nome], df)
    gravar_excel(raiz / "descoberta.xlsx", {"COLUNAS_DAS_FONTES": pd.DataFrame(col_rows)}, raiz)
    (raiz / "descoberta.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    print("\n".join(txt))
    print(f"Sugestões gravadas na aba COLUNAS do config (só onde estava vazio). Confira a coluna 'sugerido'.\n"
          f"Lista de colunas e valores distintos (só para você, não mande para IA): {raiz / 'descoberta.xlsx'}")
    return v


def _cfg_com(cfg, apelido, sistema, canon, origem):
    novo = copy.deepcopy(cfg)
    c = novo["COLUNAS"]
    manter = ~((c["apelido"].map(_s) == apelido) & (c["sistema"].map(_s) == sistema)
               & (c["coluna_canonica"].map(_s) == canon))
    c = c[manter]
    if origem:
        c = pd.concat([c, pd.DataFrame([{"apelido": apelido, "sistema": sistema, "coluna_canonica": canon,
                                         "coluna_origem": origem}])], ignore_index=True)
    novo["COLUNAS"] = c.reset_index(drop=True)
    return novo


def hipoteses(config, data_base=None, eco=True):
    """Roda a conciliação com cada coluna candidata e diz qual fecha melhor (Σ |diferença| menor)."""
    v = Verificacao(eco=False)
    raiz, cfg, P, contas, indexadores, faixas = _preparar(config, v)
    db = _data_param(data_base if data_base else P["data_base"], "data_base")
    cache = {}

    def medir(cfg_x, P_x):
        vq = Verificacao(eco=False)
        try:
            _, _, res, _ = _calcular_dia(cfg_x, P_x, contas, indexadores, faixas, db, raiz, vq, cache,
                                         APELIDOS_DIA_ANTERIOR)
        except (ErroConfig, KeyError, ValueError) as e:
            return np.inf, 0, f"erro: {e}"
        m = res[res["checagem"].isin(["C1", "C2", "C3"])]
        return float(m["diferenca"].abs().sum()), int((m["diferenca"].abs() <= EPS).sum()), ""

    dims, valores_situacao = [], set()
    for apelido, sistema, tipo, caminho, alvo in cfg["FONTES"].itertuples(index=False):
        apelido, sistema = _s(apelido), _s(sistema)
        if apelido not in ("posicao", "parcelas"):
            continue
        bruto = ler_fonte(_s(tipo), _s(caminho), _s(alvo), db, raiz, cache=cache)
        amostra = bruto.head(5000)
        nums = [c for c in bruto.columns if _tipo_detectado(amostra[c]) == "num"]
        atual = mapa_colunas(cfg, apelido, sistema)
        col_cong = atual.get("congelada", "")
        nomes = {str(c).strip().upper(): c for c in bruto.columns}
        if col_cong.upper() in nomes:
            distintos = set(_texto(bruto[nomes[col_cong.upper()]]).str.upper()) - {""}
            if len(distintos) <= 20:
                valores_situacao |= distintos
        if apelido == "posicao":
            saldos = [c for c in nums if "SALDO" in c.upper()]
            if len(saldos) > 1:
                dims.append((apelido, sistema, "saldo_devedor", saldos, atual.get("saldo_devedor", "")))
        cong = [c for c in nums if "CONG" in c.upper()]
        if cong:
            congelando = [c for c in cong if "DESCONG" not in c.upper()]
            descong = [c for c in cong if "DESCONG" in c.upper()]
            cands = [""] + cong
            if len(congelando) > 1:
                cands.append(" + ".join(congelando))
            if congelando and descong:
                cands.append(" + ".join(congelando) + " - " + " - ".join(descong))
            dims.append((apelido, sistema, "juros_congelados", cands, atual.get("juros_congelados", "")))
    linhas = []
    for apelido, sistema, canon, cands, atual in dims:
        for cand in cands:
            total, n_ok, erro = medir(_cfg_com(cfg, apelido, sistema, canon, cand), P)
            linhas.append((f"{apelido}[{sistema or '-'}].{canon}", cand or "(nenhuma)",
                           cand == atual, total, n_ok, erro))
    atuais_cong = {x.strip().upper() for x in _s(P["valores_congelada"]).split(",") if x.strip()}
    for valor in sorted(valores_situacao):
        total, n_ok, erro = medir(cfg, dict(P, valores_congelada=valor))
        linhas.append(("parametro.valores_congelada", valor, valor in atuais_cong, total, n_ok, erro))
    for valor in ("sim", "nao"):
        P_x = dict(P, saldo_inclui_multa_mora=valor)
        total, n_ok, erro = medir(cfg, P_x)
        linhas.append(("parametro.saldo_inclui_multa_mora", valor,
                       valor == _s(P["saldo_inclui_multa_mora"]).lower(), total, n_ok, erro))
    tab = pd.DataFrame(linhas, columns=["hipotese", "candidato", "atual", "soma_abs_diferencas",
                                        "contas_zeradas", "erro"])
    tab["posicao_no_ranking"] = tab.groupby("hipotese")["soma_abs_diferencas"].rank(method="min").astype(int)
    tab = tab.sort_values(["hipotese", "posicao_no_ranking"]).reset_index(drop=True)
    melhores = {}
    txt = [f"Hipóteses testadas na data {db:%Y-%m-%d} (1 = fecha melhor). Sem valores.", ""]
    for hip, g in tab.groupby("hipotese", sort=False):
        melhores[hip] = list(g[g["posicao_no_ranking"] == 1]["candidato"])
        txt.append(hip)
        for cand, pos, at, erro in g[["candidato", "posicao_no_ranking", "atual", "erro"]].itertuples(index=False):
            txt.append(f"  {pos}. {cand}{'  (atual)' if at else ''}{'  ' + erro if erro else ''}")
        txt.append("")
    gravar_excel(raiz / "hipoteses.xlsx", {"HIPOTESES": tab}, raiz)
    (raiz / "hipoteses.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
    if eco:
        print("\n".join(txt))
        print(f"Ranking em {raiz / 'hipoteses.txt'} (só nomes). Valores só em hipoteses.xlsx, no seu PC.")
    return melhores, tab


# ---------------------------------------------------------------------------
# Modelo de config + dados de exemplo (inventados)
# ---------------------------------------------------------------------------
DATA_EXEMPLO = "2026-11-13"  # sexta-feira


def _dados_exemplo(data_base):
    db = pd.Timestamp(data_base)
    da = _dia_util_anterior(db)
    d2 = _dia_util_anterior(da)
    d3 = d2 - pd.Timedelta(days=1)
    v40, v21, v92 = db - pd.Timedelta(days=40), db + pd.Timedelta(days=21), db + pd.Timedelta(days=92)

    def br(d):
        return pd.Timestamp(d).strftime("%d/%m/%Y")

    pa = []
    for d, multa, mora, pres1, raoc_a2, pres_a2 in ((db, 2.0, 1.0, 103.0, 50.0, 450.0),
                                                     (da, 0.0, 0.0, 100.0, 55.0, 445.0),
                                                     (d2, 0.0, 0.0, 100.0, 55.0, 445.0)):
        pa += [(d, "A1", 1, "EMP01", v40, 110.0, multa, mora, 5.0, pres1, "PRE"),
               (d, "A1", 2, "EMP01", v21, 110.0, 0.0, 0.0, 5.0, 100.0, "PRE"),
               (d, "A2", 1, "EMP02", v92, 500.0, 0.0, 0.0, raoc_a2, pres_a2, "PRE")]
    pa.append((d3, "A1", 1, "EMP01", v40, 999.0, 0.0, 0.0, 0.0, 0.0, "PRE"))  # outro dia: ignorado
    parcelas_a = pd.DataFrame(pa, columns=["DT_REF", "CONTRATO", "NR_PARCELA", "CONTA", "DT_VENCTO", "VL_VENCTO",
                                           "VL_MULTA", "VL_MORA", "VL_RAOC", "VL_PRESENTE", "INDEXADOR"])
    v30 = br(db + pd.Timedelta(days=30))
    pb = []
    for d, b1 in ((db, "800,00"), (da, "795,00"), (d2, "795,00")):
        pb += [(br(d), "B1", "1", "EMP03", v30, "1.000,00", "", "", "0,00", b1, "CDI"),
               (br(d), "B2", "1", "EMP03", v30, "600,00", "", "", "0,00", "500,00", "SELIC")]
    parcelas_b = pd.DataFrame(pb, columns=["DATA_REFERENCIA", "NUM_OPERACAO", "PARC", "COD_CONTA", "VENCIMENTO",
                                           "VALOR_FUTURO", "MULTA", "MORA", "RAOC_PARCELA", "VALOR_ATUAL",
                                           "INDEXADOR"])
    posicao_a = pd.DataFrame([(d, op, conta, s, orig) for d, a1, a2 in ((db, 203.0, 450.0), (da, 200.0, 445.0),
                                                                         (d2, 200.0, 445.0))
                              for op, conta, s, orig in (("A1", "EMP01", a1, 300.0), ("A2", "EMP02", a2, 600.0))],
                             columns=["DT_REF", "CONTRATO", "CONTA", "SALDO_DEVEDOR", "SALDO_ORIGINAL"])
    posicao_b = pd.DataFrame([(br(d), "B1", "EMP03", b1, "N", "", desc) for d, b1, desc in
                              ((db, "800,00", "2,00"), (da, "795,00", ""), (d2, "795,00", ""))]
                             + [(br(d), "B2", "EMP03", "500,00", "S", j, desc) for d, j, desc in
                                ((db, "30,00", "2,00"), (da, "25,00", ""), (d2, "25,00", ""))],
                             columns=["DATA_REFERENCIA", "NUM_OPERACAO", "COD_CONTA", "SALDO", "CONGELADA",
                                      "JUROS_CONG", "RENDA_DESCONG"])
    contas_ = ["1.000.001", "1.000.002", "1.000.099", "3.000.001", "3.000.099", "9.999.999"]
    saldos = {db: [223.0, 510.0, -80.0, 1330.0, -30.0, 12345.0],
              da: [220.0, 510.0, -85.0, 1320.0, -25.0, 12000.0],
              d2: [220.0, 510.0, -85.0, 1320.0, -25.0, 12000.0]}
    contabil = pd.DataFrame([(d, c, s) for d, lista in saldos.items() for c, s in zip(contas_, lista)],
                            columns=["DATA", "CONTA", "SALDO"])
    atual = pd.DataFrame({"CONTA": ["1.000.001", "1.000.002", "3.000.001"], "DIFERENCA": [0.0, 0.0, 0.0]})
    cols_l = ["DATA_MOV", "CONTA_CONTABIL", "NR_OPERACAO", "DEB_CRED", "VALOR", "HISTORICO"]
    lanc_a = {db: pd.DataFrame([(br(db), "1.000.001", "A1", "D", "3,00", "MULTA E MORA"),
                                (br(db), "7.000.001", "A1", "C", "3,00", "RENDA MULTA E MORA"),
                                (br(db), "1.000.099", "A2", "D", "5,00", "APROPRIACAO"),
                                (br(db), "7.000.002", "A2", "C", "5,00", "APROPRIACAO")], columns=cols_l),
              da: pd.DataFrame(columns=cols_l)}
    lanc_b = {db: pd.DataFrame([(br(db), "3.000.001", "B1", "D", "5,00", "JUROS"),
                                (br(db), "7.000.003", "B1", "C", "5,00", "JUROS"),
                                (br(db), "3.000.001", "B2", "D", "5,00", "JUROS CONGELADOS"),
                                (br(db), "3.000.099", "B2", "C", "5,00", "JUROS CONGELADOS")], columns=cols_l),
              da: pd.DataFrame(columns=cols_l)}
    return {"parcelas_a": parcelas_a, "parcelas_b": parcelas_b, "posicao_a": posicao_a,
            "posicao_b": posicao_b, "contabil": contabil, "atual": atual, "lanc_a": lanc_a, "lanc_b": lanc_b}


def _mapa_exemplo():
    return {
        ("saldo_contabil", ""): {"data_base": "DATA", "conta": "CONTA", "saldo": "SALDO"},
        ("conciliacao_atual", ""): {"conta": "CONTA", "diferenca": "DIFERENCA"},
        ("parcelas", "A"): {"data_base": "DT_REF", "operacao": "CONTRATO", "num_parcela": "NR_PARCELA",
                            "conta_operacional": "CONTA", "vencimento": "DT_VENCTO",
                            "valor_vencimento": "VL_VENCTO", "multa": "VL_MULTA", "mora": "VL_MORA",
                            "raoc_informado": "VL_RAOC", "saldo_parcela": "VL_PRESENTE",
                            "indexador": "INDEXADOR"},
        ("parcelas", "B"): {"data_base": "DATA_REFERENCIA", "operacao": "NUM_OPERACAO", "num_parcela": "PARC",
                            "conta_operacional": "COD_CONTA", "vencimento": "VENCIMENTO",
                            "valor_vencimento": "VALOR_FUTURO", "multa": "MULTA", "mora": "MORA",
                            "raoc_informado": "RAOC_PARCELA", "saldo_parcela": "VALOR_ATUAL",
                            "indexador": "INDEXADOR"},
        ("posicao", "A"): {"data_base": "DT_REF", "operacao": "CONTRATO", "conta_operacional": "CONTA",
                           "saldo_devedor": "SALDO_DEVEDOR"},
        ("posicao", "B"): {"data_base": "DATA_REFERENCIA", "operacao": "NUM_OPERACAO",
                           "conta_operacional": "COD_CONTA", "saldo_devedor": "SALDO", "congelada": "CONGELADA",
                           "juros_congelados": "JUROS_CONG"},
        ("lancamentos", "A"): {"data_base": "DATA_MOV", "conta": "CONTA_CONTABIL", "operacao": "NR_OPERACAO",
                               "natureza": "DEB_CRED", "valor": "VALOR", "historico": "HISTORICO"},
        ("lancamentos", "B"): {"data_base": "DATA_MOV", "conta": "CONTA_CONTABIL", "operacao": "NR_OPERACAO",
                               "natureza": "DEB_CRED", "valor": "VALOR", "historico": "HISTORICO"},
    }


def _config_exemplo(data_base, pasta_rel):
    d = Path(pasta_rel)  # relativo à pasta do projeto
    fontes = [("saldo_contabil", "", "excel", str(d / "contabil.xlsx"), ""),
              ("parcelas", "A", "excel", str(d / "parcelas_a.xlsx"), ""),
              ("parcelas", "B", "csv", str(d / "parcelas_b.csv"), ""),
              ("posicao", "A", "excel", str(d / "posicao_a.xlsx"), ""),
              ("posicao", "B", "csv", str(d / "posicao_b.csv"), ""),
              ("lancamentos", "A", "csv", str(d / "lancamentos_a_{aaaammdd}.csv"), ""),
              ("lancamentos", "B", "csv", str(d / "lancamentos_b_{aaaammdd}.csv"), ""),
              ("conciliacao_atual", "", "excel", str(d / "conciliacao_atual.xlsx"), "")]
    colunas = [(a, s, k, val) for (a, s), m in _mapa_exemplo().items() for k, val in m.items()]
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
    pasta = Path(raiz) / pasta_rel
    pasta.mkdir(parents=True, exist_ok=True)
    dd = _dados_exemplo(data_base)
    dd["contabil"].to_excel(pasta / "contabil.xlsx", index=False)
    dd["parcelas_a"].to_excel(pasta / "parcelas_a.xlsx", index=False)
    dd["posicao_a"].to_excel(pasta / "posicao_a.xlsx", index=False)
    dd["atual"].to_excel(pasta / "conciliacao_atual.xlsx", index=False)
    dd["parcelas_b"].to_csv(pasta / "parcelas_b.csv", sep=";", index=False, encoding="utf-8-sig")
    dd["posicao_b"].to_csv(pasta / "posicao_b.csv", sep=";", index=False, encoding="utf-8-sig")
    for sis in ("a", "b"):
        for d, df in dd[f"lanc_{sis}"].items():
            df.to_csv(pasta / f"lancamentos_{sis}_{d:%Y%m%d}.csv", sep=";", index=False, encoding="utf-8-sig")
    config = Path(raiz) / "config_local" / "config.xlsx"
    config.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config, engine="openpyxl") as w:
        for nome, df in _config_exemplo(data_base, pasta_rel).items():
            df.to_excel(w, sheet_name=nome, index=False)
            _formatar(w.sheets[nome], df)
    return config


def criar_modelo(config):
    config = Path(config).resolve()
    raiz = config.parent.parent
    if config.exists():
        print(f"Já existe {config}. Não sobrescrevi. Apague ou renomeie se quiser um modelo novo.")
        return None
    criado = _gravar_exemplo(raiz, DATA_EXEMPLO, "dados/exemplo")
    da = _dia_util_anterior(pd.Timestamp(DATA_EXEMPLO))
    print(f"Modelo criado: {criado}\nDados inventados em: {raiz / 'dados' / 'exemplo'}\nTeste, nesta ordem:\n"
          f"  python conciliacao.py conciliar {da:%Y-%m-%d}\n"
          f"  python conciliacao.py baseline {da:%Y-%m-%d}\n"
          f"  python conciliacao.py conciliar {DATA_EXEMPLO}")
    return criado


# ---------------------------------------------------------------------------
# Autoteste (dados inventados, resultado conhecido)
# ---------------------------------------------------------------------------
def autoteste():
    v = Verificacao()
    v.info("== AUTOTESTE (dados inventados) ==")
    pastas = []

    def nova_pasta():
        p = Path(tempfile.mkdtemp(prefix="conciliacao_teste_"))
        pastas.append(p)
        return p, _gravar_exemplo(p, DATA_EXEMPLO, "dados")

    def rodar(config, data=DATA_EXEMPLO):
        return executar_conciliacao(config, data, v=Verificacao(eco=False))

    def linha(pend, onde, operacao=None, conta=None):
        p = pend[pend["onde_cod"] == onde]
        if operacao is not None:
            p = p[p["Operação"] == operacao]
        if conta is not None:
            p = p[p["Conta"] == conta]
        return p.iloc[0] if len(p) else None

    def dif(res, chk, chave):
        return float(res[(res["checagem"] == chk) & (res["chave"] == chave)]["diferenca"].iloc[0])

    try:
        db = pd.Timestamp(DATA_EXEMPLO)
        da = _dia_util_anterior(db)
        tmp, config = nova_pasta()

        # Dia anterior (sem baseline): diferenças antigas aparecem como "não explicada"
        r0 = rodar(config, f"{da:%Y-%m-%d}")
        ne = linha(r0["pend"], "NAO_EXPLICADA", conta="G1")
        v.check("T01 sem baseline, diferença antiga = não explicada (Emp 10, RAOC 10, saldo 0)",
                ne is not None and ne["Dif. Empréstimo"] == 10 and ne["Dif. RAOC"] == 10 and ne["Dif. saldo"] == 0
                and ne["Prioridade"] == 2)
        gravar_baseline(config, f"{da:%Y-%m-%d}", eco=False)

        # Dia: tudo consistente -> só histórico
        r1 = rodar(config)
        ops, res, pend = r1["ops"], r1["res"], r1["pend"]
        a1 = ops[(ops["sistema"] == "A") & (ops["operacao"] == "A1")].iloc[0]
        b1 = ops[(ops["sistema"] == "B") & (ops["operacao"] == "B1")].iloc[0]
        b2 = ops[(ops["sistema"] == "B") & (ops["operacao"] == "B2")].iloc[0]
        v.check("T02 filtro de data-base ignora outros dias", abs(a1["soma_vencimento"] - 220) < EPS)
        v.check("T03 Empréstimo da operação inclui multa e mora", abs(a1["emprestimo_op"] - 223) < EPS)
        v.check("T04 RAOC implícito = Empréstimo − saldo", abs(a1["raoc_implicito"] - 20) < EPS)
        v.check("T05 erro da coluna RAOC medido", abs(a1["erro_coluna_raoc"] + 10) < EPS)
        v.check("T06 dias e faixa de atraso", a1["dias_atraso"] == 40 and a1["faixa_atraso"] == "1-60")
        v.check("T07 pós: Empréstimo = saldo e RAOC = 0",
                abs(b1["emprestimo_op"] - 800) < EPS and abs(b1["raoc_implicito"]) < EPS)
        v.check("T08 pós congelada: Empréstimo = saldo + juros, RAOC = juros",
                abs(b2["emprestimo_op"] - 530) < EPS and abs(b2["raoc_implicito"] - 30) < EPS and b2["congelada"])
        v.check("T09 CSV com vírgula decimal e data dd/mm/aaaa", abs(b1["soma_vencimento"] - 1000) < EPS)
        v.check("T10 C1/C2 mostram erros que se anulam no C3",
                dif(res, "C1", "1000002") == 10 and dif(res, "C2", "1000099") == 10 and dif(res, "C3", "G1") == 0)
        v.check("T11 C2b mede a coluna de RAOC", dif(res, "C2b", "1000099") == 20)
        v.check("T12 conta fora da aba CONTAS ignorada", not (res["chave"] == "9999999").any())
        v.check("T13 movimento do dia fecha (base = lançamentos = contábil)",
                r1["itens"].empty and (r1["mov_contas"]["contabil_menos_lanc"] == 0).all())
        h = linha(pend, "HISTORICO", conta="G1")
        v.check("T14 diferença da baseline vira 'Histórico' prioridade 4",
                h is not None and h["Prioridade"] == 4 and len(pend) == 1)
        v.check("T15 checagens internas sem falha",
                [l for l in r1["v"].linhas if "FALHOU" in l] == [])
        v.check("T16 Excel com PENDENCIAS e RESUMO primeiro",
                pd.ExcelFile(r1["saida"]).sheet_names[:2] == ["PENDENCIAS", "RESUMO"])

        # Lançamento manual no contábil (fora dos lançamentos do dia)
        pasta_d = tmp / "dados"
        cont = pd.read_excel(pasta_d / "contabil.xlsx")
        cont.loc[(cont["CONTA"] == "1.000.002") & (cont["DATA"] == db), "SALDO"] = 515.0
        cont.to_excel(pasta_d / "contabil.xlsx", index=False)
        r2 = rodar(config)
        p = linha(r2["pend"], "CONTABIL_X_LANC", conta="1000002")
        v.check("T17 lançamento manual: Contábil ≠ Lançamentos, prioridade 1, idade 0, saldo 5",
                p is not None and p["Prioridade"] == 1 and p["Idade (dias)"] == 0 and p["Dif. saldo"] == 5
                and p["Operação"] == "—")
        v.check("T18 pendência nova derruba a checagem",
                "CHECK nenhuma pendência nova hoje: FALHOU" in r2["v"].linhas)

        # Operação mexeu na base sem lançamento (e contábil não mexeu)
        cont.loc[(cont["CONTA"] == "1.000.002") & (cont["DATA"] == db), "SALDO"] = 510.0
        cont.loc[(cont["CONTA"] == "1.000.099") & (cont["DATA"] == db), "SALDO"] = -85.0
        cont.to_excel(pasta_d / "contabil.xlsx", index=False)
        la = pd.read_csv(pasta_d / f"lancamentos_a_{db:%Y%m%d}.csv", sep=";", dtype=str)
        la[la["NR_OPERACAO"] != "A2"].to_csv(pasta_d / f"lancamentos_a_{db:%Y%m%d}.csv", sep=";", index=False)
        r3 = rodar(config)
        p = linha(r3["pend"], "BASE_X_LANC", operacao="A/A2")
        v.check("T19 rodar o mesmo dia de novo substitui (lançamento manual sumiu)",
                linha(r3["pend"], "CONTABIL_X_LANC") is None)
        v.check("T20 base sem lançamento: aponta a operação A2, só RAOC, saldo −5",
                p is not None and p["Dif. RAOC"] == 5 and p["Dif. saldo"] == -5 and p["Dif. Empréstimo"] == 0
                and p["Conta"] == "1000099" and p["Prioridade"] == 1)
        v.check("T21 soma das pendências do grupo = diferença do grupo",
                abs(r3["pend"][r3["pend"]["grupo"] == "G1"]["Dif. saldo"].sum() - dif(r3["res"], "C3", "G1")) < EPS
                and linha(r3["pend"], "NAO_EXPLICADA") is None)

        # Conta operacional sem mapa
        pa = pd.read_excel(pasta_d / "parcelas_a.xlsx")
        extra = pa[(pa["DT_REF"] == db) & (pa["CONTRATO"] == "A2")].copy()
        extra["CONTRATO"], extra["CONTA"] = "A9", "EMP99"
        pd.concat([pa, extra]).to_excel(pasta_d / "parcelas_a.xlsx", index=False)
        r4 = rodar(config)
        v.check("T22 conta sem mapa derruba a checagem e marca a operação",
                "CHECK todas as contas operacionais estão na aba CONTAS: FALHOU" in r4["v"].linhas
                and "SEM_MAPA" in r4["ops"][r4["ops"]["operacao"] == "A9"]["alertas"].iloc[0])

        # Idade: pendência aberta no dia anterior continua aberta hoje (sem baseline)
        tmp2, config2 = nova_pasta()
        pd.DataFrame([(f"{da:%d/%m/%Y}", "1.000.099", "A2", "D", "1,00", "LANCAMENTO A MAIS")],
                     columns=["DATA_MOV", "CONTA_CONTABIL", "NR_OPERACAO", "DEB_CRED", "VALOR", "HISTORICO"]) \
            .to_csv(tmp2 / "dados" / f"lancamentos_a_{da:%Y%m%d}.csv", sep=";", index=False)
        rodar(config2, f"{da:%Y-%m-%d}")
        r5 = rodar(config2)
        p_op = linha(r5["pend"], "BASE_X_LANC", operacao="A/A2")
        p_ct = linha(r5["pend"], "CONTABIL_X_LANC", conta="1000099")
        ne = linha(r5["pend"], "NAO_EXPLICADA", conta="G1")
        v.check("T23 pendência de ontem segue aberta com idade 1",
                p_op is not None and p_op["Idade (dias)"] == (db - da).days and p_op["Dif. RAOC"] == -1
                and p_ct is not None and p_ct["Dif. RAOC"] == 1)
        v.check("T24 não explicada conta a idade pelos dias seguidos",
                ne is not None and ne["Idade (dias)"] == (db - da).days)

        # Descobrir colunas pelo nome e tipo
        tmp3, config3 = nova_pasta()
        abas = pd.read_excel(config3, sheet_name=None, dtype=object)
        abas["COLUNAS"] = abas["COLUNAS"].iloc[0:0]
        with pd.ExcelWriter(config3, engine="openpyxl") as w:
            for nome, df in abas.items():
                df.to_excel(w, sheet_name=nome, index=False)
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            descobrir(config3)
        cfg3, _ = ler_config(config3)
        erradas = [(a, s, k) for (a, s), m in _mapa_exemplo().items() for k, col in m.items()
                   if mapa_colunas(cfg3, a, s).get(k) != col]
        v.check("T25 descobrir acerta todas as colunas do exemplo", not erradas)
        if erradas:
            v.info(f"    erradas: {erradas}")

        # Hipóteses pelos valores
        melhores, _ = hipoteses(config3, eco=False)
        v.check("T26 hipóteses: saldo certo da posição",
                melhores.get("posicao[A].saldo_devedor") == ["SALDO_DEVEDOR"])
        v.check("T27 hipóteses: coluna de juros congelados certa",
                melhores.get("posicao[B].juros_congelados") == ["JUROS_CONG"])
        v.check("T28 hipóteses: saldo inclui multa e mora",
                melhores.get("parametro.saldo_inclui_multa_mora") == ["sim"])
        v.check("T29 hipóteses: código de situação que significa congelada",
                melhores.get("parametro.valores_congelada") == ["S"])
        # Senha: variável de ambiente ou pergunta uma vez, nunca no config
        import os
        import getpass as _gp
        guardada = os.environ.pop("CONCILIACAO_SENHA", None)
        try:
            _SENHAS.clear()
            os.environ["CONCILIACAO_SENHA_TESTE"] = "x1"
            ok_env = _preencher_senha("UID=u;PWD={senha:teste}") == "UID=u;PWD=x1"
            del os.environ["CONCILIACAO_SENHA_TESTE"]
            _SENHAS.clear()
            chamadas, original = [], _gp.getpass
            _gp.getpass = lambda prompt="": chamadas.append(prompt) or "y2"
            try:
                a = _preencher_senha("PWD={senha}")
                b = _preencher_senha("PWD={senha};X={senha}")
            finally:
                _gp.getpass = original
        finally:
            _SENHAS.clear()
            if guardada is not None:
                os.environ["CONCILIACAO_SENHA"] = guardada
        v.check("T31 senha lida da variável de ambiente", ok_env)
        v.check("T32 senha perguntada uma vez só por execução",
                a == "PWD=y2" and b == "PWD=y2;X=y2" and len(chamadas) == 1)

        # Um sistema só, lançamentos sem 'sistema': casam com a base sozinhos
        tmp5, config5 = nova_pasta()
        abas = pd.read_excel(config5, sheet_name=None, dtype=object)
        f = abas["FONTES"]
        f = f[~((f["sistema"] == "B") & f["apelido"].isin(["parcelas", "posicao", "lancamentos"]))].copy()
        f.loc[f["apelido"] == "lancamentos", "sistema"] = np.nan
        abas["FONTES"] = f
        c = abas["COLUNAS"]
        c.loc[(c["apelido"] == "lancamentos") & (c["sistema"] == "A"), "sistema"] = np.nan
        abas["COLUNAS"] = c
        with pd.ExcelWriter(config5, engine="openpyxl") as w:
            for nome, df in abas.items():
                df.to_excel(w, sheet_name=nome, index=False)
        rodar(config5, f"{da:%Y-%m-%d}")
        r6 = rodar(config5)
        it = r6["itens"]
        v.check("T33 lançamentos sem 'sistema' casam com a base de um sistema só",
                not ((it["onde"] == "BASE_X_LANC") & it["operacao"].isin(["A1", "A2"])).any()
                and "CHECK lançamentos: sistema informado (há mais de um sistema na base): OK" in r6["v"].linhas)

        # CSV com outro separador é detectado sozinho
        tmp4 = nova_pasta()[0]
        for sep in (",", chr(9), "|"):
            arq = tmp4 / f"sep_{ord(sep)}.csv"
            arq.write_text(sep.join(["CONTA", "VALOR"]) + chr(10) + sep.join(["1.000.001", '"3,50"']) + chr(10),
                           encoding="utf-8")
            df = ler_fonte("csv", str(arq), "", db, tmp4)
            v.check(f"T30 CSV com separador {'tab' if sep == chr(9) else sep} detectado",
                    list(df.columns) == ["CONTA", "VALOR"] and df["VALOR"].iloc[0] == "3,50")
    finally:
        for p in pastas:
            shutil.rmtree(p, ignore_errors=True)
    return v


# ---------------------------------------------------------------------------
COMANDOS = ["autoteste", "modelo", "descobrir", "hipoteses", "conciliar", "baseline"]
MENU = [
    ("autoteste", "testa o programa com dados inventados", False),
    ("modelo", "cria config_local/config.xlsx e dados de exemplo", False),
    ("descobrir", "lê as fontes e sugere as colunas", False),
    ("hipoteses", "testa pelos valores qual coluna fecha melhor", True),
    ("conciliar", "concilia um dia e gera o Excel", True),
    ("baseline", "guarda as diferenças de um dia como 'Histórico'", True),
]


def _menu():
    print(f"\nConciliação v{VERSAO} — escolha o que rodar:")
    for i, (cmd, desc, _) in enumerate(MENU, 1):
        print(f"  {i}. {cmd:<11} {desc}")
    print("  0. sair")
    escolha = input("Número: ").strip()
    if not escolha.isdigit() or not 1 <= int(escolha) <= len(MENU):
        print("Saindo.")
        return None, None, None
    cmd, _, pede_data = MENU[int(escolha) - 1]
    data = anterior = None
    if pede_data:
        obrig = cmd == "baseline"
        data = input(f"Data AAAA-MM-DD ({'obrigatória' if obrig else 'Enter = data do config'}): ").strip() or None
        if cmd == "conciliar":
            anterior = input("Dia anterior AAAA-MM-DD (Enter = dia útil anterior): ").strip() or None
    return cmd, data, anterior


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # console do Spyder/IPython não tem reconfigure
        pass
    ap = argparse.ArgumentParser(description="Conciliação Empréstimo x RAOC x Saldo")
    ap.add_argument("comando", nargs="?", choices=COMANDOS)
    ap.add_argument("data_base", nargs="?", help="AAAA-MM-DD")
    ap.add_argument("--anterior", help="dia anterior (AAAA-MM-DD), para feriado")
    ap.add_argument("--config", default=str(CONFIG_PADRAO))
    a = ap.parse_args(argv)
    if a.comando is None:  # rodado sem argumento (ex.: botão Run do Spyder): mostra um menu
        a.comando, a.data_base, a.anterior = _menu()
        if a.comando is None:
            return 0
    resumo = PASTA_SCRIPT / "resumo_verificacao.txt"
    v = Verificacao()
    try:
        if a.comando == "autoteste":
            v = autoteste()
        elif a.comando == "modelo":
            criar_modelo(a.config)
            return 0
        elif a.comando == "descobrir":
            v = descobrir(a.config)
        elif a.comando == "hipoteses":
            hipoteses(a.config, a.data_base)
            return 0
        elif a.comando == "conciliar":
            r = executar_conciliacao(a.config, a.data_base, v, a.anterior)
            print(f"\nArquivo gerado: {r['saida']}")
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
