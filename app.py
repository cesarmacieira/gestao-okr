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
    page_title="Sistema OKR | JF-CE",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

NUCLEOS = ["NEGI", "COMUNICAÇÃO", "DTIC", "NGP", "NIAP", "NIST", "NUAUD", "NUFIP", "NUJUD", "TESTE"]
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

def popular_dados_teste():
    conn = get_conn()
    existe = conn.execute("SELECT COUNT(*) FROM okr WHERE nucleo='TESTE'").fetchone()[0]
    if existe > 0:
        conn.close()
        return
    cur = conn.cursor()

    cur.execute("""INSERT INTO okr(nucleo,tipo,numero,descricao,gerente,data_inicio,data_fim)
        VALUES('TESTE','Estratégico','OKR 1','Atingir 90% dos índices de Governança do Questionário iESGO (TCU)',
        'João Silva','2025-01-07','2026-12-31')""")
    okr1 = cur.lastrowid

    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 1.1','Identificar os pontos de melhoria',0,100,'Maria Souza','2025-12-19')""", (okr1,))
    kr11 = cur.lastrowid
    for n,d,r,s in [("1","Avaliar e priorizar os pontos de melhoria","Carlos","Em Andamento"),
                     ("2","Classificar os pontos de melhorias por relevância","Ana","Concluído"),
                     ("3","Desenvolver um cronograma de implantação","Pedro","Concluído")]:
        cur.execute("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",(kr11,n,d,r,s))
    for dt,sm,v,s,c in [("2025-01-15","Semana 03/2025",40,"Em Andamento","Levantamento inicial concluído"),
                         ("2025-02-05","Semana 06/2025",70,"Em Andamento","Priorização em andamento"),
                         ("2025-03-01","Semana 09/2025",96,"Em Andamento","Quase concluído")]:
        cur.execute("INSERT INTO checkin(kr_id,data_ref,semana,valor_atual,status,comentario) VALUES(?,?,?,?,?,?)",(kr11,dt,sm,v,s,c))

    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 1.2','Implantar 90% dos pontos de melhorias do iESGO',0,100,'Lucas Lima','2025-12-31')""", (okr1,))
    kr12 = cur.lastrowid
    for n,d,r,s in [("1","Executar plano de implantação","Lucas","Não Iniciado"),
                     ("2","Monitorar execução quinzenal","Fernanda","Em Andamento")]:
        cur.execute("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",(kr12,n,d,r,s))
    cur.execute("INSERT INTO checkin(kr_id,data_ref,semana,valor_atual,status,comentario) VALUES(?,?,?,?,?,?)",
                (kr12,"2025-03-01","Semana 09/2025",20,"Em Andamento","Início do plano"))

    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 1.3','Estabelecer plano de ação para demais Núcleos',0,8,'Rafael Costa','2025-06-30')""", (okr1,))
    kr13 = cur.lastrowid
    for n,d,r,s in [("1","Reunião com líderes dos núcleos","Rafael","Concluído"),
                     ("2","Elaborar guia de boas práticas","Juliana","Em Andamento"),
                     ("3","Apresentar plano ao comitê gestor","Rafael","Não Iniciado")]:
        cur.execute("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",(kr13,n,d,r,s))
    cur.execute("INSERT INTO checkin(kr_id,data_ref,semana,valor_atual,status,comentario) VALUES(?,?,?,?,?,?)",
                (kr13,"2025-03-01","Semana 09/2025",4,"Em Andamento","4 de 8 núcleos engajados"))

    cur.execute("""INSERT INTO okr(nucleo,tipo,numero,descricao,gerente,data_inicio,data_fim)
        VALUES('TESTE','Estratégico','OKR 2','Melhorar o índice de satisfação dos usuários para 85%',
        'Ana Paula','2025-01-07','2026-12-31')""")
    okr2 = cur.lastrowid

    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 2.1','Implementar pesquisa de satisfação trimestral',0,4,'Carla Dias','2025-12-31')""", (okr2,))
    kr21 = cur.lastrowid
    for n,d,r,s in [("1","Criar formulário de pesquisa","Carla","Concluído"),
                     ("2","Aplicar 1ª rodada de pesquisa","Bruno","Concluído"),
                     ("3","Analisar resultados e propor melhorias","Carla","Em Andamento")]:
        cur.execute("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",(kr21,n,d,r,s))
    cur.execute("INSERT INTO checkin(kr_id,data_ref,semana,valor_atual,status,comentario) VALUES(?,?,?,?,?,?)",
                (kr21,"2025-03-01","Semana 09/2025",1,"Em Andamento","1ª pesquisa aplicada"))

    cur.execute("""INSERT INTO kr(okr_id,codigo,descricao,valor_ini,valor_alvo,gerente_kr,data_entrega)
        VALUES(?,'KR 2.2','Reduzir tempo médio de resposta para 3 dias úteis',10,3,'Diego Melo','2025-09-30')""", (okr2,))
    kr22 = cur.lastrowid
    for n,d,r,s in [("1","Mapear fluxo atual de demandas","Diego","Concluído"),
                     ("2","Implementar sistema de triagem","Patrícia","Em Andamento"),
                     ("3","Treinar equipe no novo fluxo","Diego","Não Iniciado")]:
        cur.execute("INSERT INTO iniciativa(kr_id,numero,descricao,responsavel,status) VALUES(?,?,?,?,?)",(kr22,n,d,r,s))
    cur.execute("INSERT INTO checkin(kr_id,data_ref,semana,valor_atual,status,comentario) VALUES(?,?,?,?,?,?)",
                (kr22,"2025-03-01","Semana 09/2025",6,"Em Andamento","Reduzindo gradualmente"))

    conn.commit()
    conn.close()

