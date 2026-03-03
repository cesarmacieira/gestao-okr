import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
import os
import io
import base64

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Sistema OKR | JFCE",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",)

NUCLEOS = ["NEGI", "COMUNICAÇÃO", "DTIC", "NGP", "NIAP", "NIST", "NUAUD", "NUFIP", "NUJUD"]
STATUS_OPTIONS = ["Não Iniciado", "Em Andamento", "Concluído", "Cancelado", "Atrasado"]
DB_PATH = "okr_sistema.db"
XLSX_PATH = "okr_backup.xlsx"

def img_to_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

# ──────────────────────────────────────────────
# BANCO DE DADOS
# ──────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS okr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nucleo TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Estratégico',
            numero TEXT NOT NULL,
            descricao TEXT NOT NULL,
            gerente TEXT,
            data_inicio TEXT,
            data_fim TEXT,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS kr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            okr_id INTEGER NOT NULL REFERENCES okr(id) ON DELETE CASCADE,
            codigo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor_ini REAL DEFAULT 0,
            valor_alvo REAL DEFAULT 100,
            gerente_kr TEXT,
            data_entrega TEXT,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS iniciativa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kr_id INTEGER NOT NULL REFERENCES kr(id) ON DELETE CASCADE,
            numero TEXT NOT NULL,
            descricao TEXT NOT NULL,
            responsavel TEXT,
            status TEXT DEFAULT 'Não Iniciado',
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS checkin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kr_id INTEGER NOT NULL REFERENCES kr(id) ON DELETE CASCADE,
            data_ref TEXT NOT NULL,
            semana TEXT,
            valor_atual REAL,
            status TEXT,
            comentario TEXT,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()