init_db()
popular_dados_teste()

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
    return run_query("SELECT * FROM checkin WHERE kr_id=? ORDER BY data_ref DESC", (kr_id,))

def calc_progresso_kr(ini, alvo, checkins_df):
    ini, alvo = float(ini or 0), float(alvo or 100)
    if checkins_df is None or checkins_df.empty:
        return 0.0
    ult = checkins_df.sort_values("data_ref", ascending=False).iloc[0]["valor_atual"]
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
  /* Paleta principal: Azul institucional refinado */
  --navy:      #0C2461;
  --navy-mid:  #1a3a7a;
  --blue:      #1E5FBB;
  --blue-mid:  #2878D6;
  --blue-lit:  #4A9EE8;
  --sky:       #D6E8FA;
  --sky-lit:   #EBF4FD;
  --sky-dim:   #C8DFF7;

  /* Neutros (sem cinzas frios isolados) */
  --off-white: #F7F9FC;
  --white:     #FFFFFF;
  --slate:     #3D5475;
  --slate-mid: #5A728F;
  --slate-lit: #8BA4BF;
  --border:    #C8D8EA;

  /* Semânticos */
  --green:     #0D7A45;
  --green-bg:  #E6F5EE;
  --amber:     #B45309;
  --amber-bg:  #FEF3C7;
  --red:       #B91C1C;
  --red-bg:    #FEE2E2;
  --gray-s:    #64748B;
  --gray-bg:   #F1F5F9;

  /* Gold accent */
  --gold:      #D4A017;
  --gold-bg:   #FEF9E7;
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
  background: var(--gold) !important;
  color: var(--navy) !important;
  border: none;
  border-radius: 6px;
  font-weight: 700;
  font-size: 0.84rem;
  width: calc(100% - 40px) !important;
  margin: 0 20px !important;
  padding: 10px 16px !important;
}
[data-testid="stSidebar"] .stDownloadButton > button:hover {
  background: #c49010 !important;
  transform: none !important;
}