def popular_dados_negi():
    conn = get_conn()
    existe = conn.execute("SELECT COUNT(*) FROM okr WHERE nucleo='NEGI'").fetchone()[0]
    if existe > 0:
        conn.close()
        return
    cur = conn.cursor()

    # ── OKR 1 ──────────────────────────────────────────────────────────
    cur.execute("""INSERT INTO okr(nucleo,tipo,numero,descricao,gerente,data_inicio,data_fim)
        VALUES('NEGI','Estratégico','OKR 1',
        'Atingir 80% dos índices de Governança do Questionário iESGO (TCU)',
        '','2025-01-01','2025-12-31')""")
    okr1 = cur.lastrowid

    # KR 1.1
    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 1.1','Identificar 100% dos pontos ainda não implementados',
        0,100,'','2025-12-31')""", (okr1,))
    # KR 1.1 sem iniciativas (apenas KR solo)

    # KR 1.2
    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 1.2','Implantar, no mínimo, 80% dos pontos de melhorias do IESGO específicos do NEGI',
        0,80,'','2025-12-31')""", (okr1,))
    kr12 = cur.lastrowid
    for n, d in [
        ("1.2.1", "Executar as iniciativas relativas à Governança"),
        ("1.2.2", "Criar um Programa de Integridade com novas 07 iniciativas previstas no IESGO"),
        ("1.2.3", "Atualizar a Política de gestão de riscos com 10 iniciativas previstas no IESGO"),
        ("1.2.4", "Implantar RELATÓRIO que contemple os itens do IESGO relativos à gestão estratégica"),
    ]:
        cur.execute("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",
                    (kr12, n, d, '', 'Não Iniciado'))

    # KR 1.3
    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 1.3',
        'Estabelecer um plano de ação para incentivar os 8 Núcleos da Administração a implantar, no mínimo, 70% dos pontos de melhorias do IESGO',
        0,8,'','2025-12-31')""", (okr1,))
    kr13 = cur.lastrowid
    for n, d in [
        ("1.3.1", "Plano - PA 0004127-57.2024.4.05.7600, inserido relatório de melhorias aos Núcleos e Seções"),
        ("1.3.2", "Elaborar planilha de acompanhamento das ações do iESGO aos Núcleos envolvidos"),
        ("1.3.3", "Encaminhar planilha de acompanhamento aos Núcleos envolvidos no iESGO a partir do PA 0004127-57.2024.4.05.7600"),
    ]:
        cur.execute("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",
                    (kr13, n, d, '', 'Não Iniciado'))

    conn.commit()
    conn.close()

init_db()
popular_dados_negi()

# ──────────────────────────────────────────────
# QUERIES
# ──────────────────────────────────────────────
def run_query(sql, params=()):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def run_exec(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid

def get_okrs(nucleo=None):
    if nucleo:
        return run_query("SELECT * FROM okr WHERE nucleo=? ORDER BY tipo, numero", (nucleo,))
    return run_query("SELECT * FROM okr ORDER BY nucleo, tipo, numero")

def get_krs(okr_id):
    return run_query("SELECT * FROM kr WHERE okr_id=? ORDER BY codigo", (okr_id,))

def get_iniciativas(kr_id):
    return run_query("SELECT * FROM iniciativa WHERE kr_id=? ORDER BY CAST(numero AS INTEGER)", (kr_id,))

def get_checkins(kr_id):
    return run_query("SELECT * FROM checkin WHERE kr_id=? ORDER BY data_ref DESC, id DESC", (kr_id,))

def calc_progresso_kr(ini, alvo, checkins_df):
    ini, alvo = float(ini or 0), float(alvo or 100)
    if checkins_df is None or checkins_df.empty:
        return 0.0
    # Ordena por data DESC e id DESC para garantir que o registro mais recente vença
    df_ord = checkins_df.sort_values(["data_ref","id"], ascending=[False, False])
    ult = df_ord.iloc[0]["valor_atual"]
    if ult is None:
        return 0.0
    if abs(alvo - ini) < 0.0001:
        return 100.0 if float(ult) >= alvo else 0.0
    return max(0.0, min(100.0, (float(ult) - ini) / (alvo - ini) * 100))

def calc_progresso_iniciativas(inis_df):
    """Calcula progresso das iniciativas: % de concluídas."""
    if inis_df is None or inis_df.empty:
        return 0.0
    total = len(inis_df)
    concluidas = len(inis_df[inis_df["status"] == "Concluído"])
    return (concluidas / total) * 100 if total > 0 else 0.0

def exportar_xlsx():
    okrs = run_query("SELECT * FROM okr ORDER BY nucleo, tipo, numero")
    krs = run_query("""
        SELECT kr.id, okr.nucleo, okr.numero as okr_numero, okr.tipo,
               okr.descricao as okr_descricao, kr.codigo, kr.descricao,
               kr.valor_ini, kr.valor_alvo, kr.gerente_kr, kr.data_entrega, kr.criado_em
        FROM kr JOIN okr ON kr.okr_id=okr.id ORDER BY okr.nucleo, kr.codigo
    """)
    inics = run_query("""
        SELECT i.id, okr.nucleo, okr.numero as okr_numero, kr.codigo as kr_codigo,
               i.numero, i.descricao, i.responsavel, i.status, i.criado_em
        FROM iniciativa i JOIN kr ON i.kr_id=kr.id JOIN okr ON kr.okr_id=okr.id
        ORDER BY okr.nucleo, kr.codigo, CAST(i.numero AS INTEGER)
    """)
    chk = run_query("""
        SELECT c.id, okr.nucleo, okr.numero as okr_numero, kr.codigo as kr_codigo,
               c.data_ref, c.semana, c.valor_atual, c.status, c.comentario, c.criado_em
        FROM checkin c JOIN kr ON c.kr_id=kr.id JOIN okr ON kr.okr_id=okr.id
        ORDER BY okr.nucleo, kr.codigo, c.data_ref DESC
    """)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        okrs.to_excel(w, sheet_name="OKRs", index=False)
        krs.to_excel(w, sheet_name="KRs", index=False)
        inics.to_excel(w, sheet_name="Iniciativas", index=False)
        chk.to_excel(w, sheet_name="CheckIns", index=False)
    with open(XLSX_PATH, "wb") as f:
        f.write(buf.getvalue())
    buf.seek(0)
    return buf.getvalue()

# ──────────────────────────────────────────────
# LOGOS
# ──────────────────────────────────────────────
logo_jcp  = img_to_base64("logo_horizontal_branca.png")
logo_trf5 = img_to_base64("logo_Justica_Federal_5Regiao_branca.png")
logo_jfce = img_to_base64("logo_Justica_Federal_Ceara_branca.png")
logo_pnud = img_to_base64("Logo_PNUD_branca.png")

# ──────────────────────────────────────────────
# CSS PRINCIPAL
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  /* Paleta principal: Azul institucional com alto contraste */
  --navy:      #0A1F5C;
  --navy-mid:  #1740A0;
  --blue:      #1857D4;
  --blue-mid:  #2D7DD2;
  --blue-lit:  #5BA3E8;
  --sky:       #CCDFF7;
  --sky-lit:   #EAF4FD;
  --sky-dim:   #B8D4F0;

  /* Neutros */
  --off-white: #F4F7FC;
  --white:     #FFFFFF;
  --slate:     #2C3E6B;
  --slate-mid: #4A6080;
  --slate-lit: #7A96B8;
  --border:    #B8CCE4;

  /* Semânticos com alto contraste */
  --green:     #096B38;
  --green-bg:  #D4EFE1;
  --amber:     #92400E;
  --amber-bg:  #FDE68A;
  --red:       #9B1010;
  --red-bg:    #FECACA;
  --gray-s:    #475569;
  --gray-bg:   #E8EEF6;

  /* Gold accent mais vibrante */
  --gold:      #C48C00;
  --gold-bg:   #FEF3C7;
  --gold-text: #7C5A00;
}

html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', sans-serif;
  color: var(--navy);
}

.main .block-container {
  padding: 1rem 2rem 2rem;
  max-width: 100%;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
  background: var(--navy) !important;
  border-right: none;
}
[data-testid="stSidebar"] > div {
  padding: 0 !important;
}
[data-testid="stSidebarContent"] {
  padding: 0 !important;
}

/* Nav item wrapper — ocupa toda largura, sem radio button visível */
[data-testid="stSidebar"] .stRadio > label {
  display: none !important;
}
[data-testid="stSidebar"] .stRadio > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding: 0;
}
[data-testid="stSidebar"] .stRadio > div > label {
  display: flex !important;
  align-items: center;
  gap: 10px;
  padding: 11px 20px !important;
  border-radius: 0 !important;
  margin: 0 !important;
  cursor: pointer;
  color: #B8CDE8 !important;
  font-size: 0.88rem !important;
  font-weight: 500 !important;
  transition: background 0.15s, color 0.15s;
  border-left: 3px solid transparent;
  background: transparent !important;
  width: 100%;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
  background: rgba(255,255,255,0.07) !important;
  color: #FFFFFF !important;
  border-left-color: var(--blue-lit);
}
[data-testid="stSidebar"] .stRadio > div > label[data-baseweb="radio"]:has(input:checked),
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
  background: rgba(255,255,255,0.12) !important;
  color: #FFFFFF !important;
  border-left-color: var(--gold) !important;
  font-weight: 600 !important;
}
/* Esconder o círculo do radio */
[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
  display: none !important;
}
[data-testid="stSidebar"] .stRadio > div > label > div:last-child {
  margin: 0 !important;
}

[data-testid="stSidebar"] * { color: #B8CDE8 !important; }
[data-testid="stSidebar"] .stRadio > div > label:has(input:checked) * {
  color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover * {
  color: #FFFFFF !important;
}
[data-testid="stSidebar"] hr {
  border-color: rgba(255,255,255,0.12) !important;
  margin: 12px 20px !important;
}
[data-testid="stSidebar"] .stDownloadButton > button {
  background: rgba(255,255,255,0.10) !important;
  color: #CCDFF7 !important;
  border: 1px solid rgba(255,255,255,0.20) !important;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.84rem;
  width: calc(100% - 40px) !important;
  margin: 0 20px !important;
  padding: 10px 16px !important;
}
[data-testid="stSidebar"] .stDownloadButton > button:hover {
  background: rgba(255,255,255,0.18) !important;
  color: #FFFFFF !important;
  border-color: rgba(255,255,255,0.38) !important;
  transform: none !important;
}

/* ── HEADER ── */
.header-bar {
  background: linear-gradient(135deg, #0A1F5C 0%, #1740A0 50%, #1857D4 100%);
  padding: 14px 28px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  border-bottom: 3px solid var(--gold);
  box-shadow: 0 4px 20px rgba(12,36,97,0.2);
}
.header-logos { display: flex; align-items: center; gap: 22px; }
.header-logos img { height: 44px; object-fit: contain; }
.header-title { text-align: center; color: white; flex: 1; }
.header-title h1 {
  font-size: 1.25rem; font-weight: 700; margin: 0;
  letter-spacing: 0.5px; text-transform: uppercase;
}
.header-title p {
  font-size: 0.74rem; margin: 3px 0 0;
  color: #F0C040; letter-spacing: 0.8px;
}

/* ── MÉTRICAS ── */
div[data-testid="metric-container"] {
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 18px !important;
  box-shadow: 0 1px 6px rgba(12,36,97,0.06);
  border-top: 3px solid var(--blue-mid);
}
div[data-testid="metric-container"] label {
  color: var(--slate-mid) !important;
  font-size: 0.73rem !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: var(--navy) !important;
  font-size: 1.7rem !important;
  font-weight: 700 !important;
}

/* ── TABS ── */
.stTabs { width: 100%; }
.stTabs [data-baseweb="tab-list"] {
  background: #EAF1FB;
  border-radius: 8px;
  padding: 4px;
  gap: 2px;
  width: 100%;
  display: flex;
  border: 2px solid #B8D0EE;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.82rem;
  color: #2C4880 !important;
  flex: 1;
  text-align: center;
  padding: 9px 6px;
  white-space: nowrap;
  border-right: 1px solid #C8D8EE;
  transition: background 0.15s;
}
.stTabs [data-baseweb="tab"]:last-child {
  border-right: none;
}
.stTabs [data-baseweb="tab"]:hover {
  background: #D0E4F7 !important;
  color: #0A1F5C !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, #0A1F5C 0%, #1740A0 50%, #1857D4 100%) !important;
  color: #FFFFFF !important;
  box-shadow: 0 2px 8px rgba(10,31,92,0.35);
  border-right-color: transparent !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 20px; }

/* ── BOTÕES ── */
.stButton > button, .stFormSubmitButton > button {
  background: linear-gradient(135deg, #0A1F5C 0%, #1740A0 50%, #1857D4 100%) !important;
  color: white !important;
  border: none;
  border-radius: 7px;
  font-weight: 600;
  font-family: 'IBM Plex Sans', sans-serif;
  transition: all 0.2s;
  padding: 8px 20px;
  letter-spacing: 0.3px;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  background: linear-gradient(135deg, #1740A0 0%, #1857D4 100%) !important;
  box-shadow: 0 4px 14px rgba(10,31,92,0.35);
  transform: translateY(-1px);
}

/* ── CARDS HIERÁRQUICOS ── */
.okr-card {
  background: var(--white);
  border-radius: 12px;
  padding: 16px 20px 14px;
  margin-bottom: 4px;
  border-left: 5px solid var(--blue);
  box-shadow: 0 2px 10px rgba(12,36,97,0.08);
}
.kr-card {
  background: var(--sky-lit);
  border-radius: 10px;
  padding: 13px 18px 11px;
  margin: 8px 0 8px 20px;
  border-left: 4px solid var(--blue-lit);
  border: 1px solid var(--sky-dim);
  border-left: 4px solid var(--blue-lit);
}
.inic-card {
  background: var(--white);
  border-radius: 7px;
  padding: 9px 16px;
  margin: 5px 0 5px 44px;
  border-left: 3px solid var(--gold);
  font-size: 0.86rem;
  color: var(--slate);
  border: 1px solid var(--border);
  border-left: 3px solid var(--gold);
}

/* ── TAGS / BADGES ── */
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 5px;
  font-size: 0.69rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-right: 5px;
}
.tag-nucleo  { background: var(--navy);    color: white; }
.tag-tipo    { background: var(--sky);     color: var(--blue); border: 1px solid var(--sky-dim); }
.tag-c       { background: var(--green-bg); color: var(--green); }
.tag-a       { background: var(--sky);      color: var(--blue); }
.tag-n       { background: var(--gray-bg);  color: var(--gray-s); }
.tag-at      { background: var(--red-bg);   color: var(--red); }
.tag-ca      { background: var(--gray-bg);  color: var(--gray-s); }

/* ── BARRA DE PROGRESSO — KR ── */
.prog-kr-wrap {
  background: var(--sky-dim);
  border-radius: 99px;
  height: 8px;
  width: 100%;
  margin: 6px 0 2px;
  overflow: hidden;
}
.prog-kr-fill {
  height: 8px;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--blue-mid), var(--blue-lit));
  transition: width 0.4s ease;
}

/* ── BARRA DE PROGRESSO — INICIATIVAS ── */
.prog-ini-wrap {
  background: #FDE68A;
  border-radius: 99px;
  height: 8px;
  width: 100%;
  margin: 6px 0 2px;
  overflow: hidden;
}
.prog-ini-fill {
  height: 8px;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--gold), #F59E0B);
  transition: width 0.4s ease;
}
.prog-ini-label {
  font-size: 0.73rem;
  color: var(--amber);
  font-weight: 600;
  display: block;
}
.prog-kr-label {
  font-size: 0.75rem;
  color: var(--slate-mid);
  font-weight: 500;
  display: block;
}

/* ── EXPANDER ── */
details summary {
  background: var(--sky-lit) !important;
  border-radius: 10px !important;
  padding: 12px 18px !important;
  font-weight: 600 !important;
  color: var(--navy) !important;
  border: 1px solid var(--border) !important;
  cursor: pointer;
  font-size: 0.95rem !important;
}
details[open] summary { border-radius: 10px 10px 0 0 !important; }

/* ── FORMULÁRIOS ── */
.stForm {
  background: #F0F6FF;
  border-radius: 12px;
  border: 2px solid #B8D0EE;
  padding: 4px !important;
}
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stDateInput"] label {
  font-weight: 700;
  color: #0A1F5C !important;
  font-size: 0.82rem;
  letter-spacing: 0.2px;
}
/* ════════════════════════════════════════════════════════
   INPUTS — borda uniforme #9BB8D8, fundo branco
   Estratégia: estilizar sempre o WRAPPER externo,
   nunca o input nativo (evita borda dupla).
   ════════════════════════════════════════════════════════ */

/* 1. SelectBox e DateInput compartilham [data-baseweb="select"/"input"] */
div[data-baseweb="select"] > div {
  background-color: #FFFFFF !important;
  border: 1.5px solid #9BB8D8 !important;
  border-radius: 6px !important;
}
div[data-baseweb="select"] > div:focus-within {
  border-color: #1857D4 !important;
  box-shadow: 0 0 0 3px rgba(24,87,212,0.12) !important;
}
div[data-baseweb="input"] {
  background-color: #FFFFFF !important;
  border: 1.5px solid #9BB8D8 !important;
  border-radius: 6px !important;
}
div[data-baseweb="input"]:focus-within {
  border-color: #1857D4 !important;
  box-shadow: 0 0 0 3px rgba(24,87,212,0.12) !important;
}
/* Filhos dos wrappers acima: sem borda própria */
div[data-baseweb="input"] input,
div[data-baseweb="select"] input {
  background-color: #FFFFFF !important;
  border: none !important;
  box-shadow: none !important;
  color: #0A1F5C !important;
}

/* 2. TextInput — o Streamlit usa [data-testid="stTextInput"] > div
      que contém um [data-baseweb="base-input"] internamente.
      Forçamos borda no wrapper stTextInput > div e zeramos
      qualquer borda que o baseweb possa adicionar dentro. */
div[data-testid="stTextInput"] > div {
  background-color: #FFFFFF !important;
  border: 1.5px solid #9BB8D8 !important;
  border-radius: 6px !important;
  padding: 0 !important;
}
div[data-testid="stTextInput"] > div:focus-within {
  border-color: #1857D4 !important;
  box-shadow: 0 0 0 3px rgba(24,87,212,0.12) !important;
}
/* Zerar todas as bordas internas do stTextInput */
div[data-testid="stTextInput"] > div > div,
div[data-testid="stTextInput"] input {
  background-color: #FFFFFF !important;
  border: none !important;
  box-shadow: none !important;
  color: #0A1F5C !important;
  border-radius: 0 !important;
}

/* 3. NumberInput — wrapper externo recebe a borda */
div[data-testid="stNumberInput"] > div {
  background-color: #FFFFFF !important;
  border: 1.5px solid #9BB8D8 !important;
  border-radius: 6px !important;
  overflow: hidden;
}
div[data-testid="stNumberInput"] > div:focus-within {
  border-color: #1857D4 !important;
  box-shadow: 0 0 0 3px rgba(24,87,212,0.12) !important;
}
div[data-testid="stNumberInput"] > div input {
  background-color: #FFFFFF !important;
  border: none !important;
  box-shadow: none !important;
  color: #0A1F5C !important;
}
/* Botões +/− do NumberInput: fundo branco */
div[data-testid="stNumberInput"] > div button {
  background-color: #FFFFFF !important;
  border-left: 1px solid #C8D8EE !important;
  color: #4A6080 !important;
}
div[data-testid="stNumberInput"] > div button:hover {
  background-color: #EAF1FB !important;
  color: #0A1F5C !important;
}

/* 4. TextArea */
div[data-testid="stTextArea"] textarea {
  background-color: #FFFFFF !important;
  border: 1.5px solid #9BB8D8 !important;
  border-radius: 6px !important;
  color: #0A1F5C !important;
}
div[data-testid="stTextArea"] textarea:focus {
  border-color: #1857D4 !important;
  box-shadow: 0 0 0 3px rgba(24,87,212,0.12) !important;
  outline: none !important;
}

/* 5. Dropdown list */
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #FFFFFF !important; }
[data-baseweb="menu"] li:hover { background: #EAF1FB !important; }

/* ── TÍTULO DE SEÇÃO ── */
.sec-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--navy);
  border-left: 4px solid var(--blue-mid);
  padding-left: 12px;
  margin-bottom: 16px;
  letter-spacing: 0.2px;
}

/* ── SIDEBAR NAV LABEL ── */
.sidebar-section {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: #607d99 !important;
  padding: 16px 20px 6px;
}

/* ── FOOTER ── */
.footer {
  text-align: center;
  color: var(--slate-lit);
  font-size: 0.72rem;
  margin-top: 48px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

/* ── DATAFRAME ── */
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid var(--border) !important; }

/* ── ALERTAS / MENSAGENS ── */
div[data-testid="stAlert"] {
  border-radius: 8px !important;
  border-left-width: 4px !important;
}

/* ── SECTION TITLE — borda gradiente simulada ── */
.sec-title {
  border-left: 4px solid #1740A0;
}

/* ── CAPTION / HELP TEXT ── */
div[data-testid="stCaptionContainer"] p {
  color: var(--slate-mid) !important;
  font-size: 0.80rem !important;
}

/* ── SUBHEADER ── */
h3 {
  color: var(--navy) !important;
  font-weight: 700 !important;
  font-size: 1.05rem !important;
  margin-bottom: 12px !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
def render_header():
    esq = "".join(
        f'<img src="data:image/png;base64,{b64}" alt="{alt}">'
        for b64, alt in [(logo_jfce, "JF-CE"), (logo_trf5, "TRF5")] if b64
    )
    dir_ = "".join(
        f'<img src="data:image/png;base64,{b64}" alt="{alt}">'
        for b64, alt in [(logo_jcp, "JCP"), (logo_pnud, "PNUD")] if b64
    )
    st.markdown(f"""
    <div class="header-bar">
      <div class="header-logos">{esq}</div>
      <div class="header-title">
        <h1>⚖️ Sistema de Gestão OKR</h1>
        <p>Seção Judiciária do Ceará · Projeto Justiça Centrada nas Pessoas</p>
      </div>
      <div class="header-logos">{dir_}</div>
    </div>
    """, unsafe_allow_html=True)

render_header()

# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section">Menu</div>', unsafe_allow_html=True)
    pagina = st.radio(
        "",
        ["🏠  Visão Hierárquica", "🎯  Cadastro", "📝  Check-in Semanal", "📊  Dashboard"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown('<div class="sidebar-section">Exportar</div>', unsafe_allow_html=True)
    try:
        st.download_button(
            "⬇️  Baixar Excel (Backup)",
            data=exportar_xlsx(),
            file_name=f"OKR_backup_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as e:
        st.caption(f"Export indisponível")

    st.markdown("<br>", unsafe_allow_html=True)
    for b64, alt, w in [(logo_jfce, "JF-CE", "72%"), (logo_pnud, "PNUD", "38%")]:
        if b64:
            st.markdown(
                f'<img src="data:image/png;base64,{b64}" alt="{alt}" '
                f'style="width:{w};margin:6px auto;display:block;opacity:0.55;">',
                unsafe_allow_html=True,
            )

# ──────────────────────────────────────────────
# HELPERS VISUAIS
# ──────────────────────────────────────────────
def gestores_tags(gestores_str):
    """Renderiza lista de gestores como tags visuais."""
    if not gestores_str or str(gestores_str).strip() in ("", "None", "nan"):
        return '<span style="color:#7A96B8;font-size:0.82rem;">—</span>'
    nomes = [g.strip() for g in str(gestores_str).split(",") if g.strip()]
    tags = "".join(
        f'<span style="background:#EAF4FD;color:#1740A0;border:1px solid #B8D4F0;'
        f'border-radius:5px;padding:2px 8px;font-size:0.75rem;font-weight:600;'
        f'margin-right:4px;display:inline-block;">'
        f'👤 {n}</span>'
        for n in nomes
    )
    return tags

def status_tag(status):
    mapa  = {"Concluído":"tag-c","Em Andamento":"tag-a","Não Iniciado":"tag-n","Atrasado":"tag-at","Cancelado":"tag-ca"}
    icons = {"Concluído":"✓","Em Andamento":"◎","Não Iniciado":"○","Atrasado":"⚑","Cancelado":"✕"}
    cls   = mapa.get(status, "tag-n")
    ic    = icons.get(status, "•")
    return f'<span class="tag {cls}">{ic} {status}</span>'

def barra_kr(pct):
    cor = "#1857D4" if pct >= 70 else "#C48C00" if pct >= 40 else "#9B1010"
    return f"""
    <div style="display:flex;align-items:center;gap:8px;margin:4px 0 2px;">
      <span style="font-size:0.72rem;color:#4A6080;font-weight:600;min-width:90px;">📊 Progresso KR</span>
      <div style="flex:1;background:#B8D4F0;border-radius:99px;height:10px;overflow:hidden;">
        <div style="width:{pct:.1f}%;height:10px;border-radius:99px;background:linear-gradient(90deg,{cor},{cor}99);transition:width 0.4s;"></div>
      </div>
      <span style="font-size:0.78rem;font-weight:700;color:{cor};min-width:46px;text-align:right;">{pct:.1f}%</span>
    </div>
    """

def barra_ini(pct, total, concluidas):
    return f"""
    <div style="display:flex;align-items:center;gap:8px;margin:4px 0 2px;">
      <span style="font-size:0.72rem;color:#92400E;font-weight:600;min-width:90px;">🗂️ Iniciativas</span>
      <div style="flex:1;background:#FDE68A;border-radius:99px;height:10px;overflow:hidden;">
        <div style="width:{pct:.1f}%;height:10px;border-radius:99px;background:linear-gradient(90deg,#C48C00,#F59E0B);transition:width 0.4s;"></div>
      </div>
      <span style="font-size:0.78rem;font-weight:700;color:#92400E;min-width:46px;text-align:right;">{int(concluidas)}/{int(total)}</span>
    </div>
    """


# ══════════════════════════════════════════════
# PÁGINA 1 — VISÃO HIERÁRQUICA
# ══════════════════════════════════════════════
if "Visão" in pagina:
    st.markdown('<div class="sec-title">🏠 Visão Hierárquica</div>', unsafe_allow_html=True)
    st.caption("OKR → KR → Iniciativas com progresso em tempo real")

    cf1, cf2, cf3 = st.columns([1, 1, 2])
    f_nucleo = cf1.selectbox("Núcleo", NUCLEOS, key="vh_n")
    f_tipo   = cf2.selectbox("Tipo OKR", ["Todos", "Estratégico", "Tático/Departamental"], key="vh_t")

    okrs_all = get_okrs(f_nucleo)
    if f_tipo != "Todos":
        okrs_all = okrs_all[okrs_all.tipo == f_tipo]

    if not okrs_all.empty:
        okr_opts = ["Todos os OKRs"] + [f"{r.numero} — {r.descricao[:60]}" for r in okrs_all.itertuples()]
        f_okr = cf3.selectbox("OKR", okr_opts, key="vh_okr")
        if f_okr != "Todos os OKRs":
            sel_num = f_okr.split(" — ")[0].strip()
            okrs_all = okrs_all[okrs_all.numero == sel_num]
    else:
        cf3.selectbox("OKR", ["—"], key="vh_okr", disabled=True)

    if okrs_all.empty:
        st.info("Nenhum OKR encontrado. Use Cadastro para adicionar.")
    else:
        all_chk  = run_query("SELECT * FROM checkin")
        all_krs  = run_query("SELECT * FROM kr")
        all_inis = run_query("SELECT * FROM iniciativa")

        for okr in okrs_all.itertuples():
            krs_okr = all_krs[all_krs.okr_id == okr.id]
            progs_kr = []
            for kr in krs_okr.itertuples():
                chkr = all_chk[all_chk.kr_id == kr.id] if not all_chk.empty else pd.DataFrame()
                progs_kr.append(calc_progresso_kr(kr.valor_ini, kr.valor_alvo, chkr))
            prog_okr = sum(progs_kr) / len(progs_kr) if progs_kr else 0.0

            # Progresso global de iniciativas do OKR
            all_inis_okr = all_inis[all_inis.kr_id.isin(krs_okr.id.tolist())] if not all_inis.empty else pd.DataFrame()
            prog_ini_okr = calc_progresso_iniciativas(all_inis_okr)

            with st.expander(
                f"🎯  {okr.numero}  —  {okr.descricao}",
                expanded=False
            ):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.markdown(
                    f'<span class="tag tag-nucleo">{okr.nucleo}</span>'
                    f'<span class="tag tag-tipo">{okr.tipo}</span>',
                    unsafe_allow_html=True,)
                c2.markdown(gestores_tags(okr.gerente), unsafe_allow_html=True)
                c3.markdown(f"📅 {okr.data_inicio or '—'} → {okr.data_fim or '—'}")

                # Barras do OKR
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(barra_kr(prog_okr), unsafe_allow_html=True)
                with col_b:
                    n_total = len(all_inis_okr)
                    n_conc  = len(all_inis_okr[all_inis_okr.status == "Concluído"]) if n_total > 0 else 0
                    st.markdown(barra_ini(prog_ini_okr, n_total, n_conc), unsafe_allow_html=True)

                st.markdown("<hr style='margin:10px 0;border-color:#C8D8EA;'>", unsafe_allow_html=True)

                # KRs
                for kr in krs_okr.itertuples():
                    chkr     = all_chk[all_chk.kr_id == kr.id] if not all_chk.empty else pd.DataFrame()
                    prog_kr  = calc_progresso_kr(kr.valor_ini, kr.valor_alvo, chkr)
                    inis_kr  = all_inis[all_inis.kr_id == kr.id] if not all_inis.empty else pd.DataFrame()
                    prog_ini = calc_progresso_iniciativas(inis_kr)
                    n_ini    = len(inis_kr)
                    n_conc_i = len(inis_kr[inis_kr.status == "Concluído"]) if n_ini > 0 else 0

                    ult_status = None
                    if not chkr.empty:
                        ult_status = chkr.sort_values("data_ref", ascending=False).iloc[0]["status"]

                    st.markdown(f"""
                    <div class="kr-card">
                      <b>📌 {kr.codigo}</b> — {kr.descricao}<br>
                      <small style="color:#4A6080;">
                        {gestores_tags(kr.gerente_kr)} &nbsp;·&nbsp;
                        🎯 Meta: <b>{kr.valor_ini} → {kr.valor_alvo}</b> &nbsp;·&nbsp;
                        📅 {kr.data_entrega or '—'} &nbsp;·&nbsp;
                        {status_tag(ult_status) if ult_status else '<span class="tag tag-n">○ Sem check-in</span>'}
                      </small>
                    </div>
                    """, unsafe_allow_html=True)

                    # Barras do KR
                    col_kr_a, col_kr_b = st.columns(2)
                    with col_kr_a:
                        st.markdown(barra_kr(prog_kr), unsafe_allow_html=True)
                    with col_kr_b:
                        if n_ini > 0:
                            st.markdown(barra_ini(prog_ini, n_ini, n_conc_i), unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="prog-ini-label">Sem iniciativas cadastradas</span>', unsafe_allow_html=True)

                    # Iniciativas
                    for ini in inis_kr.itertuples() if not inis_kr.empty else []:
                        st.markdown(f"""
                        <div class="inic-card">
                          ▶ <b>Iniciativa {ini.numero}:</b> {ini.descricao}
                          &nbsp;·&nbsp; {gestores_tags(ini.responsavel)}
                          &nbsp;·&nbsp; {status_tag(ini.status)}
                        </div>
                        """, unsafe_allow_html=True)

                    st.write("")

    st.markdown('<div class="footer">Sistema OKR · Justiça Federal · Seção Judiciária do Ceará · Projeto Justiça Centrada nas Pessoas · PNUD</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
# PÁGINA 2 — CADASTRO
# ══════════════════════════════════════════════
elif "Cadastro" in pagina:
    st.markdown('<div class="sec-title">🎯 Cadastro de OKR, KR e Iniciativas</div>', unsafe_allow_html=True)

    t1,t2,t3,t4,t5,t6 = st.tabs(["➕ Novo OKR", "➕ Novo KR", "➕ Nova Iniciativa",
        "✏️ Editar OKR", "✏️ Editar KR", "✏️ Editar Iniciativa",])

    with t1:
        st.subheader("Cadastrar Objetivo (OKR)")
        with st.form("f_okr", clear_on_submit=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns([1.4, 1.4, 0.9, 1.6])
            nuc = r1c1.selectbox("Núcleo *", NUCLEOS)
            tip = r1c2.selectbox("Tipo *", ["Estratégico","Tático/Departamental"])
            num = r1c3.text_input("Número *", placeholder="OKR 1")
            ger = r1c4.text_input("Gerente(s)", help="Separe por vírgula")
            r2c1, r2c2, r2c3 = st.columns([3, 1, 1])
            dsc = r2c1.text_area("Descrição do Objetivo *", height=68, placeholder="Descreva o objetivo...")
            di  = r2c2.date_input("Data Início", value=date.today())
            df_ = r2c3.date_input("Data Conclusão", value=date(date.today().year+1,12,31))
            if st.form_submit_button("💾 Cadastrar OKR", type="primary", use_container_width=True):
                if not num.strip() or not dsc.strip():
                    st.error("Preencha Número e Descrição.")
                else:
                    run_exec("INSERT INTO okr(nucleo,tipo,numero,descricao,gerente,data_inicio,data_fim) VALUES(?,?,?,?,?,?,?)",
                             (nuc,tip,num.strip(),dsc.strip(),ger.strip(),str(di),str(df_)))
                    st.success(f"✅ OKR '{num.strip()}' cadastrado!")
                    st.rerun()

    with t2:
        st.subheader("Cadastrar Resultado-Chave (KR)")
        okrs_df = get_okrs()
        if okrs_df.empty:
            st.info("Cadastre um OKR primeiro.")
        else:
            fn = st.selectbox("Filtrar Núcleo", NUCLEOS, key="kr_fn")
            dff = okrs_df[okrs_df.nucleo==fn]
            opc = {f"[{r.nucleo}] {r.numero} — {r.descricao[:55]}": r.id for r in dff.itertuples()}
            with st.form("f_kr", clear_on_submit=True):
                okr_s = st.selectbox("OKR vinculado *", list(opc.keys()))
                r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns([0.9, 2.2, 0.8, 0.8, 1])
                cod = r1c1.text_input("Código *", placeholder="KR 1.1")
                dkr = r1c2.text_input("Descrição *")
                vi  = r1c3.number_input("Val. Inicial", value=0.0, step=1.0)
                va  = r1c4.number_input("Val. Alvo", value=100.0, step=1.0)
                de  = r1c5.date_input("Data Entrega", value=date(date.today().year,12,31))
                gkr = st.text_input("Gerente(s) do KR", help="Separe por vírgula")
                if st.form_submit_button("💾 Cadastrar KR", type="primary", use_container_width=True):
                    if not cod.strip() or not dkr.strip():
                        st.error("Preencha Código e Descrição.")
                    else:
                        run_exec("INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega) VALUES(?,?,?,?,?,?,?)",
                                 (opc[okr_s],cod.strip(),dkr.strip(),vi,va,gkr.strip(),str(de)))
                        st.success(f"✅ KR '{cod.strip()}' cadastrado!")
                        st.rerun()

    with t3:
        st.subheader("Cadastrar Iniciativa")
        okrs3 = get_okrs()
        if okrs3.empty:
            st.info("Cadastre OKR e KR primeiro.")
        else:
            fn3 = st.selectbox("Filtrar Núcleo", NUCLEOS, key="in_fn")
            dff3 = okrs3[okrs3.nucleo==fn3]
            opc3 = {f"[{r.nucleo}] {r.numero} — {r.descricao[:50]}": r.id for r in dff3.itertuples()}
            s_okr = st.selectbox("OKR", list(opc3.keys()), key="in_okr")
            krs3 = get_krs(opc3[s_okr])
            if krs3.empty:
                st.info("Nenhum KR neste OKR.")
            else:
                opkr3 = {f"{r.codigo} — {r.descricao[:55]}": r.id for r in krs3.itertuples()}
                with st.form("f_ini", clear_on_submit=True):
                    s_kr3 = st.selectbox("KR vinculado *", list(opkr3.keys()))
                    r1c1, r1c2, r1c3, r1c4 = st.columns([0.6, 2.8, 1.4, 1.2])
                    num_i = r1c1.text_input("Nº *", placeholder="1")
                    dsc_i = r1c2.text_input("Descrição da Iniciativa *")
                    resp  = r1c3.text_input("Responsável(eis)", help="Separe por vírgula")
                    sts_i = r1c4.selectbox("Status", STATUS_OPTIONS)
                    if st.form_submit_button("💾 Cadastrar Iniciativa", type="primary", use_container_width=True):
                        if not num_i.strip() or not dsc_i.strip():
                            st.error("Preencha Número e Descrição.")
                        else:
                            run_exec("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",
                                     (opkr3[s_kr3],num_i.strip(),dsc_i.strip(),resp.strip(),sts_i))
                            st.success(f"✅ Iniciativa {num_i.strip()} cadastrada!")
                            st.rerun()

    with t4:
        st.subheader("Editar ou Excluir OKR")
        ne = st.selectbox("Núcleo", NUCLEOS, key="eo_n")
        oe = get_okrs(ne)
        if oe.empty:
            st.info("Nenhum OKR.")
        else:
            opce = {f"[{r.nucleo}] {r.numero} — {r.descricao[:50]}": r.id for r in oe.itertuples()}
            sel  = st.selectbox("OKR", list(opce.keys()), key="eo_sel")
            eid  = opce[sel]; er = oe[oe.id==eid].iloc[0]
            tl   = ["Estratégico","Tático/Departamental"]
            with st.form("f_eokr"):
                c1,c2,c3 = st.columns([1.5,1.5,1])
                nn  = c1.selectbox("Núcleo", NUCLEOS, index=NUCLEOS.index(er.nucleo))
                nt  = c2.selectbox("Tipo", tl, index=tl.index(er.tipo) if er.tipo in tl else 0)
                nnu = c3.text_input("Número", value=er.numero)
                nds = st.text_area("Descrição", value=er.descricao, height=70)
                c4,c5,c6 = st.columns(3)
                ng = c4.text_input("Gerente(s)", value=er.gerente or "", help="Separe múltiplos por vírgula")
                try:    div = datetime.strptime(str(er.data_inicio),"%Y-%m-%d").date()
                except: div = date.today()
                try:    dfv = datetime.strptime(str(er.data_fim),"%Y-%m-%d").date()
                except: dfv = date(date.today().year+1,12,31)
                ndi = c5.date_input("Data Início", value=div, key="eo_di")
                ndf = c6.date_input("Data Fim",    value=dfv, key="eo_df")
                cs,cx = st.columns(2)
                if cs.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                    run_exec("UPDATE okr SET nucleo=?,tipo=?,numero=?,descricao=?,gerente=?,data_inicio=?,data_fim=? WHERE id=?",
                             (nn,nt,nnu.strip(),nds.strip(),ng.strip(),str(ndi),str(ndf),eid))
                    st.success("✅ OKR atualizado!"); st.rerun()
                if cx.form_submit_button("🗑️ Excluir OKR", use_container_width=True):
                    run_exec("DELETE FROM okr WHERE id=?", (eid,))
                    st.warning("🗑️ OKR excluído."); st.rerun()

    with t5:
        st.subheader("Editar ou Excluir KR")
        nke = st.selectbox("Núcleo", NUCLEOS, key="ek_n")
        oke = get_okrs(nke)
        if oke.empty:
            st.info("Nenhum OKR.")
        else:
            opoke = {f"[{r.nucleo}] {r.numero} — {r.descricao[:45]}": r.id for r in oke.itertuples()}
            sokr  = st.selectbox("OKR", list(opoke.keys()), key="ek_okr")
            kred  = get_krs(opoke[sokr])
            if kred.empty:
                st.info("Nenhum KR.")
            else:
                opkr = {f"{r.codigo} — {r.descricao[:55]}": r.id for r in kred.itertuples()}
                skr  = st.selectbox("KR", list(opkr.keys()), key="ek_kr")
                krid = opkr[skr]; krr = kred[kred.id==krid].iloc[0]
                with st.form("f_ekr"):
                    c1,c2 = st.columns([1,2])
                    nc  = c1.text_input("Código", value=krr.codigo)
                    nd  = c2.text_input("Descrição", value=krr.descricao)
                    c3,c4,c5,c6 = st.columns(4)
                    nvi = c3.number_input("Valor Inicial", value=float(krr.valor_ini or 0))
                    nva = c4.number_input("Valor Alvo",    value=float(krr.valor_alvo or 100))
                    ngk = c5.text_input("Gerente(s)", value=krr.gerente_kr or "", help="Separe por vírgula")
                    try:    dev = datetime.strptime(str(krr.data_entrega),"%Y-%m-%d").date()
                    except: dev = date(date.today().year,12,31)
                    nde = c6.date_input("Data Entrega", value=dev, key="ek_de")
                    cs2,cx2 = st.columns(2)
                    if cs2.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                        run_exec("UPDATE kr SET codigo=?,descricao=?,valor_ini=?,valor_alvo=?,gerente_kr=?,data_entrega=? WHERE id=?",
                                 (nc.strip(),nd.strip(),nvi,nva,ngk.strip(),str(nde),krid))
                        st.success("✅ KR atualizado!"); st.rerun()
                    if cx2.form_submit_button("🗑️ Excluir KR", use_container_width=True):
                        run_exec("DELETE FROM kr WHERE id=?", (krid,))
                        st.warning("🗑️ KR excluído."); st.rerun()

    with t6:
        st.subheader("Editar ou Excluir Iniciativa")
        nie = st.selectbox("Núcleo", NUCLEOS, key="ei_n")
        oie = get_okrs(nie)
        if oie.empty:
            st.info("Nenhum OKR.")
        else:
            opie = {f"[{r.nucleo}] {r.numero} — {r.descricao[:40]}": r.id for r in oie.itertuples()}
            soie = st.selectbox("OKR", list(opie.keys()), key="ei_okr")
            kie  = get_krs(opie[soie])
            if kie.empty:
                st.info("Nenhum KR.")
            else:
                opkie = {f"{r.codigo} — {r.descricao[:50]}": r.id for r in kie.itertuples()}
                skie  = st.selectbox("KR", list(opkie.keys()), key="ei_kr")
                inie  = get_iniciativas(opkie[skie])
                if inie.empty:
                    st.info("Nenhuma iniciativa.")
                else:
                    opinie = {f"Iniciativa {r.numero}: {r.descricao[:50]}": r.id for r in inie.itertuples()}
                    sinie  = st.selectbox("Iniciativa", list(opinie.keys()), key="ei_ini")
                    iniid  = opinie[sinie]; inir = inie[inie.id==iniid].iloc[0]
                    with st.form("f_eini"):
                        c1,c2 = st.columns([1,3])
                        nni = c1.text_input("Número", value=inir.numero)
                        ndi = c2.text_input("Descrição", value=inir.descricao)
                        c3,c4 = st.columns(2)
                        nri = c3.text_input("Responsável(eis)", value=inir.responsavel or "", help="Separe por vírgula")
                        si  = STATUS_OPTIONS.index(inir.status) if inir.status in STATUS_OPTIONS else 0
                        nsi = c4.selectbox("Status", STATUS_OPTIONS, index=si)
                        ci1,ci2 = st.columns(2)
                        if ci1.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                            run_exec("UPDATE iniciativa SET numero=?,descricao=?,responsavel=?,status=? WHERE id=?",
                                     (nni.strip(),ndi.strip(),nri.strip(),nsi,iniid))
                            st.success("✅ Iniciativa atualizada!"); st.rerun()
                        if ci2.form_submit_button("🗑️ Excluir", use_container_width=True):
                            run_exec("DELETE FROM iniciativa WHERE id=?", (iniid,))
                            st.warning("🗑️ Iniciativa excluída."); st.rerun()


# ══════════════════════════════════════════════
# PÁGINA 3 — CHECK-IN
# ══════════════════════════════════════════════
elif "Check-in" in pagina:
    st.markdown('<div class="sec-title">📝 Check-in Semanal</div>', unsafe_allow_html=True)

    def quinzenas_proximas(n_meses=3):
        """Retorna lista de datas das 1ª e 3ª quintas-feiras dos próximos n_meses."""
        from calendar import monthrange
        datas = []
        hoje = date.today()
        for delta in range(n_meses):
            m = ((hoje.month - 1 + delta) % 12) + 1
            a = hoje.year + (hoje.month - 1 + delta) // 12
            dias = monthrange(a, m)[1]
            quintas = [date(a, m, d) for d in range(1, dias+1)
                       if date(a, m, d).weekday() == 3]
            if len(quintas) >= 1: datas.append(quintas[0])
            if len(quintas) >= 3: datas.append(quintas[2])
        return sorted(set(datas))

    t1, t2 = st.tabs(["📋 Preencher Check-ins", "🕓 Histórico e Edição"])

    with t1:
        hc1, hc2, hc3 = st.columns([1, 1.2, 1.4])
        cn_b = hc1.selectbox("Núcleo", NUCLEOS, key="ci_nucleo")

        datas_q = quinzenas_proximas(3)
        hoje = date.today()
        # Mostra datas no formato dd/mm/yyyy — sem rótulo de "1ª quinta"
        opcoes_dt = {d.strftime("%d/%m/%Y"): d for d in datas_q}
        # Default: quinzena mais próxima da hoje
        idx_def = 0
        for i, d in enumerate(datas_q):
            if d >= hoje:
                idx_def = i
                break
        sel_dt_str = hc2.selectbox("Quinzena", list(opcoes_dt.keys()),
                                   index=idx_def, key="ci_quinzena")
        dt_b = opcoes_dt[sel_dt_str]

        mostrar_pend = hc3.checkbox("Exibir só pendentes", value=False, key="ci_filtro")

        krs_nucleo = run_query("""
            SELECT kr.id, kr.codigo, kr.descricao, kr.valor_ini, kr.valor_alvo,
                   okr.numero as okr_num, okr.descricao as okr_desc
            FROM kr JOIN okr ON kr.okr_id = okr.id
            WHERE okr.nucleo = ?
            ORDER BY okr.numero, kr.codigo
        """, (cn_b,))

        if krs_nucleo.empty:
            st.info(f"Nenhum KR cadastrado para {cn_b}.")
        else:
            feitos = run_query("SELECT DISTINCT kr_id FROM checkin WHERE data_ref=?", (str(dt_b),))
            ids_feitos = set(feitos["kr_id"].tolist()) if not feitos.empty else set()

            total_krs    = len(krs_nucleo)
            total_feitos = len(ids_feitos & set(krs_nucleo["id"].tolist()))
            total_pend   = total_krs - total_feitos
            pct          = (total_feitos / total_krs * 100) if total_krs > 0 else 0
            cor_p        = "#096B38" if pct == 100 else "#1857D4" if pct >= 50 else "#C48C00"

            st.markdown(f"""
            <div style="background:#F0F6FF;border-radius:10px;padding:10px 18px;margin-bottom:14px;
                        border:1px solid #B8D0EE;display:flex;align-items:center;gap:16px;">
              <div style="flex:1;">
                <div style="font-size:0.78rem;font-weight:700;color:#0A1F5C;margin-bottom:5px;">
                  {cn_b} — {sel_dt_str}
                </div>
                <div style="background:#B8D4F0;border-radius:99px;height:10px;overflow:hidden;">
                  <div style="width:{pct:.0f}%;height:10px;border-radius:99px;
                              background:linear-gradient(90deg,{cor_p},{cor_p}BB);"></div>
                </div>
              </div>
              <div style="text-align:right;min-width:120px;">
                <span style="font-size:1.5rem;font-weight:700;color:{cor_p};">{total_feitos}/{total_krs}</span>
                <span style="font-size:0.72rem;color:#4A6080;display:block;">
                  {"✅ Todos feitos!" if total_pend==0 else f"⏳ {total_pend} pendente{'s' if total_pend>1 else ''}"}
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            krs_exibir = krs_nucleo[~krs_nucleo["id"].isin(ids_feitos)].copy() if mostrar_pend else krs_nucleo.copy()

            if krs_exibir.empty:
                st.success("✅ Todos os KRs já têm check-in para esta quinzena!")
            else:
                # Cabeçalho usando as MESMAS proporções das colunas do form abaixo
                COL_W = [0.55, 2.8, 0.7, 0.8, 0.95, 1.1]
                h_cols = st.columns(COL_W)
                for col, lb in zip(h_cols, ["KR","DESCRIÇÃO","PROGRESSO","META","VALOR ATUAL","STATUS"]):
                    col.markdown(
                        f'<div style="background:#0A1F5C;color:#B8CDE8;font-size:0.69rem;font-weight:700;'
                        f'letter-spacing:0.5px;text-transform:uppercase;padding:6px 4px;'
                        f'text-align:center;border-radius:4px;">{lb}</div>',
                        unsafe_allow_html=True,
                    )

                with st.form("f_ci_lote", clear_on_submit=False):
                    okr_ant = None
                    inputs  = {}

                    for row in krs_exibir.itertuples():
                        if row.okr_num != okr_ant:
                            okr_ant = row.okr_num
                            st.markdown(
                                f'<div style="background:#EAF1FB;border-left:4px solid #1857D4;'
                                f'padding:5px 12px;font-size:0.8rem;font-weight:700;color:#0A1F5C;'
                                f'margin:6px 0 0;border-radius:0 5px 5px 0;">'
                                f'🎯 {row.okr_num} — {row.okr_desc[:75]}</div>',
                                unsafe_allow_html=True,
                            )

                        chkr  = get_checkins(row.id)
                        uv    = float(row.valor_ini)
                        if not chkr.empty and chkr.iloc[0]["valor_atual"] is not None:
                            uv = float(chkr.iloc[0]["valor_atual"])
                        prog  = calc_progresso_kr(row.valor_ini, row.valor_alvo, chkr)
                        cor   = "#096B38" if prog >= 80 else "#1857D4" if prog >= 40 else "#C48C00"
                        feito = row.id in ids_feitos
                        badge = (' <span style="background:#D4EFE1;color:#096B38;border-radius:3px;'
                                 'padding:1px 5px;font-size:0.62rem;font-weight:700;">✓</span>'
                                 if feito else "")

                        g1, g2, g3, g4, g5, g6 = st.columns(COL_W)
                        g1.markdown(
                            f'<div style="padding-top:8px;font-weight:700;font-size:0.82rem;'
                            f'color:#0A1F5C;">{row.codigo}{badge}</div>', unsafe_allow_html=True)
                        g2.markdown(
                            f'<div style="padding-top:8px;font-size:0.8rem;color:#2C3E6B;">'
                            f'{row.descricao[:75]}</div>', unsafe_allow_html=True)
                        g3.markdown(
                            f'<div style="padding-top:4px;text-align:center;">'
                            f'<div style="background:#B8D4F0;border-radius:99px;height:8px;overflow:hidden;">'
                            f'<div style="width:{prog:.0f}%;height:8px;border-radius:99px;background:{cor};"></div>'
                            f'</div><div style="font-size:0.7rem;font-weight:700;color:{cor};">{prog:.0f}%</div>'
                            f'</div>', unsafe_allow_html=True)
                        g4.markdown(
                            f'<div style="padding-top:8px;font-size:0.75rem;color:#4A6080;text-align:center;">'
                            f'{row.valor_ini:.0f}→{row.valor_alvo:.0f}</div>', unsafe_allow_html=True)
                        val_w = g5.number_input("v", value=uv, step=1.0,
                                                label_visibility="collapsed", key=f"val_{row.id}")
                        sts_w = g6.selectbox("s", STATUS_OPTIONS,
                                             label_visibility="collapsed", key=f"sts_{row.id}")
                        inputs[row.id] = (val_w, sts_w)

                    st.markdown("<br>", unsafe_allow_html=True)
                    com_geral = st.text_input(
                        "💬 Comentário geral (opcional)",
                        placeholder="Ex: Dados consolidados, revisão de metas...",
                        key="ci_com",
                    )
                    n = len(inputs)
                    if st.form_submit_button(
                        f"💾  Salvar {n} check-in{'s' if n>1 else ''}  —  {cn_b}  ·  {sel_dt_str}",
                        type="primary", use_container_width=True,
                    ):
                        for kr_id, (val, sts) in inputs.items():
                            run_exec(
                                "INSERT INTO checkin(kr_id,data_ref,semana,valor_atual,status,comentario)"
                                " VALUES(?,?,?,?,?,?)",
                                (kr_id, str(dt_b), sel_dt_str, val, sts, com_geral.strip()),
                            )
                        st.success(f"✅ {n} check-in{'s' if n>1 else ''} registrado{'s' if n>1 else ''}!")
                        st.rerun()

    with t2:
        st.subheader("Histórico de Check-ins por KR")
        h1, h2, h3 = st.columns(3)
        hn  = h1.selectbox("Núcleo", NUCLEOS, key="hi_n")
        oh  = get_okrs(hn)
        if oh.empty:
            st.info("Nenhum OKR.")
        else:
            opoh = {f"{r.numero} — {r.descricao[:45]}": r.id for r in oh.itertuples()}
            soh  = h2.selectbox("OKR", list(opoh.keys()), key="hi_okr")
            kh   = get_krs(opoh[soh])
            if kh.empty:
                st.info("Nenhum KR.")
            else:
                opkh = {f"{r.codigo} — {r.descricao[:50]}": r.id for r in kh.itertuples()}
                skh  = h3.selectbox("KR", list(opkh.keys()), key="hi_kr")
                khid = opkh[skh]
                chh  = get_checkins(khid)
                if chh.empty:
                    st.info("Nenhum check-in registrado.")
                else:
                    st.dataframe(
                        chh[["data_ref","semana","valor_atual","status","comentario","criado_em"]].rename(
                            columns={"data_ref":"Data","semana":"Quinzena","valor_atual":"Valor Atual",
                                     "status":"Status","comentario":"Comentário","criado_em":"Registrado em"}),
                        use_container_width=True, hide_index=True)

                    st.markdown("#### ✏️ Editar Check-in")
                    opch    = {f"{r.data_ref}  ·  Val: {r.valor_atual}  ·  {r.status}": r.id
                               for r in chh.itertuples()}
                    sch     = st.selectbox("Selecione", list(opch.keys()), key="hi_ced")
                    chid_ed = opch[sch]; chr_ = chh[chh.id==chid_ed].iloc[0]
                    with st.form("f_ech"):
                        ec1, ec2 = st.columns(2)
                        try:    drv = datetime.strptime(str(chr_.data_ref),"%Y-%m-%d").date()
                        except: drv = date.today()
                        ndr  = ec1.date_input("Data", value=drv, key="hi_dr")
                        si   = STATUS_OPTIONS.index(chr_.status) if chr_.status in STATUS_OPTIONS else 0
                        nsts = ec2.selectbox("Status", STATUS_OPTIONS, index=si)
                        nvat = st.number_input("Valor Atual", value=float(chr_.valor_atual or 0))
                        ncom = st.text_area("Comentário", value=chr_.comentario or "", height=60)
                        es1, es2 = st.columns(2)
                        if es1.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                            run_exec("UPDATE checkin SET data_ref=?,valor_atual=?,status=?,comentario=? WHERE id=?",
                                     (str(ndr),nvat,nsts,ncom.strip(),chid_ed))
                            st.success("✅ Atualizado!"); st.rerun()
                        if es2.form_submit_button("🗑️ Excluir", use_container_width=True):
                            run_exec("DELETE FROM checkin WHERE id=?", (chid_ed,))
                            st.warning("🗑️ Excluído."); st.rerun()


# ══════════════════════════════════════════════
# PÁGINA 4 — DASHBOARD
# ══════════════════════════════════════════════
elif "Dashboard" in pagina:
    st.markdown('<div class="sec-title">📊 Dashboard de OKRs e KRs</div>', unsafe_allow_html=True)

    all_okrs = get_okrs()
    if all_okrs.empty:
        st.info("Nenhum dado cadastrado ainda.")
        st.stop()

    all_krs  = run_query("SELECT kr.id,kr.codigo,kr.descricao,kr.valor_ini,kr.valor_alvo,okr.nucleo,okr.numero as okr_num,okr.tipo FROM kr JOIN okr ON kr.okr_id=okr.id")
    all_chk  = run_query("SELECT id,kr_id,data_ref,valor_atual,status FROM checkin")
    all_inis = run_query("SELECT * FROM iniciativa")

    rows = []
    for kr in all_krs.itertuples():
        chkr  = all_chk[all_chk.kr_id==kr.id]  if not all_chk.empty  else pd.DataFrame()
        inis  = all_inis[all_inis.kr_id==kr.id] if not all_inis.empty else pd.DataFrame()
        prog_kr  = calc_progresso_kr(kr.valor_ini, kr.valor_alvo, chkr)
        prog_ini = calc_progresso_iniciativas(inis)
        n_ini   = len(inis)
        n_conc  = len(inis[inis.status=="Concluído"]) if n_ini > 0 else 0
        us = None
        if not chkr.empty:
            us = chkr.sort_values("data_ref",ascending=False).iloc[0]["status"]
        rows.append({
            "kr_id":kr.id,"nucleo":kr.nucleo,"okr_num":kr.okr_num,"tipo":kr.tipo,
            "kr_cod":kr.codigo,"kr_desc":kr.descricao,"valor_ini":kr.valor_ini,
            "valor_alvo":kr.valor_alvo,"prog_kr":prog_kr,"prog_ini":prog_ini,
            "n_ini":n_ini,"n_conc":n_conc,"ultimo_status":us,"n_checkins":len(chkr),
        })
    dp = pd.DataFrame(rows) if rows else pd.DataFrame()

    # ── MÉTRICAS
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("OKRs",           len(all_okrs))
    m2.metric("KRs",            len(all_krs)  if not all_krs.empty  else 0)
    m3.metric("Iniciativas",    len(all_inis) if not all_inis.empty else 0)
    m4.metric("Check-ins",      len(all_chk)  if not all_chk.empty  else 0)
    m5.metric("Progresso KR",   f"{dp['prog_kr'].mean():.1f}%"  if not dp.empty else "0%")
    m6.metric("Prog. Iniciativas", f"{dp['prog_ini'].mean():.1f}%" if not dp.empty else "0%")
    st.markdown("---")

    # ── FILTROS
    fc1,fc2,fc3 = st.columns(3)
    fn = fc1.selectbox("Núcleo", NUCLEOS, key="d_n")
    ft = fc2.selectbox("Tipo",   ["Todos","Estratégico","Tático/Departamental"], key="d_t")
    fs = fc3.selectbox("Status", ["Todos"]+STATUS_OPTIONS, key="d_s")

    df_f = dp.copy() if not dp.empty else pd.DataFrame()
    if not df_f.empty:
        df_f = df_f[df_f.nucleo==fn]
        if ft != "Todos": df_f = df_f[df_f.tipo==ft]
        if fs != "Todos": df_f = df_f[df_f.ultimo_status==fs]

    if df_f.empty:
        st.warning("Nenhum dado com esses filtros."); st.stop()

    # Paleta de azuis coerente
    BLUE_SCALE = ["#D6E8FA","#93C5FD","#4A9EE8","#2878D6","#1857D4","#0A1F5C"]
    cores_status = {
        "Concluído":    "#1857D4",
        "Em Andamento": "#4A9EE8",
        "Não Iniciado": "#93C5FD",
        "Atrasado":     "#B91C1C",
        "Cancelado":    "#94A3B8",
        "Sem check-in": "#E2E8F0",
    }

    # ── GRÁFICOS LADO A LADO
    cg1, cg2 = st.columns(2)
    with cg1:
        pn = df_f.groupby("nucleo")[["prog_kr","prog_ini"]].mean().reset_index()
        pn = pn.sort_values("prog_kr", ascending=True)
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            name="Progresso KR", x=pn["prog_kr"], y=pn["nucleo"],
            orientation="h", marker_color="#2878D6",
            text=pn["prog_kr"].apply(lambda v: f"{v:.1f}%"), textposition="outside",
        ))
        fig1.add_trace(go.Bar(
            name="Prog. Iniciativas", x=pn["prog_ini"], y=pn["nucleo"],
            orientation="h", marker_color="#C48C00",
            text=pn["prog_ini"].apply(lambda v: f"{v:.1f}%"), textposition="outside",
            visible="legendonly",
        ))
        fig1.update_layout(
            title="Progresso Médio por Núcleo",
            barmode="group", xaxis=dict(range=[0,120], title="%"),
            height=340, paper_bgcolor="white", plot_bgcolor="#F7F9FC",
            font=dict(family="IBM Plex Sans", color="#0A1F5C"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig1, use_container_width=True)

    with cg2:
        sc = df_f["ultimo_status"].fillna("Sem check-in").value_counts().reset_index()
        sc.columns = ["Status","Qtd"]
        fig2 = px.pie(sc, names="Status", values="Qtd", title="Status dos KRs",
                      color="Status", color_discrete_map=cores_status, hole=0.42)
        fig2.update_layout(height=340, paper_bgcolor="white",
                           font=dict(family="IBM Plex Sans", color="#0A1F5C"))
        st.plotly_chart(fig2, use_container_width=True)

    # ── BARRAS: KR vs Iniciativas
    st.markdown("### 📈 Progresso por KR (KR e Iniciativas)")
    dfs = df_f.sort_values(["nucleo","okr_num","kr_cod"]).copy()
    dfs["label"] = dfs["nucleo"] + " | " + dfs["kr_cod"]

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        name="Progresso KR",
        x=dfs["prog_kr"], y=dfs["label"], orientation="h",
        marker_color="#2878D6",
        text=dfs["prog_kr"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>KR: %{x:.1f}%<extra></extra>",
    ))
    fig3.add_trace(go.Bar(
        name="Prog. Iniciativas",
        x=dfs["prog_ini"], y=dfs["label"], orientation="h",
        marker_color="#C48C00",
        text=dfs["prog_ini"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Iniciativas: %{x:.1f}%<extra></extra>",
    ))
    fig3.add_shape(type="line", x0=100, y0=-0.5, x1=100, y1=len(dfs)-0.5,
                   line=dict(color="#8BA4BF", width=1, dash="dot"))
    fig3.update_layout(
        barmode="group",
        title="Progresso Individual por KR e Iniciativas",
        xaxis=dict(range=[0,125], title="Progresso (%)"),
        yaxis=dict(automargin=True),
        height=max(340, len(dfs)*48+80),
        paper_bgcolor="white", plot_bgcolor="#F7F9FC",
        font=dict(family="IBM Plex Sans", color="#0A1F5C"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        margin=dict(l=10, r=80),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── EVOLUÇÃO TEMPORAL
    if not all_chk.empty:
        ids = df_f["kr_id"].tolist()
        cf  = all_chk[all_chk.kr_id.isin(ids)].copy()
        if not cf.empty:
            cf["data_ref"] = pd.to_datetime(cf["data_ref"])
            cf = cf.merge(df_f[["kr_id","nucleo","kr_cod","valor_ini","valor_alvo"]], on="kr_id")
            cf["prog_chk"] = cf.apply(
                lambda r: max(0,min(100,(float(r["valor_atual"])-float(r["valor_ini"]))/
                              max(float(r["valor_alvo"])-float(r["valor_ini"]),0.001)*100))
                if r["valor_atual"] is not None else 0, axis=1)
            cf["lbl"] = cf["nucleo"] + " | " + cf["kr_cod"]
            top = cf.groupby("kr_id")["data_ref"].max().nlargest(10).index.tolist()
            cp2 = cf[cf.kr_id.isin(top)]
            if not cp2.empty:
                fig4 = px.line(
                    cp2.sort_values("data_ref"), x="data_ref", y="prog_chk", color="lbl",
                    title="Evolução do Progresso ao Longo do Tempo", markers=True,
                    labels={"data_ref":"Data","prog_chk":"Progresso (%)","lbl":"KR"},
                    color_discrete_sequence=BLUE_SCALE * 3,
                )
                fig4.update_layout(
                    height=380, yaxis=dict(range=[0,110]),
                    paper_bgcolor="white", plot_bgcolor="#F7F9FC",
                    font=dict(family="IBM Plex Sans", color="#0A1F5C"),
                )
                st.plotly_chart(fig4, use_container_width=True)

    # ── INICIATIVAS POR STATUS
    if not all_inis.empty:
        st.markdown("### ⚡ Iniciativas por Status")
        ij = all_inis.merge(
            run_query("SELECT kr.id as kr_id, okr.nucleo FROM kr JOIN okr ON kr.okr_id=okr.id"),
            on="kr_id")
        ij = ij[ij.nucleo==fn]
        if not ij.empty:
            pi = ij["status"].value_counts().reset_index()
            pi.columns = ["Status","Qtd"]
            fig5 = px.bar(pi, x="Status", y="Qtd", title="Iniciativas por Status",
                          color="Status", color_discrete_map=cores_status, text="Qtd")
            fig5.update_traces(textposition="outside")
            fig5.update_layout(
                height=290, showlegend=False,
                paper_bgcolor="white", plot_bgcolor="#F7F9FC",
                font=dict(family="IBM Plex Sans", color="#0A1F5C"),
            )
            st.plotly_chart(fig5, use_container_width=True)

    # ── TABELA RESUMO
    st.markdown("### 🗂️ Tabela Resumo")
    dtab = df_f[["nucleo","tipo","okr_num","kr_cod","kr_desc","valor_ini","valor_alvo",
                 "prog_kr","prog_ini","n_ini","n_conc","ultimo_status","n_checkins"]].copy()
    dtab.columns = ["Núcleo","Tipo","OKR","KR","Descrição KR","Val.Ini","Val.Alvo",
                    "Prog.KR(%)","Prog.Ini(%)","Iniciativas","Concluídas","Último Status","Check-ins"]
    dtab["Prog.KR(%)"]  = dtab["Prog.KR(%)"].round(1)
    dtab["Prog.Ini(%)"] = dtab["Prog.Ini(%)"].round(1)

    def hp_kr(v):
        try:
            fv = float(v)
            if fv >= 80:  return "background-color:#DBEAFE;color:#1E3A8A;font-weight:600"
            elif fv >= 50:return "background-color:#BFDBFE;color:#1E40AF;font-weight:600"
            elif fv >= 20:return "background-color:#EFF6FF;color:#1D4ED8"
            else:         return "background-color:#FEF2F2;color:#B91C1C"
        except: return ""

    def hp_ini(v):
        try:
            fv = float(v)
            if fv >= 80:  return "background-color:#FEF3C7;color:#92400E;font-weight:600"
            elif fv >= 50:return "background-color:#FEF9C3;color:#A16207"
            elif fv >= 20:return "background-color:#FFFBEB;color:#B45309"
            else:         return "background-color:#FFF7ED;color:#C2410C"
        except: return ""

    st.dataframe(
        dtab.style
            .applymap(hp_kr,  subset=["Prog.KR(%)"])
            .applymap(hp_ini, subset=["Prog.Ini(%)"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        '<div class="footer">Sistema OKR · Justiça Federal · Seção Judiciária do Ceará · Projeto Justiça Centrada nas Pessoas · PNUD</div>',
        unsafe_allow_html=True,
    )