/* ── HEADER ── */
.header-bar {
  background: linear-gradient(135deg, #0C2461 0%, #1a3a7a 50%, #1E5FBB 100%);
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
  background: var(--sky-lit);
  border-radius: 10px;
  padding: 4px;
  gap: 3px;
  width: 100%;
  display: flex;
  border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 7px;
  font-weight: 600;
  font-size: 0.83rem;
  color: var(--slate);
  flex: 1;
  text-align: center;
  padding: 10px 6px;
  white-space: nowrap;
}
.stTabs [aria-selected="true"] {
  background: var(--blue) !important;
  color: white !important;
  box-shadow: 0 2px 8px rgba(30,95,187,0.25);
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 20px; }

/* ── BOTÕES ── */
.stButton > button, .stFormSubmitButton > button {
  background: var(--blue) !important;
  color: white !important;
  border: none;
  border-radius: 7px;
  font-weight: 600;
  font-family: 'IBM Plex Sans', sans-serif;
  transition: background 0.2s;
  padding: 8px 20px;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  background: var(--navy-mid) !important;
  box-shadow: 0 3px 12px rgba(12,36,97,0.25);
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
  height: 6px;
  width: 100%;
  margin: 5px 0 2px 44px;
  overflow: hidden;
  width: calc(100% - 44px);
}
.prog-ini-fill {
  height: 6px;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--gold), #F59E0B);
  transition: width 0.4s ease;
}
.prog-ini-label {
  font-size: 0.73rem;
  color: var(--amber);
  font-weight: 600;
  margin-left: 44px;
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
  background: var(--sky-lit);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 4px !important;
}
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stDateInput"] label {
  font-weight: 600;
  color: var(--slate);
  font-size: 0.81rem;
}

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
def status_tag(status):
    mapa  = {"Concluído":"tag-c","Em Andamento":"tag-a","Não Iniciado":"tag-n","Atrasado":"tag-at","Cancelado":"tag-ca"}
    icons = {"Concluído":"✓","Em Andamento":"◎","Não Iniciado":"○","Atrasado":"⚑","Cancelado":"✕"}
    cls   = mapa.get(status, "tag-n")
    ic    = icons.get(status, "•")
    return f'<span class="tag {cls}">{ic} {status}</span>'

def barra_kr(pct):
    return f"""
    <div class="prog-kr-wrap"><div class="prog-kr-fill" style="width:{pct:.1f}%;"></div></div>
    <span class="prog-kr-label">Progresso KR: <b>{pct:.1f}%</b></span>
    """

def barra_ini(pct, total, concluidas):
    return f"""
    <div class="prog-ini-wrap"><div class="prog-ini-fill" style="width:{pct:.1f}%;"></div></div>
    <span class="prog-ini-label">Iniciativas concluídas: <b>{int(concluidas)}/{int(total)}</b> ({pct:.0f}%)</span>
    """


# ══════════════════════════════════════════════
# PÁGINA 1 — VISÃO HIERÁRQUICA
# ══════════════════════════════════════════════
if "Visão" in pagina:
    st.markdown('<div class="sec-title">🏠 Visão Hierárquica</div>', unsafe_allow_html=True)
    st.caption("OKR → KR → Iniciativas com progresso em tempo real")

    cf1, cf2 = st.columns([1, 3])
    f_nucleo = cf1.selectbox("Núcleo", ["Todos"] + NUCLEOS, key="vh_n")
    f_tipo   = cf2.selectbox("Tipo OKR", ["Todos", "Estratégico", "Tático/Departamental"], key="vh_t")

    okrs_all = get_okrs() if f_nucleo == "Todos" else get_okrs(f_nucleo)
    if f_tipo != "Todos":
        okrs_all = okrs_all[okrs_all.tipo == f_tipo]

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
                expanded=True
            ):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.markdown(
                    f'<span class="tag tag-nucleo">{okr.nucleo}</span>'
                    f'<span class="tag tag-tipo">{okr.tipo}</span>',
                    unsafe_allow_html=True,
                )
                c2.markdown(f"👤 **{okr.gerente or '—'}**")
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
                      <small style="color:#5A728F;">
                        👤 {kr.gerente_kr or '—'} &nbsp;·&nbsp;
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
                          &nbsp;·&nbsp; 👤 {ini.responsavel or '—'}
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

    t1,t2,t3,t4,t5,t6 = st.tabs([
        "➕ Novo OKR", "➕ Novo KR", "➕ Nova Iniciativa",
        "✏️ Editar OKR", "✏️ Editar KR", "✏️ Editar Iniciativa",
    ])

    with t1:
        st.subheader("Cadastrar Objetivo (OKR)")
        with st.form("f_okr", clear_on_submit=True):
            c1,c2,c3 = st.columns([1.5,1.5,1])
            nuc = c1.selectbox("Núcleo *", NUCLEOS)
            tip = c2.selectbox("Tipo *", ["Estratégico","Tático/Departamental"])
            num = c3.text_input("Número (ex: OKR 1) *")
            dsc = st.text_area("Descrição do Objetivo *", height=80)
            c4,c5,c6 = st.columns(3)
            ger = c4.text_input("Gerente do OKR")
            di  = c5.date_input("Data Início", value=date.today())
            df_ = c6.date_input("Data Conclusão", value=date(date.today().year+1,12,31))
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
            fn = st.selectbox("Filtrar Núcleo", ["Todos"]+NUCLEOS, key="kr_fn")
            dff = okrs_df if fn=="Todos" else okrs_df[okrs_df.nucleo==fn]
            opc = {f"[{r.nucleo}] {r.numero} — {r.descricao[:55]}": r.id for r in dff.itertuples()}
            with st.form("f_kr", clear_on_submit=True):
                okr_s = st.selectbox("OKR vinculado *", list(opc.keys()))
                c1,c2 = st.columns([1,2])
                cod = c1.text_input("Código KR (ex: KR 1.1) *")
                dkr = c2.text_input("Descrição *")
                c3,c4,c5,c6 = st.columns(4)
                vi = c3.number_input("Valor Inicial", value=0.0, step=1.0)
                va = c4.number_input("Valor Alvo", value=100.0, step=1.0)
                gkr = c5.text_input("Gerente KR")
                de  = c6.date_input("Data Entrega", value=date(date.today().year,12,31))
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
            fn3 = st.selectbox("Filtrar Núcleo", ["Todos"]+NUCLEOS, key="in_fn")
            dff3 = okrs3 if fn3=="Todos" else okrs3[okrs3.nucleo==fn3]
            opc3 = {f"[{r.nucleo}] {r.numero} — {r.descricao[:50]}": r.id for r in dff3.itertuples()}
            s_okr = st.selectbox("OKR", list(opc3.keys()), key="in_okr")
            krs3 = get_krs(opc3[s_okr])
            if krs3.empty:
                st.info("Nenhum KR neste OKR.")
            else:
                opkr3 = {f"{r.codigo} — {r.descricao[:55]}": r.id for r in krs3.itertuples()}
                with st.form("f_ini", clear_on_submit=True):
                    s_kr3 = st.selectbox("KR vinculado *", list(opkr3.keys()))
                    c1,c2 = st.columns([1,3])
                    num_i = c1.text_input("Número (ex: 1) *")
                    dsc_i = c2.text_input("Descrição da Iniciativa *")
                    c3,c4 = st.columns(2)
                    resp  = c3.text_input("Responsável")
                    sts_i = c4.selectbox("Status", STATUS_OPTIONS)
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
        ne = st.selectbox("Núcleo", ["Todos"]+NUCLEOS, key="eo_n")
        oe = get_okrs() if ne=="Todos" else get_okrs(ne)
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
                ng = c4.text_input("Gerente", value=er.gerente or "")
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
        nke = st.selectbox("Núcleo", ["Todos"]+NUCLEOS, key="ek_n")
        oke = get_okrs() if nke=="Todos" else get_okrs(nke)
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
                    ngk = c5.text_input("Gerente", value=krr.gerente_kr or "")
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
        nie = st.selectbox("Núcleo", ["Todos"]+NUCLEOS, key="ei_n")
        oie = get_okrs() if nie=="Todos" else get_okrs(nie)
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
                        nri = c3.text_input("Responsável", value=inir.responsavel or "")
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
    st.markdown('<div class="sec-title">📝 Preenchimento Semanal de Check-in</div>', unsafe_allow_html=True)

    t1, t2 = st.tabs(["➕ Novo Check-in", "📋 Histórico e Edição"])

    with t1:
        c1,c2 = st.columns(2)
        cn  = c1.selectbox("Núcleo", NUCLEOS, key="ci_n")
        oci = get_okrs(cn)
        if oci.empty:
            st.info(f"Nenhum OKR para {cn}.")
        else:
            opci = {f"{r.numero} — {r.descricao[:55]} [{r.tipo}]": r.id for r in oci.itertuples()}
            soci = c2.selectbox("OKR", list(opci.keys()), key="ci_okr")
            kci  = get_krs(opci[soci])
            if kci.empty:
                st.info("Nenhum KR.")
            else:
                opkci = {f"{r.codigo} — {r.descricao[:60]}": r.id for r in kci.itertuples()}
                skci  = st.selectbox("KR", list(opkci.keys()), key="ci_kr")
                krid  = opkci[skci]
                krci  = kci[kci.id==krid].iloc[0]
                chant = get_checkins(krid)
                inis_ci = get_iniciativas(krid)
                prog_kr  = calc_progresso_kr(krci.valor_ini, krci.valor_alvo, chant)
                prog_ini = calc_progresso_iniciativas(inis_ci)

                m1,m2,m3,m4,m5 = st.columns(5)
                m1.metric("Valor Inicial",  f"{krci.valor_ini:.1f}")
                m2.metric("Valor Alvo",     f"{krci.valor_alvo:.1f}")
                m3.metric("Progresso KR",   f"{prog_kr:.1f}%")
                m4.metric("Prog. Iniciativas", f"{prog_ini:.0f}%")
                m5.metric("Check-ins",      len(chant))

                st.markdown(barra_kr(prog_kr), unsafe_allow_html=True)
                if not inis_ci.empty:
                    n_c = len(inis_ci[inis_ci.status == "Concluído"])
                    st.markdown(barra_ini(prog_ini, len(inis_ci), n_c), unsafe_allow_html=True)

                uv = float(krci.valor_ini)
                if not chant.empty and chant.iloc[0]["valor_atual"] is not None:
                    uv = float(chant.iloc[0]["valor_atual"])

                st.markdown("---")
                with st.form("f_ci", clear_on_submit=True):
                    cc1,cc2,cc3 = st.columns(3)
                    dr  = cc1.date_input("Data do Check-in *", value=date.today())
                    sem = cc2.text_input("Semana (ex: Semana 12/2025)")
                    sts = cc3.selectbox("Status do KR", STATUS_OPTIONS)
                    vat = st.number_input(
                        f"Valor Atual  (Inicial: {krci.valor_ini}  |  Alvo: {krci.valor_alvo})",
                        value=uv, step=1.0)
                    com = st.text_area("Comentário / Observações", height=80)
                    if st.form_submit_button("💾 Registrar Check-in", type="primary", use_container_width=True):
                        run_exec("INSERT INTO checkin(kr_id,data_ref,semana,valor_atual,status,comentario) VALUES(?,?,?,?,?,?)",
                                 (krid,str(dr),sem.strip(),vat,sts,com.strip()))
                        np_ = max(0,min(100,(vat-float(krci.valor_ini))/max(float(krci.valor_alvo)-float(krci.valor_ini),0.001)*100))
                        st.success(f"✅ Check-in registrado! Progresso KR: **{np_:.1f}%**")
                        st.rerun()

    with t2:
        st.subheader("Histórico de Check-ins")
        h1,h2 = st.columns(2)
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
                skh  = st.selectbox("KR", list(opkh.keys()), key="hi_kr")
                khid = opkh[skh]
                chh  = get_checkins(khid)
                if chh.empty:
                    st.info("Nenhum check-in registrado.")
                else:
                    st.dataframe(
                        chh[["data_ref","semana","valor_atual","status","comentario","criado_em"]].rename(columns={
                            "data_ref":"Data","semana":"Semana","valor_atual":"Valor Atual",
                            "status":"Status","comentario":"Comentário","criado_em":"Registrado em"}),
                        use_container_width=True, hide_index=True)

                    st.markdown("#### ✏️ Editar Check-in")
                    opch = {f"{r.data_ref}  ·  {r.semana or ''}  ·  Val: {r.valor_atual}  ·  {r.status}": r.id
                            for r in chh.itertuples()}
                    sch     = st.selectbox("Selecione", list(opch.keys()), key="hi_ced")
                    chid_ed = opch[sch]; chr_ = chh[chh.id==chid_ed].iloc[0]
                    with st.form("f_ech"):
                        ec1,ec2,ec3 = st.columns(3)
                        try:    drv = datetime.strptime(str(chr_.data_ref),"%Y-%m-%d").date()
                        except: drv = date.today()
                        ndr  = ec1.date_input("Data", value=drv, key="hi_dr")
                        nsem = ec2.text_input("Semana", value=chr_.semana or "")
                        si   = STATUS_OPTIONS.index(chr_.status) if chr_.status in STATUS_OPTIONS else 0
                        nsts = ec3.selectbox("Status", STATUS_OPTIONS, index=si)
                        nvat = st.number_input("Valor Atual", value=float(chr_.valor_atual or 0))
                        ncom = st.text_area("Comentário", value=chr_.comentario or "", height=60)
                        es1,es2 = st.columns(2)
                        if es1.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                            run_exec("UPDATE checkin SET data_ref=?,semana=?,valor_atual=?,status=?,comentario=? WHERE id=?",
                                     (str(ndr),nsem.strip(),nvat,nsts,ncom.strip(),chid_ed))
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
    fn = fc1.selectbox("Núcleo", ["Todos"]+NUCLEOS, key="d_n")
    ft = fc2.selectbox("Tipo",   ["Todos","Estratégico","Tático/Departamental"], key="d_t")
    fs = fc3.selectbox("Status", ["Todos"]+STATUS_OPTIONS, key="d_s")

    df_f = dp.copy() if not dp.empty else pd.DataFrame()
    if not df_f.empty:
        if fn != "Todos": df_f = df_f[df_f.nucleo==fn]
        if ft != "Todos": df_f = df_f[df_f.tipo==ft]
        if fs != "Todos": df_f = df_f[df_f.ultimo_status==fs]

    if df_f.empty:
        st.warning("Nenhum dado com esses filtros."); st.stop()

    # Paleta de azuis coerente
    BLUE_SCALE = ["#D6E8FA","#93C5FD","#4A9EE8","#2878D6","#1E5FBB","#0C2461"]
    cores_status = {
        "Concluído":    "#1E5FBB",
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
            orientation="h", marker_color="#D4A017",
            text=pn["prog_ini"].apply(lambda v: f"{v:.1f}%"), textposition="outside",
            visible="legendonly",
        ))
        fig1.update_layout(
            title="Progresso Médio por Núcleo",
            barmode="group", xaxis=dict(range=[0,120], title="%"),
            height=340, paper_bgcolor="white", plot_bgcolor="#F7F9FC",
            font=dict(family="IBM Plex Sans", color="#0C2461"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig1, use_container_width=True)

    with cg2:
        sc = df_f["ultimo_status"].fillna("Sem check-in").value_counts().reset_index()
        sc.columns = ["Status","Qtd"]
        fig2 = px.pie(sc, names="Status", values="Qtd", title="Status dos KRs",
                      color="Status", color_discrete_map=cores_status, hole=0.42)
        fig2.update_layout(height=340, paper_bgcolor="white",
                           font=dict(family="IBM Plex Sans", color="#0C2461"))
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
        marker_color="#D4A017",
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
        font=dict(family="IBM Plex Sans", color="#0C2461"),
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
                    font=dict(family="IBM Plex Sans", color="#0C2461"),
                )
                st.plotly_chart(fig4, use_container_width=True)

    # ── INICIATIVAS POR STATUS
    if not all_inis.empty:
        st.markdown("### ⚡ Iniciativas por Status")
        ij = all_inis.merge(
            run_query("SELECT kr.id as kr_id, okr.nucleo FROM kr JOIN okr ON kr.okr_id=okr.id"),
            on="kr_id")
        if fn != "Todos": ij = ij[ij.nucleo==fn]
        if not ij.empty:
            pi = ij["status"].value_counts().reset_index()
            pi.columns = ["Status","Qtd"]
            fig5 = px.bar(pi, x="Status", y="Qtd", title="Iniciativas por Status",
                          color="Status", color_discrete_map=cores_status, text="Qtd")
            fig5.update_traces(textposition="outside")
            fig5.update_layout(
                height=290, showlegend=False,
                paper_bgcolor="white", plot_bgcolor="#F7F9FC",
                font=dict(family="IBM Plex Sans", color="#0C2461"),
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